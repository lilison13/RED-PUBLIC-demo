#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

LOCAL_TZ = ZoneInfo("Asia/Jerusalem")
LIVE_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
OFFICIAL_HISTORY_URL = "https://www.oref.org.il/warningMessages/alert/History/AlertsHistory.json"

BASE_DIR = Path(os.environ.get("OREF_MONITOR_BASE_DIR", "/opt/oref-monitor"))
DATA_DIR = BASE_DIR / "data"
WEB_API_DIR = BASE_DIR / "web" / "api"

STATE_FILE = DATA_DIR / "state.json"
LOCAL_HISTORY_FILE = DATA_DIR / "local_history.json"
OFFICIAL_HISTORY_FILE = DATA_DIR / "official_history.json"
MERGED_HISTORY_FILE = DATA_DIR / "history.json"
LATEST_EVENT_FILE = DATA_DIR / "latest_event.json"
META_FILE = DATA_DIR / "meta.json"

WEB_STATUS_FILE = WEB_API_DIR / "status"
WEB_HISTORY_FILE = WEB_API_DIR / "history"
WEB_LATEST_EVENT_FILE = WEB_API_DIR / "latest_event"
WEB_META_FILE = WEB_API_DIR / "meta"

DEDUP_SECONDS = 5
FAST_POLL_SECONDS = 1
OFFICIAL_HISTORY_REFRESH_SECONDS = 60
MAX_LOCAL_HISTORY = 2000
MAX_MERGED_HISTORY = 5000
MERGE_DUP_WINDOW_SECONDS = 120
LOCAL_ATTACH_WINDOW_SECONDS = 600
LOCAL_HISTORY_WINDOW_HOURS = 24

LIVE_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0",
}

OFFICIAL_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0",
}


def log(msg: str):
    print(f"[oref-monitor] {msg}", flush=True)


def load_json_file(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"load_json_file failed for {path}: {e}")
    return default


def atomic_write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def save_json_file(path: Path, data):
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    atomic_write_text(path, payload + "\n")


def atomic_publish(web_path: Path, data):
    save_json_file(web_path, data)


def fetch_live_alert():
    req = Request(LIVE_URL, headers=LIVE_HEADERS, method="GET")
    with urlopen(req, timeout=10) as resp:
        raw = resp.read()

    raw = raw.lstrip(b"\xef\xbb\xbf")
    text = raw.decode("utf-8", errors="replace").replace("\r", "").strip()

    if not text or text in ("[]", "{}"):
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        log(f"live alert JSON parse error: {e}")
        return None

    if not isinstance(parsed, dict):
        log(f"live alert unexpected type: {type(parsed).__name__}")
        return None

    return parsed


def fetch_official_history_24h():
    req = Request(OFFICIAL_HISTORY_URL, headers=OFFICIAL_HEADERS, method="GET")

    with urlopen(req, timeout=20) as resp:
        body = resp.read()

    # Observed response from the new endpoint: HTTP 200 with CRLF only.
    # This is not JSON and does not prove there are no historical alerts.
    # Return a distinct result so the caller keeps the existing history.
    if body == b"\r\n":
        return None

    raw = body.decode("utf-8-sig").strip()
    if not raw:
        raise ValueError("Unexpected empty official history response")

    rows = json.loads(raw)

    if not isinstance(rows, list):
        raise ValueError("Unexpected official history response")

    cutoff = datetime.now(LOCAL_TZ) - timedelta(hours=24)

    groups = {}

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Unexpected official history record")
        alert_time = row.get("alertDate")
        if not isinstance(alert_time, str) or not alert_time.strip():
            raise ValueError("Missing official history timestamp")
        if not isinstance(row.get("data"), str) or not row["data"].strip():
            raise ValueError("Unexpected official history locality")
        if not str(row.get("category") or "").strip():
            raise ValueError("Missing official history category")
        if not str(row.get("category_desc") or row.get("title") or "").strip():
            raise ValueError("Missing official history title")

        try:
            dt = datetime.fromisoformat(alert_time)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=LOCAL_TZ)
            else:
                dt = dt.astimezone(LOCAL_TZ)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid official history timestamp") from exc

        if dt < cutoff:
            continue

        category = str(row.get("category", "")).strip()
        category_desc = str(row.get("category_desc") or row.get("title") or "").strip()
        matrix_id = str(row.get("matrix_id", "")).strip()

        key = (alert_time, category, category_desc, matrix_id)

        if key not in groups:
            groups[key] = {
                "ts": int(dt.timestamp() * 1000),
                "datetime": dt.strftime("%d.%m.%Y %H:%M:%S"),
                "alert": {
                    "id": f"official-{alert_time}-{category}-{matrix_id}",
                    "cat": category,
                    "title": category_desc,
                    "data": [],
                    "desc": category_desc,
                },
                "sources": ["official"],
            }

        city = str(row.get("data", "")).strip()
        if city and city not in groups[key]["alert"]["data"]:
            groups[key]["alert"]["data"].append(city)

    events = list(groups.values())
    events.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return events


def retain_official_history(previous, incoming):
    # The replacement feed may cover less than 24 hours. Retain already
    # collected official events inside the existing 24-hour window.
    cutoff_ts = int((datetime.now(LOCAL_TZ) - timedelta(hours=24)).timestamp() * 1000)
    retained = {}
    for item in [*previous, *incoming]:
        ts = int(item.get("ts", 0) or 0)
        if ts < cutoff_ts:
            continue
        alert = item.get("alert", {}) or {}
        key = (ts, alert.get("id"), alert.get("cat"), alert.get("title"))
        if key in retained:
            old_alert = retained[key]["alert"]
            cities = merge_alert_localities(old_alert, alert)
            retained[key] = {**item, "alert": {**alert, "data": cities}}
        else:
            retained[key] = item
    return sorted(retained.values(), key=lambda item: item.get("ts", 0), reverse=True)


def make_fingerprint(alert_obj) -> str:
    normalized = json.dumps(alert_obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def build_alert_keys(alert_obj):
    alert_id = str(alert_obj.get("id", "")).strip()
    title = str(alert_obj.get("title", "")).strip()
    category = str(alert_obj.get("cat", "")).strip()
    desc = str(alert_obj.get("desc", "")).strip()

    # normalize localities order so live and official produce identical keys
    localities = sorted(str(l).strip() for l in (alert_obj.get("data", []) or []))

    keys = []

    for locality in localities:
        if alert_id:
            keys.append(f"{alert_id}|{category}|{title}|{desc}|{locality}")
        else:
            keys.append(f"{category}|{title}|{desc}|{locality}")

    if not keys:
        if alert_id:
            keys.append(f"{alert_id}|{category}|{title}|{desc}|NO_LOCALITY")
        else:
            keys.append(f"{category}|{title}|{desc}|NO_LOCALITY")

    return keys


def is_valid_alert(alert_obj):
    if not isinstance(alert_obj, dict):
        return False

    title = str(alert_obj.get("title") or "").strip()
    data = alert_obj.get("data") or []

    if not title:
        return False

    if not isinstance(data, list):
        return False

    return True


def make_status(ok=True, current_alert=None, error_message=None):
    return {
        "ok": ok,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "has_active_alert": current_alert is not None,
        "current_alert": current_alert,
        "error": error_message,
    }


def append_local_history(local_history, alert_obj):
    item = {
        "ts": int(time.time() * 1000),
        "datetime": time.strftime("%d.%m.%Y %H:%M:%S"),
        "alert": alert_obj,
        "sources": ["local"],
    }
    local_history.append(item)
    local_history = local_history[-MAX_LOCAL_HISTORY:]
    save_json_file(LOCAL_HISTORY_FILE, local_history)
    return local_history, item


def trim_local_history_by_time(local_history):
    cutoff_ts = int((time.time() - (LOCAL_HISTORY_WINDOW_HOURS * 3600)) * 1000)
    trimmed = [
        item for item in (local_history or [])
        if int(item.get("ts", 0) or 0) >= cutoff_ts
    ]
    return trimmed[-MAX_LOCAL_HISTORY:]


def normalize_event_kind_for_match(cat, title=None):
    """
    Used only for logical matching.
    Never written back as final event classification.
    """
    cat = str(cat or "").strip()
    title = str(title or "").strip()

    if title == "חדירת כלי טיס עוין":
        return "uav"

    if title == "ירי רקטות וטילים":
        return "rocket"

    if title == "האירוע הסתיים":
        return "all_clear"

    if title == "בדקות הקרובות צפויות להתקבל התרעות באזורך":
        return "early_warning"

    if cat in ("6", "2"):
        return "uav"

    if cat == "1":
        return "rocket"

    if cat == "13":
        return "all_clear"

    if cat == "14":
        return "early_warning"

    if cat == "10":
        return "info"

    return cat


def normalize_title_for_match(title):
    return str(title or "").strip()


def alert_cities_set(alert):
    return {
        str(x).strip()
        for x in (alert.get("data", []) or [])
        if str(x).strip()
    }


def alerts_overlap(alert_a, alert_b):
    return bool(alert_cities_set(alert_a) & alert_cities_set(alert_b))


def is_same_logical_event(item_a, item_b):
    alert_a = item_a.get("alert", {}) or {}
    alert_b = item_b.get("alert", {}) or {}

    kind_a = normalize_event_kind_for_match(alert_a.get("cat"), alert_a.get("title"))
    kind_b = normalize_event_kind_for_match(alert_b.get("cat"), alert_b.get("title"))

    title_a = normalize_title_for_match(alert_a.get("title"))
    title_b = normalize_title_for_match(alert_b.get("title"))

    if not kind_a or not title_a:
        return False

    if kind_a != kind_b:
        return False

    if title_a != title_b:
        return False

    if not alerts_overlap(alert_a, alert_b):
        return False

    ts_a = int(item_a.get("ts", 0) or 0)
    ts_b = int(item_b.get("ts", 0) or 0)
    delta_sec = abs(ts_a - ts_b) / 1000.0

    sources_a = set(item_a.get("sources", []) or [])
    sources_b = set(item_b.get("sources", []) or [])

    # official <-> local: attach only if close enough in time
    if ("official" in sources_a and "local" in sources_b) or \
       ("official" in sources_b and "local" in sources_a):
        return delta_sec <= LOCAL_ATTACH_WINDOW_SECONDS

    return delta_sec <= MERGE_DUP_WINDOW_SECONDS


def is_official_item(item):
    return "official" in (item.get("sources", []) or [])


def is_local_item(item):
    return "local" in (item.get("sources", []) or [])


def merge_alert_localities(*alerts):
    seen = set()
    merged = []

    for alert in alerts:
        for locality in (alert.get("data", []) or []):
            name = str(locality).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            merged.append(name)

    return merged


def apply_official_truth(matched, official_item):
    official_alert = official_item.get("alert", {}) or {}
    matched_alert = matched["alert"]
    existing_localities = merge_alert_localities(matched_alert)

    matched_alert["id"] = official_alert.get("id")
    matched_alert["cat"] = official_alert.get("cat")
    matched_alert["title"] = official_alert.get("title")
    matched_alert["desc"] = official_alert.get("desc")
    matched_alert["data"] = merge_alert_localities(official_alert, {"data": existing_localities})

    matched["ts"] = official_item.get("ts", 0)
    matched["datetime"] = official_item.get("datetime", "")

    matched["official_ts"] = official_item.get("ts", 0)
    matched["official_datetime"] = official_item.get("datetime", "")


def merge_histories(local_history, official_history):
    merged = []

    local_history = trim_local_history_by_time(local_history)

    # 1) start from official history as canonical base
    for item in official_history:
        alert = item.get("alert", {}) or {}

        if not is_valid_alert(alert):
            continue

        new_item = {
            "ts": item.get("ts", 0),
            "datetime": item.get("datetime", ""),
            "alert": {
                "id": alert.get("id"),
                "cat": alert.get("cat"),
                "title": alert.get("title"),
                "data": list(alert.get("data", []) or []),
                "desc": alert.get("desc"),
            },
            "sources": ["official"],
            "official_ts": item.get("ts", 0),
            "official_datetime": item.get("datetime", ""),
        }
        merged.append(new_item)

    # 2) attach local items to matching official events
    #    if no match exists yet -> keep the local item in merged history
    for local_item in local_history:
        local_alert = local_item.get("alert", {}) or {}

        if not is_valid_alert(local_alert):
            continue

        matched = None

        for existing in merged:
            if is_same_logical_event(local_item, existing):
                matched = existing
                break

        if matched is not None:
            if "local" not in matched["sources"]:
                matched["sources"].append("local")

            matched["local_seen_ts"] = max(
                int(matched.get("local_seen_ts", 0) or 0),
                int(local_item.get("ts", 0) or 0)
            )
            matched["local_seen_datetime"] = local_item.get(
                "datetime",
                matched.get("local_seen_datetime", "")
            )

            # keep official truth if official exists
            if is_official_item(matched):
                apply_official_truth(matched, matched)

            continue

        # no official match yet -> include local event as-is
        new_local_item = {
            "ts": int(local_item.get("ts", 0) or 0),
            "datetime": local_item.get("datetime", ""),
            "alert": {
                "id": local_alert.get("id"),
                "cat": local_alert.get("cat"),
                "title": local_alert.get("title"),
                "data": list(local_alert.get("data", []) or []),
                "desc": local_alert.get("desc"),
            },
            "sources": ["local"],
            "local_seen_ts": int(local_item.get("ts", 0) or 0),
            "local_seen_datetime": local_item.get("datetime", ""),
        }
        merged.append(new_local_item)

    merged.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return merged[:MAX_MERGED_HISTORY]


def build_meta(state):
    return {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status_version": state.get("status_version", 0),
        "latest_event_version": state.get("latest_event_version", 0),
        "history_version": state.get("history_version", 0),
        "official_history_last_fetch_ts": state.get("official_history_last_fetch_ts", 0),
        "last_live_ok": state.get("last_live_ok", False),
        "last_history_ok": state.get("last_history_ok", False),
        "official_history_error": state.get("official_history_error"),
        "last_live_parse_error": state.get("last_live_parse_error", False),
    }


def publish_meta(state):
    meta = build_meta(state)
    save_json_file(META_FILE, meta)
    atomic_publish(WEB_META_FILE, meta)


def ensure_bootstrap_files(state, merged_history, latest_event):
    status_payload = make_status(ok=False, current_alert=None, error_message=None)

    if not WEB_STATUS_FILE.exists():
        atomic_publish(WEB_STATUS_FILE, status_payload)

    if not WEB_HISTORY_FILE.exists():
        atomic_publish(WEB_HISTORY_FILE, merged_history)

    if latest_event is not None and not WEB_LATEST_EVENT_FILE.exists():
        atomic_publish(WEB_LATEST_EVENT_FILE, latest_event)

    if not WEB_META_FILE.exists():
        publish_meta(state)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WEB_API_DIR.mkdir(parents=True, exist_ok=True)

    state = load_json_file(STATE_FILE, {
        "last_fingerprint": "",
        "last_seen_ts": 0,
        "recent_alert_keys": {},
        "recent_fingerprints": {},
        "official_history_last_fetch_ts": 0,
        "status_version": 0,
        "latest_event_version": 0,
        "history_version": 0,
        "last_live_ok": False,
        "last_history_ok": False,
        "last_live_parse_error": False,
    })

    local_history = trim_local_history_by_time(load_json_file(LOCAL_HISTORY_FILE, []))
    save_json_file(LOCAL_HISTORY_FILE, local_history)

    official_history = load_json_file(OFFICIAL_HISTORY_FILE, [])
    merged_history = merge_histories(local_history, official_history)
    save_json_file(MERGED_HISTORY_FILE, merged_history)
    latest_event = load_json_file(LATEST_EVENT_FILE, None)

    atomic_publish(WEB_HISTORY_FILE, merged_history)
    atomic_publish(WEB_STATUS_FILE, make_status(ok=False, current_alert=None, error_message=None))
    if latest_event is not None:
        atomic_publish(WEB_LATEST_EVENT_FILE, latest_event)
    publish_meta(state)
    ensure_bootstrap_files(state, merged_history, latest_event)

    log("service started")

    while True:
        loop_started = time.time()
        now = int(loop_started)

        try:
            live_alert = fetch_live_alert()
            if live_alert is not None and not is_valid_alert(live_alert):
                log("invalid live alert skipped")
                live_alert = None

            status_payload = make_status(ok=True, current_alert=live_alert, error_message=None)
            atomic_publish(WEB_STATUS_FILE, status_payload)

            state["last_live_ok"] = True
            state["last_live_parse_error"] = False
            state["status_version"] = int(state.get("status_version", 0)) + 1

        except HTTPError as e:
            live_alert = None
            status_payload = make_status(ok=False, current_alert=None, error_message=f"HTTP {e.code}")
            atomic_publish(WEB_STATUS_FILE, status_payload)

            state["last_live_ok"] = False
            state["last_live_parse_error"] = False
            state["status_version"] = int(state.get("status_version", 0)) + 1
            log(f"live fetch HTTP error: {e.code}")

        except URLError as e:
            live_alert = None
            status_payload = make_status(ok=False, current_alert=None, error_message=f"URL {e}")
            atomic_publish(WEB_STATUS_FILE, status_payload)

            state["last_live_ok"] = False
            state["last_live_parse_error"] = False
            state["status_version"] = int(state.get("status_version", 0)) + 1
            log(f"live fetch URL error: {e}")

        except Exception as e:
            live_alert = None
            status_payload = make_status(ok=False, current_alert=None, error_message=str(e))
            atomic_publish(WEB_STATUS_FILE, status_payload)

            state["last_live_ok"] = False
            state["last_live_parse_error"] = False
            state["status_version"] = int(state.get("status_version", 0)) + 1
            log(f"live fetch unexpected error: {e}")

        if live_alert is not None:
            fingerprint = make_fingerprint(live_alert)
            alert_keys = build_alert_keys(live_alert)

            recent_alert_keys = state.get("recent_alert_keys", {})
            recent_alert_keys = {
                k: ts for k, ts in recent_alert_keys.items()
                if (now - ts) <= DEDUP_SECONDS
            }

            recent_fingerprints = state.get("recent_fingerprints", {})
            recent_fingerprints = {
                k: ts for k, ts in recent_fingerprints.items()
                if (now - ts) <= DEDUP_SECONDS
            }

            keys_duplicate = all(key in recent_alert_keys for key in alert_keys)
            fingerprint_duplicate = fingerprint in recent_fingerprints
            is_duplicate = keys_duplicate or fingerprint_duplicate

            if not is_duplicate:
                local_history, appended_item = append_local_history(local_history, live_alert)
                local_history = trim_local_history_by_time(local_history)
                save_json_file(LOCAL_HISTORY_FILE, local_history)

                # rebuild merged history immediately so live events appear in history
                merged_history = merge_histories(local_history, official_history)
                save_json_file(MERGED_HISTORY_FILE, merged_history)
                atomic_publish(WEB_HISTORY_FILE, merged_history)

                for key in alert_keys:
                    recent_alert_keys[key] = now
                recent_fingerprints[fingerprint] = now

                latest_event = appended_item
                save_json_file(LATEST_EVENT_FILE, latest_event)
                atomic_publish(WEB_LATEST_EVENT_FILE, latest_event)

                state["last_fingerprint"] = fingerprint
                state["last_seen_ts"] = now
                state["recent_alert_keys"] = recent_alert_keys
                state["recent_fingerprints"] = recent_fingerprints
                state["latest_event_version"] = int(state.get("latest_event_version", 0)) + 1

                log(
                    "new live alert appended: "
                    f"title={live_alert.get('title', '')!r} "
                    f"cat={live_alert.get('cat', '')!r} "
                    f"localities={len(live_alert.get('data', []) or [])}"
                )
            else:
                state["recent_alert_keys"] = recent_alert_keys
                state["recent_fingerprints"] = recent_fingerprints
                log(
                    "duplicate live alert skipped: "
                    f"title={live_alert.get('title', '')!r} "
                    f"cat={live_alert.get('cat', '')!r}"
                )

        save_json_file(LOCAL_HISTORY_FILE, local_history)

        official_due = (
            now - int(state.get("official_history_last_attempt_ts", 0))
        ) >= OFFICIAL_HISTORY_REFRESH_SECONDS

        if official_due:
            state["official_history_last_attempt_ts"] = now
            try:
                incoming_history = fetch_official_history_24h()
                if incoming_history is None:
                    # A reachable endpoint returned CRLF, not a JSON history.
                    # Keep the last successful timestamp and all existing data.
                    state["last_history_ok"] = False
                    state["official_history_error"] = (
                        "OREF history returned HTTP 200 with CRLF only; "
                        "no JSON records available, cached history retained"
                    )
                    log(state["official_history_error"])
                else:
                    official_history = retain_official_history(official_history, incoming_history)
                    save_json_file(OFFICIAL_HISTORY_FILE, official_history)

                    merged_history = merge_histories(local_history, official_history)
                    save_json_file(MERGED_HISTORY_FILE, merged_history)
                    atomic_publish(WEB_HISTORY_FILE, merged_history)

                    state["official_history_last_fetch_ts"] = now
                    state["history_version"] = int(state.get("history_version", 0)) + 1
                    state["last_history_ok"] = True
                    state.pop("official_history_error", None)

                    log(
                        f"official history refreshed successfully: "
                        f"{len(incoming_history)} fetched, "
                        f"{len(official_history)} retained, merged={len(merged_history)}"
                    )

            except Exception as e:
                state["last_history_ok"] = False
                state["official_history_error"] = str(e)
                log(f"official history refresh failed: {e}")

        publish_meta(state)
        save_json_file(STATE_FILE, state)

        elapsed = time.time() - loop_started
        sleep_for = max(0.0, FAST_POLL_SECONDS - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
