#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import urllib.request
from pathlib import Path

from beready_engine import EngineState, build_snapshot, load_json

BASE_DIR = Path(os.environ.get("OREF_MONITOR_BASE_DIR", "/opt/oref-monitor"))
WEB_API_DIR = BASE_DIR / "web" / "api"
DATA_DIR = BASE_DIR / "data"

HISTORY_FILE = WEB_API_DIR / "history"
STATUS_FILE = WEB_API_DIR / "status"
ZONES_FILE = WEB_API_DIR / "zones"
SNAPSHOT_FILE = WEB_API_DIR / "beready_snapshot"
DEBUG_FILE = DATA_DIR / "beready_snapshot_backend.json"
STATE_FILE = DATA_DIR / "beready_snapshot_poller_state.json"

POLL_SEC = int(os.environ.get("BEREADY_SNAPSHOT_POLL_SEC", "5"))
MAILER_URL = os.environ.get("BEREADY_MAILER_URL", "http://127.0.0.1:8788/snapshot")
ENABLE_MAIL = os.environ.get("BEREADY_ENABLE_MAIL", "false").strip().lower() == "true"
MAIL_ON_STARTUP = os.environ.get("BEREADY_MAIL_ON_STARTUP", "false").strip().lower() == "true"


def atomic_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def post_json(url: str, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def snapshot_signature(snapshot: dict) -> str:
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True)


def mail_transition_key(snapshot: dict) -> str:
    return json.dumps({
        "state": snapshot.get("state", "NORMAL"),
        "simpleTitle": snapshot.get("simpleTitle", ""),
        "simpleBody": snapshot.get("simpleBody", ""),
        "messageTitle": (snapshot.get("message") or {}).get("title", ""),
        "messageBody": (snapshot.get("message") or {}).get("body", ""),
    }, ensure_ascii=False, sort_keys=True)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state_obj = load_json(STATE_FILE, {
        "computed_state": "NORMAL",
        "computed_state_since_ts": 0,
        "last_official_alert_ts": 0,
        "last_all_clear_ts": 0,
        "last_hash": "",
        "last_transition_key": "",
        "initialized": False,
    })
    engine_state = EngineState(
        computed_state=str(state_obj.get("computed_state", state_obj.get("current_state", "NORMAL"))),
        computed_state_since_ts=int(state_obj.get("computed_state_since_ts", state_obj.get("state_since_ts", 0)) or 0),
        last_official_alert_ts=int(state_obj.get("last_official_alert_ts", 0) or 0),
        last_all_clear_ts=int(state_obj.get("last_all_clear_ts", 0) or 0),
    )

    while True:
        try:
            history_items = load_json(HISTORY_FILE, [])
            status_obj = load_json(STATUS_FILE, {})
            zones_map = load_json(ZONES_FILE, {})

            snapshot = build_snapshot(history_items, status_obj, zones_map, engine_state)
            atomic_write_json(SNAPSHOT_FILE, snapshot)
            atomic_write_json(DEBUG_FILE, snapshot)

            new_hash = snapshot_signature(snapshot)
            old_hash = str(state_obj.get("last_hash", ""))
            transition_key = mail_transition_key(snapshot)
            last_transition_key = str(state_obj.get("last_transition_key", ""))
            initialized = bool(state_obj.get("initialized", False))

            changed = new_hash != old_hash
            transition_changed = transition_key != last_transition_key

            state_obj["last_hash"] = new_hash
            state_obj["computed_state"] = engine_state.computed_state
            state_obj["computed_state_since_ts"] = int(engine_state.computed_state_since_ts or 0)
            state_obj["last_official_alert_ts"] = int(engine_state.last_official_alert_ts or 0)
            state_obj["last_all_clear_ts"] = int(engine_state.last_all_clear_ts or 0)

            should_mail = False
            if ENABLE_MAIL:
                if not initialized:
                    should_mail = MAIL_ON_STARTUP
                elif transition_changed:
                    should_mail = True

            if should_mail:
                code, body = post_json(MAILER_URL, snapshot)
                if 200 <= code < 300:
                    state_obj["last_transition_key"] = transition_key
                    print(f"[beready-snapshot-poller] mailed transition: {code} {body}", flush=True)
                else:
                    print(f"[beready-snapshot-poller] mailer non-2xx: {code} {body}", flush=True)
            elif changed:
                print("[beready-snapshot-poller] snapshot updated without mail (no state transition)", flush=True)

            if not initialized:
                state_obj["last_transition_key"] = transition_key
                state_obj["initialized"] = True

            atomic_write_json(STATE_FILE, state_obj)
        except Exception as e:
            print(f"[beready-snapshot-poller] loop error: {e}", flush=True)
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
