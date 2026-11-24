#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import html
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

HISTORY_WINDOW_MS = 20 * 60 * 1000
ACTIVE_WINDOW_MS = 60 * 1000
LOCALITY_DEDUP_MS = 45 * 1000
TRAJECTORY_WINDOW_MS = 7 * 60 * 1000
CLUSTER_WINDOW_MS = 2 * 60 * 1000

HYSTERESIS = {
    "READY_UP": 16,
    "READY_DOWN": 10,
    "HIGH_UP": 36,
    "HIGH_DOWN": 26,
    "PRE_UP": 60,
    "PRE_DOWN": 48,
}

STATE_TIMEOUT_MS = {
    "READY": 2 * 60 * 1000,
    "HIGH": 4 * 60 * 1000,
    "PRE_SHELTER": 3 * 60 * 1000,
    "POST_ALERT_HIGH": 3 * 60 * 1000,
}

GEOGRAPHY = {
    "PRE_HARD_BLOCK_KM": 32,
    "TRAJECTORY_CAP_KM": 30,
    "HAIFA_CORRIDOR_MAX_KM": 22,
    "NORTH_BORDER_LAT": 33.00,
    "NORTH_BUFFER_LAT": 32.98,
}

HAIFA_POINT = {"lat": 32.7940, "lon": 34.9896}

NORTH_BORDER_AREAS = {
    "אדמית", "חניתה", "שלומי", "יערה", "סער", "נהריה", "גשר הזיו", "חוף אכזיב", "לימן", "עברון",
    "כברי", "ראש הנקרה", "ערב אל עראמשה", "משגב עם", "מטולה", "כפר גלעדי", "מרגליות", "קריית שמונה",
    "תל חי", "אפק"
}

AREA_ALIASES = {
    "קרית אתא": "קריית אתא",
    "קרית ביאליק": "קריית ביאליק",
    "קרית ים": "קריית ים",
    "קרית מוצקין": "קריית מוצקין",
    "קרית חיים": "קריית חיים",
    "קרית שמונה": "קריית שמונה",
    "מעלות-תרשיחא": "מעלות תרשיחא",
    "חיפה כרמל": "חיפה - כרמל",
    "חיפה מפרץ": "חיפה - מפרץ",
    "חיפה מערב": "חיפה - מערב",
    "טירת הכרמל": "טירת כרמל",
}

NOISE_ZONES = {"גליל עליון", "קו העימות", "גליל מערבי", "הקריות", "כרמל", "מרכז הכרמל"}

# Pulled from the existing frontend's areas.js where it matters most for Haifa-oriented scoring.
AREA_OVERRIDES = {
    "חיפה": {"lat": 32.7940, "lon": 34.9896, "weight": 1.0, "corridor": "haifa", "track": "coast", "trackOrder": 10},
    "חיפה - כרמל": {"lat": 32.8000, "lon": 34.9800, "weight": 1.0, "corridor": "haifa", "track": "coast", "trackOrder": 9},
    "חיפה - מערב": {"lat": 32.8150, "lon": 34.9650, "weight": 1.0, "corridor": "haifa", "track": "coast", "trackOrder": 11},
    "חיפה - מפרץ": {"lat": 32.8200, "lon": 35.0400, "weight": 1.0, "corridor": "haifa", "track": "coast", "trackOrder": 12},
    "נשר": {"lat": 32.7650, "lon": 35.0450, "weight": 0.95, "corridor": "haifa", "track": "inland", "trackOrder": 15},
    "טירת כרמל": {"lat": 32.7600, "lon": 34.9700, "weight": 0.95, "corridor": "coast", "track": "coast", "trackOrder": 8},
    "רכסים": {"lat": 32.8200, "lon": 35.1000, "weight": 0.88, "corridor": "haifa", "track": "inland", "trackOrder": 18},
    "קריית אתא": {"lat": 32.8100, "lon": 35.1100, "weight": 0.95, "corridor": "krayot", "track": "inland", "trackOrder": 28},
    "קריית ביאליק": {"lat": 32.8300, "lon": 35.0850, "weight": 0.95, "corridor": "krayot", "track": "coast", "trackOrder": 48},
    "קריית ים": {"lat": 32.8500, "lon": 35.0700, "weight": 0.95, "corridor": "krayot", "track": "coast", "trackOrder": 50},
    "קריית מוצקין": {"lat": 32.8400, "lon": 35.0800, "weight": 0.95, "corridor": "krayot", "track": "coast", "trackOrder": 45},
    "קריית חיים": {"lat": 32.8300, "lon": 35.0300, "weight": 0.95, "corridor": "krayot", "track": "coast", "trackOrder": 35},
    "ראש הנקרה": {"lat": 33.0860, "lon": 35.1080, "weight": 0.66, "corridor": "coast", "track": "coast", "trackOrder": 100},
    "שלומי": {"lat": 33.0720, "lon": 35.1470, "weight": 0.72, "corridor": "coast", "track": "coast", "trackOrder": 90},
    "נהריה": {"lat": 33.0050, "lon": 35.0940, "weight": 0.85, "corridor": "coast", "track": "coast", "trackOrder": 80},
    "עכו": {"lat": 32.9280, "lon": 35.0820, "weight": 0.92, "corridor": "coast", "track": "coast", "trackOrder": 70},
    "לוחמי הגטאות": {"lat": 32.9780, "lon": 35.0960, "weight": 0.74, "corridor": "coast", "track": "coast", "trackOrder": 60},
    "עברון": {"lat": 33.0000, "lon": 35.0940, "weight": 0.68, "corridor": "western_galilee", "track": "coast", "trackOrder": 78},
    "כברי": {"lat": 33.0170, "lon": 35.1630, "weight": 0.68, "corridor": "western_galilee", "track": "coast", "trackOrder": 84},
    "יחיעם": {"lat": 33.0380, "lon": 35.1970, "weight": 0.68, "corridor": "western_galilee", "track": "coast", "trackOrder": 86},
    "מעלות תרשיחא": {"lat": 33.0160, "lon": 35.2740, "weight": 0.68, "corridor": "western_galilee", "track": "inland", "trackOrder": 82},
    "כרמיאל": {"lat": 32.9170, "lon": 35.3050, "weight": 0.62, "corridor": "inland", "track": "inland", "trackOrder": 70},
    "סכנין": {"lat": 32.8620, "lon": 35.2930, "weight": 0.60, "corridor": "inland", "track": "inland", "trackOrder": 62},
    "טמרה": {"lat": 32.8530, "lon": 35.1990, "weight": 0.68, "corridor": "inland", "track": "inland", "trackOrder": 58},
    "שפרעם": {"lat": 32.8050, "lon": 35.1700, "weight": 0.72, "corridor": "inland", "track": "inland", "trackOrder": 50},
    "אעבלין": {"lat": 32.8320, "lon": 35.1930, "weight": 0.66, "corridor": "inland", "track": "inland", "trackOrder": 54},
    "קריית שמונה": {"lat": 33.2070, "lon": 35.5700, "weight": 0.40, "corridor": "upper_north", "track": "upper_north", "trackOrder": 100},
    "מטולה": {"lat": 33.2790, "lon": 35.5790, "weight": 0.36, "corridor": "upper_north", "track": "upper_north", "trackOrder": 110},
    "משגב עם": {"lat": 33.2400, "lon": 35.6100, "weight": 0.36, "corridor": "upper_north", "track": "upper_north", "trackOrder": 108},
    "כפר גלעדי": {"lat": 33.2330, "lon": 35.5710, "weight": 0.36, "corridor": "upper_north", "track": "upper_north", "trackOrder": 103},
    "מרגליות": {"lat": 33.2160, "lon": 35.5500, "weight": 0.36, "corridor": "upper_north", "track": "upper_north", "trackOrder": 102},
}


AREA_ALIASES["\u05d7\u05d9\u05e4\u05d4 \u05e7\u05e8\u05d9\u05d9\u05ea \u05d7\u05d9\u05d9\u05dd \u05d5\u05e9\u05de\u05d5\u05d0\u05dc"] = "\u05d7\u05d9\u05e4\u05d4 - \u05e7\u05e8\u05d9\u05d9\u05ea \u05d7\u05d9\u05d9\u05dd \u05d5\u05e9\u05de\u05d5\u05d0\u05dc"
AREA_OVERRIDES["\u05d7\u05d9\u05e4\u05d4 - \u05e7\u05e8\u05d9\u05d9\u05ea \u05d7\u05d9\u05d9\u05dd \u05d5\u05e9\u05de\u05d5\u05d0\u05dc"] = {"lat": 32.8300, "lon": 35.0300, "weight": 1.0, "corridor": "krayot", "track": "coast", "trackOrder": 35}

@dataclass
class EngineState:
    computed_state: str = "NORMAL"
    computed_state_since_ts: int = 0
    last_official_alert_ts: int = 0
    last_all_clear_ts: int = 0


def load_json(path: Path, default: Any):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def normalize_area_name(raw: Any) -> str:
    area = str(raw or "").strip()
    if not area:
        return ""
    area = " ".join(area.split())
    area = area.replace("׳", "'").replace("`", "'").replace("״", '"')
    area = area.replace("\u200f", "").replace("\u200e", "")
    area = area.replace("-", " - ")
    area = " ".join(area.split())
    return AREA_ALIASES.get(area, area)


def is_noise_zone(area: str) -> bool:
    return normalize_area_name(area) in NOISE_ZONES


def haversine_km(a: dict[str, float], b: dict[str, float]) -> float:
    r = 6371.0
    d_lat = math.radians(b["lat"] - a["lat"])
    d_lon = math.radians(b["lon"] - a["lon"])
    lat1 = math.radians(a["lat"])
    lat2 = math.radians(b["lat"])
    x = math.sin(d_lat / 2) ** 2 + math.sin(d_lon / 2) ** 2 * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))
    return r * c


def get_area_meta(area: str, zones_map: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_area_name(area)
    if not normalized:
        return None

    # only areas explicitly defined for BeReady participate
    if normalized in AREA_OVERRIDES:
        return AREA_OVERRIDES[normalized]

    return None


def is_beready_area(area: str) -> bool:
    normalized = normalize_area_name(area)
    return bool(normalized and normalized in AREA_OVERRIDES)


def get_alert_payload(obj: dict[str, Any]) -> dict[str, Any]:
    return obj.get("alert") or obj or {}


def get_alert_sources(obj: dict[str, Any]) -> list[str]:
    if isinstance(obj.get("sources"), list):
        return obj["sources"]
    alert = obj.get("alert")
    if isinstance(alert, dict) and isinstance(alert.get("sources"), list):
        return alert["sources"]
    return []


def has_official_source(obj: dict[str, Any]) -> bool:
    return any(str(s).strip().lower() == "official" for s in get_alert_sources(obj))


def get_alert_category(obj: dict[str, Any]) -> str:
    return str(get_alert_payload(obj).get("cat") or "").strip()


def alert_text(alert_obj: dict[str, Any]) -> str:
    return " ".join([
        str(alert_obj.get("title") or ""),
        str(alert_obj.get("desc") or ""),
        str(alert_obj.get("raw") or ""),
        str(alert_obj.get("cat") or ""),
    ]).lower()


def extract_areas(alert_obj: dict[str, Any]) -> list[str]:
    data = alert_obj.get("data")
    if not isinstance(data, list):
        return []
    out = []
    for a in data:
        n = normalize_area_name(a)
        if n:
            out.append(n)
    return out



def is_haifa_area(area: str) -> bool:
    normalized = normalize_area_name(area).lower()
    return normalized in {
        "\u05d7\u05d9\u05e4\u05d4",
        "\u05d7\u05d9\u05e4\u05d4 - \u05db\u05e8\u05de\u05dc",
        "\u05d7\u05d9\u05e4\u05d4 - \u05de\u05e2\u05e8\u05d1",
        "\u05d7\u05d9\u05e4\u05d4 - \u05de\u05e4\u05e8\u05e5",
        "haifa",
        "haifa - carmel",
        "haifa - west",
        "haifa - bay",
    }


def is_kiryat_haim_shmuel_area(area: str) -> bool:
    return normalize_area_name(area) == "\u05d7\u05d9\u05e4\u05d4 - \u05e7\u05e8\u05d9\u05d9\u05ea \u05d7\u05d9\u05d9\u05dd \u05d5\u05e9\u05de\u05d5\u05d0\u05dc"


def is_early_warning(obj: dict[str, Any]) -> bool:
    alert = get_alert_payload(obj)
    text = alert_text(alert)
    cat = get_alert_category(obj)
    return cat == "14" or "התרעה מוקדמת" in text or "early warning" in text or "בדקות הקרובות צפויות להתקבל התרעות באזורך" in text


def is_official_early_warning(obj: dict[str, Any]) -> bool:
    cat = get_alert_category(obj)
    return cat == "14" or (is_early_warning(obj) and has_official_source(obj))


def is_official_haifa_alert(alert_obj: dict[str, Any]) -> bool:
    return any(is_haifa_area(a) for a in extract_areas(alert_obj))


def is_official_beready_alert(alert_obj: dict[str, Any]) -> bool:
    return any(is_beready_area(a) for a in extract_areas(alert_obj))


def is_all_clear_event(alert_obj: dict[str, Any]) -> bool:
    text = alert_text(alert_obj)
    cat = str(alert_obj.get("cat") or "").strip()
    if cat == "13":
        return True
    return any(x in text for x in [
        "יציאה מהמרחב המוגן", "ניתן לצאת מהמרחב המוגן", "אפשר לצאת מהמרחב המוגן", "האירוע הסתיים",
        "אירוע הסתיים", "all clear", "end of event", "return to routine"
    ])


def infer_threat_type(alert_obj: dict[str, Any]) -> str | None:
    text = alert_text(alert_obj)
    cat = str(alert_obj.get("cat") or "").strip()
    if cat == "1":
        return "rocket"
    if cat == "6":
        return "hostile_aircraft"
    if any(x in text for x in ["כלי טיס עוין", "חדירת כלי טיס", "hostile aircraft", "uav", "drone"]):
        return "hostile_aircraft"
    if any(x in text for x in ["ירי רקטות", "ירי טילים", "ירי רקטות וטילים", "rocket", "missile"]):
        return "rocket"
    return None


def is_actionable_threat(alert_obj: dict[str, Any]) -> bool:
    if not alert_obj:
        return False
    if is_all_clear_event(alert_obj) or is_early_warning(alert_obj):
        return False
    return infer_threat_type(alert_obj) in {"rocket", "hostile_aircraft"}


def make_alert_group_id(alert: dict[str, Any], ts: int, threat_type: str) -> str:
    alert_id = str(alert.get("id") or "").strip()
    if alert_id:
        return f"id:{alert_id}"
    title = str(alert.get("title") or "").strip().lower()
    desc = str(alert.get("desc") or "").strip().lower()
    cat = str(alert.get("cat") or "").strip().lower()
    bucket = int(ts // 60000)
    return f"derived:{threat_type}|{cat}|{title}|{desc}|{bucket}"


def resolve_operational_corridor(area: str, meta: dict[str, Any]) -> str:
    normalized_area = normalize_area_name(area)
    distance_km = haversine_km({"lat": meta["lat"], "lon": meta["lon"]}, HAIFA_POINT)
    source_corridor = str(meta.get("corridor") or "").strip().lower()
    lat = float(meta.get("lat") or 0)
    if normalized_area in NORTH_BORDER_AREAS or lat >= GEOGRAPHY["NORTH_BORDER_LAT"] or distance_km >= GEOGRAPHY["PRE_HARD_BLOCK_KM"]:
        return "north_border"
    if source_corridor in {"coast", "krayot"} and distance_km <= GEOGRAPHY["HAIFA_CORRIDOR_MAX_KM"]:
        return "haifa_corridor"
    return "other"


def event_decay_factor(age_ms: int) -> float:
    if age_ms <= 60_000:
        return 1.00
    if age_ms <= 3 * 60_000:
        return 0.80
    if age_ms <= 5 * 60_000:
        return 0.55
    if age_ms <= 8 * 60_000:
        return 0.30
    if age_ms <= 12 * 60_000:
        return 0.18
    return 0.08


def build_events(history_items: list[dict[str, Any]], zones_map: dict[str, Any]) -> list[dict[str, Any]]:
    now = int(time.time() * 1000)
    processed: set[str] = set()
    events: list[dict[str, Any]] = []

    def recent_duplicate_locality_exists(area: str, threat_type: str, timestamp: int) -> bool:
        for e in events:
            if e["area"] == area and e["type"] == threat_type and abs(e["timestamp"] - timestamp) <= LOCALITY_DEDUP_MS:
                return True
        return False

    for item in history_items:
        ts = int(item.get("ts") or 0)
        if not ts or (now - ts) > HISTORY_WINDOW_MS:
            continue
        dedup_id = f"{ts}:{json.dumps(item.get('alert') or {}, ensure_ascii=False, sort_keys=True)}"
        if dedup_id in processed:
            continue
        processed.add(dedup_id)

        alert = item.get("alert") or {}
        areas = extract_areas(alert)

        if is_all_clear_event(alert):
            area_set = set(areas)
            events[:] = [e for e in events if e["area"] not in area_set]
            continue

        if is_official_early_warning(item) and is_official_haifa_alert(alert):
            continue
        if is_official_haifa_alert(alert) and not is_early_warning(item):
            continue
        if not is_actionable_threat(alert):
            continue

        threat_type = infer_threat_type(alert)
        if not threat_type or not areas:
            continue

        alert_group_id = make_alert_group_id(alert, ts, threat_type)
        for area in areas:
            meta = get_area_meta(area, zones_map)
            if not meta or is_noise_zone(area):
                continue
            if recent_duplicate_locality_exists(area, threat_type, ts):
                continue
            events.append({
                "area": area,
                "type": threat_type,
                "timestamp": ts,
                "alertGroupId": alert_group_id,
                "coords": {"lat": meta["lat"], "lon": meta["lon"]},
                "weight": float(meta.get("weight", 0.5)),
                "corridor": resolve_operational_corridor(area, meta),
                "sourceCorridor": meta.get("corridor") or "other",
                "track": meta.get("track"),
                "trackOrder": meta.get("trackOrder"),
                "distanceKm": haversine_km({"lat": meta["lat"], "lon": meta["lon"]}, HAIFA_POINT),
            })

    active = []
    for e in events:
        age_ms = now - e["timestamp"]
        decay = event_decay_factor(age_ms)
        if decay > 0:
            x = dict(e)
            x["ageMs"] = age_ms
            x["decay"] = decay
            active.append(x)
    return active


def weighted_unique_alert_count(events: list[dict[str, Any]]) -> int:
    return len({e["alertGroupId"] for e in events if e.get("alertGroupId")})


def nearest_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return min(events, key=lambda e: e["distanceKm"]) if events else None


def latest_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(events, key=lambda e: e["timestamp"]) if events else None


def latest_event_ts(events: list[dict[str, Any]], threat_type: str | None = None) -> int:
    relevant = [e["timestamp"] for e in events if threat_type is None or e.get("type") == threat_type]
    return max(relevant) if relevant else 0


def state_hold_active(reference_ts: int, hold_ms: int, now_ts: int) -> bool:
    return reference_ts > 0 and (now_ts - reference_ts) <= hold_ms


def transition_computed_state(engine_state: EngineState, next_state: str, now_ts: int) -> None:
    if engine_state.computed_state != next_state:
        engine_state.computed_state = next_state
        engine_state.computed_state_since_ts = now_ts


def official_hold_active(engine_state: EngineState, now_ts: int) -> bool:
    return state_hold_active(
        int(engine_state.last_official_alert_ts or 0),
        STATE_TIMEOUT_MS["POST_ALERT_HIGH"],
        now_ts,
    )


def merge_display_state(official_state: str | None, computed_state: str, engine_state: EngineState, now_ts: int) -> str:
    if official_state:
        return official_state
    if official_hold_active(engine_state, now_ts):
        return "POST_ALERT_HIGH"
    return computed_state


def build_cluster_score(events: list[dict[str, Any]]) -> dict[str, int]:
    now = int(time.time() * 1000)
    recent = [e for e in events if (now - e["timestamp"]) <= CLUSTER_WINDOW_MS]
    unique_areas = len({e["area"] for e in recent})
    unique_groups = len({e["alertGroupId"] for e in recent if e.get("alertGroupId")})
    score = 0
    if unique_groups >= 10 and unique_areas >= 6:
        score = 18
    elif unique_groups >= 6 and unique_areas >= 4:
        score = 12
    elif unique_groups >= 4 and unique_areas >= 3:
        score = 7
    return {"score": score, "uniqueAreas": unique_areas, "uniqueGroups": unique_groups}


def score_distance_for_rocket(distance_km: float, weight: float = 1.0) -> float:
    if distance_km < 12:
        base = 24
    elif distance_km < 20:
        base = 18
    elif distance_km < 35:
        base = 12
    elif distance_km < 50:
        base = 7
    else:
        base = 2
    return base * weight


def score_distance_for_uav(distance_km: float, weight: float = 1.0) -> float:
    if distance_km < 10:
        base = 30
    elif distance_km < 18:
        base = 24
    elif distance_km < 30:
        base = 18
    elif distance_km < 45:
        base = 11
    else:
        base = 4
    return base * weight


def build_rocket_score(events: list[dict[str, Any]]) -> dict[str, Any]:
    rockets = [e for e in events if e["type"] == "rocket"]
    if not rockets:
        return {
            "score": 0, "components": {}, "reasons": [],
            "reasoningText": "אין כרגע פעילות רקטית רלוונטית לחיפה",
            "technicalText": "No active rocket factors",
        }
    unique_count = weighted_unique_alert_count(rockets)
    nearest = nearest_event(rockets)
    intensity = min(sum(4 * e["decay"] * e["weight"] for e in rockets), 24)
    proximity = min(score_distance_for_rocket(nearest["distanceKm"], nearest["weight"]) if nearest else 0, 24)
    spread_areas = len({e["area"] for e in rockets})
    spread = 20 if unique_count >= 10 and spread_areas >= 6 else 14 if unique_count >= 7 and spread_areas >= 4 else 8 if unique_count >= 4 and spread_areas >= 3 else 0
    most_recent_ts = max(e["timestamp"] for e in rockets)
    oldest_ts = min(e["timestamp"] for e in rockets)
    duration_min = (most_recent_ts - oldest_ts) / 60000
    persistence = 12 if duration_min >= 6 else 7 if duration_min >= 3 else 4 if duration_min >= 1.5 else 0
    coastal_bias = 8 if any(e["corridor"] in {"coast", "krayot"} for e in rockets) else 0
    cluster = build_cluster_score(rockets)["score"]
    total = min(intensity + proximity + spread + persistence + coastal_bias + cluster, 100)
    reasons = []
    if intensity > 0: reasons.append("רצף ירי בצפון")
    if proximity >= 12: reasons.append("ירי קרוב יחסית לחיפה")
    if spread >= 8: reasons.append("גל רחב של אזורי התרעה")
    if persistence >= 7: reasons.append("ירי מתמשך")
    if coastal_bias > 0: reasons.append("מעורבות של ציר חוף/קריות")
    if cluster > 0: reasons.append("אשכול התרעות מהיר")
    technical = []
    if intensity > 0: technical.append(f"Intensity: {round(intensity)}")
    if proximity > 0: technical.append(f"Proximity: {round(proximity)}")
    if spread > 0: technical.append(f"Spread: {round(spread)}")
    if persistence > 0: technical.append(f"Persistence: {round(persistence)}")
    if coastal_bias > 0: technical.append(f"Coastal bias: {round(coastal_bias)}")
    if cluster > 0: technical.append(f"Cluster: {round(cluster)}")
    return {
        "score": total,
        "components": {"intensity": intensity, "proximity": proximity, "spread": spread, "persistence": persistence, "coastalBias": coastal_bias, "cluster": cluster},
        "reasons": reasons,
        "reasoningText": " | ".join(reasons) if reasons else "אין כרגע פעילות רקטית רלוונטית לחיפה",
        "technicalText": " | ".join(technical) if technical else "No active rocket factors",
    }


def build_geography_guard(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "hardBlockPre": False,
            "allFarNorth": False,
            "nearestDistanceKm": float("inf"),
            "anyHaifaCorridor": False,
            "allNorthOfBuffer": False,
            "hasKiryatHaimShmuel": False,
            "hasKrayotHit": False,
            "hasHaifaCoreHit": False,
            "corridorHitCount": 0,
        }
    nearest = nearest_event(events)
    nearest_km = nearest["distanceKm"] if nearest else float("inf")
    all_far_north = all(e["distanceKm"] >= GEOGRAPHY["TRAJECTORY_CAP_KM"] and float(e["coords"]["lat"]) >= GEOGRAPHY["NORTH_BUFFER_LAT"] for e in events)
    all_north_of_buffer = all(float(e["coords"]["lat"]) >= GEOGRAPHY["NORTH_BUFFER_LAT"] for e in events)
    any_haifa_corridor = any(e["corridor"] == "haifa_corridor" for e in events)
    has_kiryat_haim_shmuel = any(is_kiryat_haim_shmuel_area(e.get("area")) for e in events)
    has_krayot_hit = any(str(e.get("sourceCorridor") or "") == "krayot" for e in events)
    has_haifa_core_hit = any(str(e.get("sourceCorridor") or "") == "haifa" for e in events)
    corridor_hit_count = len([e for e in events if e["corridor"] == "haifa_corridor"])
    hard_block_pre = nearest_km >= GEOGRAPHY["PRE_HARD_BLOCK_KM"] and not any_haifa_corridor
    return {
        "hardBlockPre": hard_block_pre,
        "allFarNorth": all_far_north,
        "nearestDistanceKm": nearest_km,
        "anyHaifaCorridor": any_haifa_corridor,
        "allNorthOfBuffer": all_north_of_buffer,
        "hasKiryatHaimShmuel": has_kiryat_haim_shmuel,
        "hasKrayotHit": has_krayot_hit,
        "hasHaifaCoreHit": has_haifa_core_hit,
        "corridorHitCount": corridor_hit_count,
    }


def build_geography_penalty(geography: dict[str, Any], trajectory: dict[str, Any] | None) -> dict[str, float]:
    nearest_km = float(geography.get("nearestDistanceKm", float("inf")))
    if nearest_km <= 18:
        distance_factor = 1.00
    elif nearest_km <= 22:
        distance_factor = 0.94
    elif nearest_km <= 30:
        distance_factor = 0.80
    elif nearest_km <= 36:
        distance_factor = 0.64
    elif nearest_km <= 45:
        distance_factor = 0.50
    else:
        distance_factor = 0.38
    latitude_factor = 0.74 if geography.get("allFarNorth") else 0.88 if geography.get("allNorthOfBuffer") else 1.00
    corridor_factor = 1.00 if geography.get("anyHaifaCorridor") else 0.84
    trajectory_quality_factor = 1.00
    if not trajectory or trajectory.get("score", 0) <= 0:
        trajectory_quality_factor = 0.72 if geography.get("allFarNorth") else 0.86
    elif trajectory.get("score", 0) < 10:
        trajectory_quality_factor = 0.92
    proximity_multiplier = max(0.22, min(1.0, distance_factor * (0.82 if geography.get("allFarNorth") else 1) * (1 if geography.get("anyHaifaCorridor") else 0.93)))
    direction_multiplier = max(0.18, min(1.0, distance_factor * (0.70 if geography.get("allFarNorth") else 1) * (1 if geography.get("anyHaifaCorridor") else 0.90) * trajectory_quality_factor))
    trajectory_multiplier = max(0.20, min(1.0, distance_factor * latitude_factor * corridor_factor))
    total_multiplier = max(0.24, min(1.0, distance_factor * latitude_factor * corridor_factor * trajectory_quality_factor))
    return {
        "nearestKm": nearest_km,
        "distanceFactor": distance_factor,
        "latitudeFactor": latitude_factor,
        "corridorFactor": corridor_factor,
        "trajectoryQualityFactor": trajectory_quality_factor,
        "proximityMultiplier": proximity_multiplier,
        "directionMultiplier": direction_multiplier,
        "trajectoryMultiplier": trajectory_multiplier,
        "totalMultiplier": total_multiplier,
    }


def build_trajectory_analysis(uavs: list[dict[str, Any]]) -> dict[str, Any]:
    now = int(time.time() * 1000)
    recent = sorted([e for e in uavs if (now - e["timestamp"]) <= TRAJECTORY_WINDOW_MS], key=lambda e: e["timestamp"])
    if len(recent) < 2:
        return {"score": 0, "rawScore": 0, "matchedTrack": None, "progressionSteps": 0, "consistentSteps": 0, "timeConsistency": 0, "possibleApproach": "אין כרגע מסלול גישה ברור", "technicalText": "No usable trajectory", "line": []}
    progression_steps = 0
    consistent_steps = 0
    time_consistency = 0
    matched_track = None
    line = []
    for i in range(1, len(recent)):
        prev = recent[i - 1]
        cur = recent[i]
        if not prev.get("track") or not cur.get("track") or prev.get("track") != cur.get("track"):
            continue
        matched_track = cur.get("track")
        line.append([prev["coords"]["lat"], prev["coords"]["lon"]])
        if i == len(recent) - 1:
            line.append([cur["coords"]["lat"], cur["coords"]["lon"]])
        prev_order = prev.get("trackOrder")
        cur_order = cur.get("trackOrder")
        if isinstance(prev_order, (int, float)) and isinstance(cur_order, (int, float)):
            delta = prev_order - cur_order
            if 0 < delta <= 30:
                progression_steps += 1
                consistent_steps += 1
            elif 30 < delta <= 55:
                progression_steps += 1
        dt = cur["timestamp"] - prev["timestamp"]
        if 20_000 <= dt <= 4 * 60_000:
            time_consistency += 1
    raw_score = 0
    raw_score += 28 if progression_steps >= 4 else 20 if progression_steps >= 3 else 12 if progression_steps >= 2 else 5 if progression_steps >= 1 else 0
    raw_score += 14 if consistent_steps >= 3 else 9 if consistent_steps >= 2 else 4 if consistent_steps >= 1 else 0
    raw_score += 10 if time_consistency >= 3 else 6 if time_consistency >= 2 else 3 if time_consistency >= 1 else 0
    geo = build_geography_guard(recent)
    penalty = build_geography_penalty(geo, {"score": raw_score})
    adjusted = min(raw_score * penalty["trajectoryMultiplier"], 40)
    possible = "אין כרגע מסלול גישה ברור"
    if matched_track == "coast" and progression_steps >= 2 and geo["anyHaifaCorridor"] and geo["nearestDistanceKm"] <= GEOGRAPHY["TRAJECTORY_CAP_KM"] and adjusted >= 10:
        possible = "Possible approach: coastal descent toward Haifa"
    elif matched_track == "inland" and progression_steps >= 2 and geo["nearestDistanceKm"] <= GEOGRAPHY["TRAJECTORY_CAP_KM"] and adjusted >= 10:
        possible = "Possible approach: inland descent toward Haifa"
    technical = [
        f"Track: {matched_track or 'none'}",
        f"Progression: {progression_steps}",
        f"Consistency: {consistent_steps}",
        f"Time consistency: {time_consistency}",
        f"Raw trajectory: {round(raw_score)}",
        f"Adjusted trajectory: {round(adjusted)}",
        f"Trajectory penalty: {penalty['trajectoryMultiplier']:.2f}",
        f"Nearest km: {round(geo['nearestDistanceKm']) if math.isfinite(geo['nearestDistanceKm']) else 'n/a'}",
        f"Haifa corridor: {'yes' if geo['anyHaifaCorridor'] else 'no'}",
    ]
    return {"score": round(adjusted), "rawScore": round(raw_score), "matchedTrack": matched_track, "progressionSteps": progression_steps, "consistentSteps": consistent_steps, "timeConsistency": time_consistency, "possibleApproach": possible, "technicalText": " | ".join(technical), "line": line}


def build_uav_score(events: list[dict[str, Any]]) -> dict[str, Any]:
    uavs = sorted([e for e in events if e["type"] == "hostile_aircraft"], key=lambda e: e["timestamp"])
    if not uavs:
        return {"score": 0, "components": {}, "reasons": [], "reasoningText": "אין כרגע פעילות כלי טיס רלוונטית לחיפה", "technicalText": "No active UAV factors", "trajectory": None, "geography": build_geography_guard([]), "penalty": build_geography_penalty({}, None)}
    unique_count = weighted_unique_alert_count(uavs)
    nearest = nearest_event(uavs)
    geography = build_geography_guard(uavs)
    intensity = min(sum(7 * e["decay"] * e["weight"] for e in uavs), 28)
    proximity = min(score_distance_for_uav(nearest["distanceKm"], nearest["weight"]) if nearest else 0, 30)
    progression = 0
    for i in range(1, len(uavs)):
        if uavs[i]["distanceKm"] < uavs[i - 1]["distanceKm"] - 1.0:
            progression += 1
    direction = 24 if progression >= 4 else 18 if progression >= 3 else 11 if progression >= 2 else 5 if progression >= 1 else 0
    corridor_hits = len([e for e in uavs if e["corridor"] == "haifa_corridor"])
    corridor = 10 if corridor_hits >= 3 else 6 if corridor_hits >= 2 else 3 if corridor_hits >= 1 else 0
    pace = 0
    if len(uavs) >= 2:
        deltas = [uavs[i]["timestamp"] - uavs[i - 1]["timestamp"] for i in range(1, len(uavs))]
        avg_delta = sum(deltas) / len(deltas)
        pace = 8 if avg_delta <= 90_000 else 5 if avg_delta <= 180_000 else 0
    unique_areas = len({e["area"] for e in uavs})
    multi_area = 12 if unique_count >= 5 and unique_areas >= 4 else 7 if unique_count >= 3 and unique_areas >= 3 else 0
    trajectory = build_trajectory_analysis(uavs)
    penalty = build_geography_penalty(geography, trajectory)
    proximity *= penalty["proximityMultiplier"]
    direction *= penalty["directionMultiplier"]
    total = intensity + proximity + direction + corridor + pace + multi_area + trajectory["score"]
    total *= penalty["totalMultiplier"]
    total = min(total, 100)
    reasons = []
    if intensity > 0: reasons.append("רצף אירועי כלי טיס")
    if proximity >= 12: reasons.append("אירוע קרוב יחסית לחיפה")
    if direction >= 11: reasons.append("התקרבות יחסית לחיפה")
    if corridor >= 6: reasons.append("מסלול עם קשר לציר חיפה")
    if pace > 0: reasons.append("קצב אירועים מהיר")
    if multi_area > 0: reasons.append("פריסה על כמה יישובים")
    if trajectory["score"] >= 10: reasons.append("trajectory אפשרי לכיוון חיפה")
    technical = []
    if intensity > 0: technical.append(f"Intensity: {round(intensity)}")
    if proximity > 0: technical.append(f"Proximity(adj): {round(proximity)}")
    if direction > 0: technical.append(f"Direction(adj): {round(direction)}")
    if corridor > 0: technical.append(f"Corridor: {round(corridor)}")
    if pace > 0: technical.append(f"Pace: {round(pace)}")
    if multi_area > 0: technical.append(f"Multi-area: {round(multi_area)}")
    if trajectory["score"] > 0: technical.append(f"Trajectory: {round(trajectory['score'])}")
    technical.append(f"Total penalty: {penalty['totalMultiplier']:.2f}")
    return {
        "score": round(total),
        "components": {"intensity": intensity, "proximity": proximity, "direction": direction, "corridor": corridor, "pace": pace, "multiArea": multi_area, "trajectory": trajectory["score"]},
        "reasons": reasons,
        "reasoningText": " | ".join(reasons) if reasons else "אין כרגע פעילות כלי טיס רלוונטית לחיפה",
        "technicalText": " | ".join(technical) if technical else "No active UAV factors",
        "trajectory": trajectory,
        "geography": geography,
        "penalty": penalty,
    }


def derive_state_with_hysteresis(
    rocket_score: float,
    uav_score: float,
    prev_state: str,
    geography: dict[str, Any],
    rocket: dict[str, Any] | None = None,
    uav: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    engine_state: EngineState | None = None,
    now_ts: int | None = None,
) -> str:
    rocket = rocket or {}
    uav = uav or {}
    events = events or []
    now_ts = int(now_ts or (time.time() * 1000))

    rocket_components = rocket.get("components") or {}
    uav_components = uav.get("components") or {}
    uav_traj = (uav.get("trajectory") or {})

    rocket_proximity = float(rocket_components.get("proximity", 0) or 0)
    rocket_coastal = float(rocket_components.get("coastalBias", 0) or 0)
    rocket_cluster = float(rocket_components.get("cluster", 0) or 0)

    uav_proximity = float(uav_components.get("proximity", 0) or 0)
    uav_corridor = float(uav_components.get("corridor", 0) or 0)
    uav_direction = float(uav_components.get("direction", 0) or 0)
    uav_trajectory = float(uav_components.get("trajectory", 0) or 0)

    any_haifa_corridor = bool(geography.get("anyHaifaCorridor"))
    nearest_km = float(geography.get("nearestDistanceKm", float("inf")))
    has_kiryat_haim_shmuel = bool(geography.get("hasKiryatHaimShmuel"))
    has_krayot_hit = bool(geography.get("hasKrayotHit"))
    has_haifa_core_hit = bool(geography.get("hasHaifaCoreHit"))
    corridor_hit_count = int(geography.get("corridorHitCount", 0) or 0)
    hard_block_pre = bool(geography.get("hardBlockPre"))
    latest_any_ts = latest_event_ts(events)
    latest_uav_ts = latest_event_ts(events, "hostile_aircraft")
    ready_hold = state_hold_active(latest_any_ts, STATE_TIMEOUT_MS["READY"], now_ts)
    high_hold = state_hold_active(latest_any_ts, STATE_TIMEOUT_MS["HIGH"], now_ts)
    pre_hold = state_hold_active(latest_uav_ts or latest_any_ts, STATE_TIMEOUT_MS["PRE_SHELTER"], now_ts)

    high_relevance = (
        any_haifa_corridor
        or nearest_km <= 30
        or rocket_proximity >= 8
        or rocket_coastal >= 6
        or rocket_cluster >= 8
        or uav_proximity >= 8
        or uav_corridor >= 6
        or uav_direction >= 11
        or uav_trajectory >= 10
        or uav_traj.get("progressionSteps", 0) >= 2
    )

    if prev_state == "POST_ALERT_HIGH":
        prev_state = "HIGH" if high_relevance else "READY"

    ready_candidate = (
        uav_score >= HYSTERESIS["READY_UP"]
        or rocket_score >= HYSTERESIS["READY_UP"]
    )

    high_candidate = (
        ((uav_score >= HYSTERESIS["HIGH_UP"] or rocket_score >= HYSTERESIS["HIGH_UP"]) and high_relevance)
        or (uav_traj.get("progressionSteps", 0) >= 2 and any_haifa_corridor)
        or (corridor_hit_count >= 1 and uav_direction >= 5 and nearest_km <= 22)
        or (has_krayot_hit and uav_score >= 28)
        or (has_haifa_core_hit and uav_score >= 28)
    )

    pre_candidate = (
        has_kiryat_haim_shmuel or
        ((uav_score >= HYSTERESIS["PRE_UP"] or rocket_score >= 82) and not hard_block_pre) or
        (
            not hard_block_pre and
            (has_krayot_hit or has_haifa_core_hit) and
            (uav_traj.get("progressionSteps", 0) >= 2 or uav_direction >= 11)
        ) or
        (
            not hard_block_pre and
            any_haifa_corridor and
            nearest_km <= 18 and
            corridor_hit_count >= 2 and
            uav_score >= 42
        ) or
        (rocket_score >= 82) or
        (uav_score >= 58 and rocket_score >= 48 and not hard_block_pre)
    )

    if prev_state == "PRE_SHELTER":
        if pre_candidate or (pre_hold and high_relevance and not hard_block_pre):
            return "PRE_SHELTER"
        if high_candidate or ((uav_score >= HYSTERESIS["HIGH_DOWN"] or rocket_score >= HYSTERESIS["HIGH_DOWN"]) and high_hold and high_relevance):
            return "HIGH"
        if ready_candidate or ready_hold or uav_score >= HYSTERESIS["READY_DOWN"] or rocket_score >= HYSTERESIS["READY_DOWN"]:
            return "READY"
        return "NORMAL"

    if prev_state == "HIGH":
        if pre_candidate:
            return "PRE_SHELTER"
        if high_candidate or ((uav_score >= HYSTERESIS["HIGH_DOWN"] or rocket_score >= HYSTERESIS["HIGH_DOWN"]) and high_hold and high_relevance):
            return "HIGH"
        if ready_candidate or ready_hold or uav_score >= HYSTERESIS["READY_DOWN"] or rocket_score >= HYSTERESIS["READY_DOWN"]:
            return "READY"
        return "NORMAL"

    if prev_state == "READY":
        if pre_candidate:
            return "PRE_SHELTER"
        if high_candidate:
            return "HIGH"
        if ready_candidate or ready_hold or uav_score >= HYSTERESIS["READY_DOWN"] or rocket_score >= HYSTERESIS["READY_DOWN"]:
            return "READY"
        return "NORMAL"

    if pre_candidate:
        return "PRE_SHELTER"
    if high_candidate:
        return "HIGH"
    if ready_candidate:
        return "READY"
    return "NORMAL"


def build_confidence(events: list[dict[str, Any]], rocket: dict[str, Any], uav: dict[str, Any]) -> str:
    if not events:
        return "LOW"
    score = 0
    unique_areas = len({e["area"] for e in events})
    score += 2 if unique_areas >= 5 else 1 if unique_areas >= 3 else 0
    progression = (uav.get("trajectory") or {}).get("progressionSteps", 0)
    score += 2 if progression >= 3 else 1 if progression >= 2 else 0
    if (uav.get("trajectory") or {}).get("timeConsistency", 0) >= 2:
        score += 1
    score += 2 if uav["score"] >= 65 else 1 if uav["score"] >= 45 else 0
    if rocket["score"] >= 40:
        score += 1
    if uav.get("geography", {}).get("allFarNorth"):
        score -= 1
    if uav.get("geography", {}).get("hardBlockPre"):
        score -= 2
    if not uav.get("geography", {}).get("anyHaifaCorridor"):
        score -= 1
    if uav.get("penalty", {}).get("totalMultiplier", 1) < 0.65:
        score -= 1
    return "HIGH" if score >= 5 else "MEDIUM" if score >= 3 else "LOW"


def build_eta(uav: dict[str, Any], nearest: dict[str, Any] | None) -> str:
    traj = uav.get("trajectory") or {}
    if traj.get("progressionSteps", 0) < 2 or not nearest:
        return "—"
    if uav.get("geography", {}).get("allFarNorth") or uav.get("geography", {}).get("hardBlockPre"):
        return "—"
    d = nearest["distanceKm"]
    if d <= 12 and traj.get("timeConsistency", 0) >= 2:
        return "1–2 min"
    if d <= 22 and traj.get("timeConsistency", 0) >= 1:
        return "2–4 min"
    if d <= 30:
        return "4–6 min"
    return "—"


def build_simple_status(state: str) -> dict[str, str]:
    mapping = {
        "READY": {
            "title": "יש פעילות שדורשת ערנות",
            "body": "המערכת מזהה פעילות אזורית שמצדיקה ערנות, אבל בלי אינדיקציה חזקה מספיק לאיום מתקרב לחיפה.",
        },
        "HIGH": {
            "title": "יש פעילות חריגה רלוונטית",
            "body": "המערכת מזהה כמה אינדיקציות יחד שמחייבות יותר תשומת לב ביחס לחיפה.",
        },
        "PRE_SHELTER": {
            "title": "כדאי להתקרב למרחב מוגן",
            "body": "המערכת מזהה אינדיקציה מחושבת חזקה יותר, כולל trajectory אפשרי לכיוון חיפה או שילוב חריג של כמה גורמים.",
        },
        "POST_ALERT_HIGH": {
            "title": "\u05d4\u05d0\u05d9\u05e8\u05d5\u05e2 \u05e2\u05d3\u05d9\u05d9\u05df \u05d3\u05d5\u05e8\u05e9 \u05e2\u05e8\u05e0\u05d5\u05ea \u05d2\u05d1\u05d5\u05d4\u05d4",
            "body": "\u05d4\u05d9\u05d9\u05ea\u05d4 \u05d4\u05ea\u05e8\u05e2\u05d4 \u05e8\u05e9\u05de\u05d9\u05ea \u05e8\u05dc\u05d5\u05d5\u05e0\u05d8\u05d9\u05ea, \u05d5\u05d4\u05de\u05e2\u05e8\u05db\u05ea \u05e0\u05e9\u05d0\u05e8\u05ea \u05d6\u05de\u05e0\u05d9\u05ea \u05d1\u05de\u05e6\u05d1 \u05e2\u05e8\u05e0\u05d5\u05ea \u05d2\u05d1\u05d5\u05d4\u05d4 \u05d2\u05dd \u05d0\u05d7\u05e8\u05d9 \u05d4\u05e9\u05dc\u05d1 \u05d4\u05e8\u05e9\u05de\u05d9.",
        },
        "OFFICIAL_EARLY_WARNING": {
            "title": "התקבלה התרעה מוקדמת רשמית",
            "body": "זהו מצב רשמי של פיקוד העורף, נפרד לחלוטין מהחישוב של BeReady.",
        },
        "SHELTER_NOW": {
            "title": "צבע אדום",
            "body": "זהו מצב רשמי. פועלים מיד לפי הנחיות פיקוד העורף.",
        },
    }
    return mapping.get(state, {
        "title": "אין כרגע אינדיקציה חריגה לחיפה",
        "body": "המערכת לא מזהה כרגע פעילות שמצדיקה העלאת כוננות מחושבת לחיפה.",
    })


def build_state_reasoning(state: str, rocket: dict[str, Any], uav: dict[str, Any], confidence: str, eta: str) -> str:
    if state == "PRE_SHELTER":
        if uav["score"] >= 68 and (uav.get("trajectory") or {}).get("progressionSteps", 0) >= 2:
            return f"PRE_SHELTER נקבע בעיקר בגלל UAV גבוה ({round(uav['score'])}), trajectory עקבי ו־confidence {confidence}. ETA: {eta}."
        if uav["score"] >= 58 and rocket["score"] >= 48:
            return f"PRE_SHELTER נקבע בגלל שילוב של UAV ({round(uav['score'])}) ו־Rocket ({round(rocket['score'])})."
        if rocket["score"] >= 82:
            return f"PRE_SHELTER נקבע בגלל Rocket Score חריג מאוד ({round(rocket['score'])})."
        return "PRE_SHELTER נקבע לפי שילוב חריג של אינדיקציות."
    if state == "POST_ALERT_HIGH":
        return "POST_ALERT_HIGH \u05e0\u05e7\u05d1\u05e2 \u05db\u05d9 \u05d4\u05d9\u05d9\u05ea\u05d4 \u05d4\u05ea\u05e8\u05e2\u05d4 \u05e8\u05e9\u05de\u05d9\u05ea \u05e8\u05dc\u05d5\u05d5\u05e0\u05d8\u05d9\u05ea \u05dc\u05d7\u05d9\u05e4\u05d4, \u05d5\u05d4\u05de\u05e2\u05e8\u05db\u05ea \u05e9\u05d5\u05de\u05e8\u05ea \u05d6\u05de\u05e0\u05d9\u05ea \u05e2\u05e8\u05e0\u05d5\u05ea \u05d2\u05d1\u05d5\u05d4\u05d4 \u05dc\u05e4\u05e0\u05d9 \u05d9\u05e8\u05d9\u05d3\u05d4 \u05d4\u05d3\u05e8\u05d2\u05ea\u05d9\u05ea."
    if state == "HIGH":
        return f"HIGH נקבע בעיקר על בסיס מנוע {'כלי טיס' if uav['score'] >= rocket['score'] else 'רקטות'} ({round(max(uav['score'], rocket['score']))}), confidence {confidence}."
    if state == "READY":
        if uav["score"] >= rocket["score"] and uav["score"] > 0:
            return f"READY נקבע בגלל פעילות התחלתית במנוע כלי טיס ({round(uav['score'])})."
        if rocket["score"] > 0:
            return f"READY נקבע בגלל פעילות אזורית במנוע רקטות ({round(rocket['score'])})."
        return "READY נקבע בגלל פעילות אזורית."
    if state == "NORMAL":
        return "לא זוהו אינדיקציות מספיקות להעלאת רמת הכוננות."
    return "המצב נקבע לפי מנגנון רשמי או לפי חישוב פנימי של BeReady."


def build_calculated_message(state: str, nearest: dict[str, Any] | None, rocket_score: int, uav_score: int) -> dict[str, str]:
    nearest_text = f"האירוע הקרוב ביותר: {nearest['area']} (~{round(nearest['distanceKm'])} ק״מ מחיפה)" if nearest else "לא זוהו אירועים קרובים רלוונטיים"
    mapping = {
        "READY": {
            "title": "יש פעילות שדורשת ערנות",
            "body": f"BeReady מזהה פעילות אזורית. Rocket Score: {rocket_score}, UAV Score: {uav_score}.",
            "nearestText": nearest_text
        },
        "HIGH": {
            "title": "יש אינדיקציות חריגות ביחס לחיפה",
            "body": f"BeReady מזהה הסלמה או אינדיקציות משמעותיות יותר. Rocket Score: {rocket_score}, UAV Score: {uav_score}.",
            "nearestText": nearest_text
        },
        "PRE_SHELTER": {
            "title": "כדאי להתקרב לכיוון המרחב המוגן",
            "body": "זהו מצב prediction מחושב של BeReady בלבד.",
            "nearestText": nearest_text
        },
        "POST_ALERT_HIGH": {
            "title": "\u05d4\u05d0\u05d9\u05e8\u05d5\u05e2 \u05e2\u05d3\u05d9\u05d9\u05df \u05d3\u05d5\u05e8\u05e9 \u05e2\u05e8\u05e0\u05d5\u05ea \u05d2\u05d1\u05d5\u05d4\u05d4",
            "body": "BeReady \u05e9\u05d5\u05de\u05e8 \u05d6\u05de\u05e0\u05d9\u05ea \u05e2\u05e8\u05e0\u05d5\u05ea \u05d2\u05d1\u05d5\u05d4\u05d4 \u05d0\u05d7\u05e8\u05d9 \u05d4\u05ea\u05e8\u05e2\u05d4 \u05e8\u05e9\u05de\u05d9\u05ea \u05db\u05d3\u05d9 \u05dc\u05d0 \u05dc\u05e8\u05d3\u05ea \u05de\u05d4\u05e8 \u05de\u05d3\u05d9.",
            "nearestText": nearest_text
        },
    }
    return mapping.get(state, {
        "title": "אין פעילות חריגה כרגע",
        "body": "לא זוהו כרגע אינדיקציות שמצדיקות העלאת כוננות מחושבת לחיפה.",
        "nearestText": nearest_text
    })

def active_now_text(events: list[dict[str, Any]]) -> str:
    latest = latest_event(events)
    if not latest:
        return "לא פעיל כרגע"
    diff = int(time.time() * 1000) - latest["timestamp"]
    if diff < ACTIVE_WINDOW_MS:
        return f"עדיין פעיל כעת — אירוע אחרון לפני {max(1, diff // 1000)} שניות"
    return "לא פעיל כרגע"


def recent_alerts_list(events: list[dict[str, Any]]) -> str:
    sorted_events = sorted(events, key=lambda e: e["timestamp"], reverse=True)
    lines = []
    seen = set()
    for e in sorted_events:
        key = f"{e['area']}|{e['timestamp']}|{e['type']}"
        if key in seen:
            continue
        seen.add(key)
        label = 'כטב"ם' if e["type"] == "hostile_aircraft" else "ירי"
        time_text = datetime.fromtimestamp(e["timestamp"] / 1000).strftime("%H:%M:%S")
        lines.append(f"{html.escape(e['area'])} — {label} — {time_text}")
        if len(lines) >= 6:
            break
    return "<br>".join(lines) if lines else "אין"


def build_map_points(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_events = sorted(events, key=lambda e: e["timestamp"])[-8:]
    out = []
    for e in sorted_events:
        out.append({
            "lat": e["coords"]["lat"],
            "lon": e["coords"]["lon"],
            "area": e["area"],
            "type": e["type"],
            "typeLabel": 'כטב"ם' if e["type"] == "hostile_aircraft" else "ירי",
            "timeText": datetime.fromtimestamp(e["timestamp"] / 1000).strftime("%H:%M:%S"),
        })
    return out


def build_snapshot(history_items: list[dict[str, Any]], status_obj: dict[str, Any], zones_map: dict[str, Any], engine_state: EngineState) -> dict[str, Any]:
    now_ts = int(time.time() * 1000)
    if not engine_state.computed_state_since_ts:
        engine_state.computed_state_since_ts = now_ts
    current_alert = status_obj.get("current_alert") or {}
    official_state: str | None = None
    if current_alert:
        if is_all_clear_event(current_alert) and is_official_beready_alert(current_alert):
            engine_state.last_official_alert_ts = 0
            engine_state.last_all_clear_ts = now_ts
        elif is_official_early_warning(current_alert) and is_official_haifa_alert(current_alert):
            official_state = "OFFICIAL_EARLY_WARNING"
            simple = build_simple_status("OFFICIAL_EARLY_WARNING")
            return {
                "state": "OFFICIAL_EARLY_WARNING", "riskScore": 0, "rocketScore": 0, "uavScore": 0, "confidence": "HIGH", "eta": "—",
                "possibleApproach": "מצב רשמי", "areas": extract_areas(current_alert), "reasons": ["התרעה מוקדמת רשמית של פיקוד העורף"],
                "nearest": None, "uniqueCount": 0, "activeText": "מצב רשמי פעיל כעת", "lastAlertsHtml": "התרעה מוקדמת רשמית",
                "clusterText": "מצב רשמי", "simpleTitle": simple["title"], "simpleBody": simple["body"],
                "stateReasoning": "המצב נקבע רשמית על ידי פיקוד העורף, נפרד מהמנוע המחושב.",
                "rocketReasoning": "מנוע הרקטות לא השתתף בקביעת המצב הרשמי.", "uavReasoning": "מנוע כלי הטיס לא השתתף בקביעת המצב הרשמי.",
                "rocketTechnical": "Official override", "uavTechnical": "Official override", "mapPoints": [], "uavTrackLine": [],
                "generatedAtTs": now_ts,
                "generatedAtIso": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "generatedAtText": datetime.now().strftime("%H:%M:%S"),
                "nearestText": "מצב רשמי.",
                "message": {"title": simple["title"], "body": simple["body"], "nearestText": "מצב רשמי."},
                "computedState": engine_state.computed_state,
                "officialState": official_state,
            }
        elif is_official_haifa_alert(current_alert) and not is_early_warning(current_alert):
            engine_state.last_official_alert_ts = now_ts
            official_state = "SHELTER_NOW"
            simple = build_simple_status("SHELTER_NOW")
            return {
                "state": "SHELTER_NOW", "riskScore": 0, "rocketScore": 0, "uavScore": 0, "confidence": "HIGH", "eta": "NOW",
                "possibleApproach": "התרעה רשמית בחיפה", "areas": extract_areas(current_alert), "reasons": ["התרעה רשמית רלוונטית לחיפה"],
                "nearest": None, "uniqueCount": 1, "activeText": "התרעה רשמית פעילה כעת", "lastAlertsHtml": "חיפה — עכשיו",
                "clusterText": "מצב רשמי", "simpleTitle": simple["title"], "simpleBody": simple["body"],
                "stateReasoning": "המצב נקבע רשמית על ידי פיקוד העורף, נפרד מהמנוע המחושב.",
                "rocketReasoning": "מנוע הרקטות לא השתתף בקביעת המצב הרשמי.", "uavReasoning": "מנוע כלי הטיס לא השתתף בקביעת המצב הרשמי.",
                "rocketTechnical": "Official override", "uavTechnical": "Official override", "mapPoints": [], "uavTrackLine": [],
                "generatedAtTs": now_ts,
                "generatedAtIso": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "generatedAtText": datetime.now().strftime("%H:%M:%S"),
                "nearestText": "מצב רשמי.",
                "message": {"title": simple["title"], "body": simple["body"], "nearestText": "מצב רשמי."},
                "computedState": engine_state.computed_state,
                "officialState": official_state,
            }

    dashboard_events = build_events(history_items, zones_map)
    events = dashboard_events
    if not events:
        dashboard_unique_count = weighted_unique_alert_count(dashboard_events)
        dashboard_unique_areas = len({e["area"] for e in dashboard_events})
        dashboard_nearest = nearest_event(dashboard_events)
        next_computed_state = derive_state_with_hysteresis(
            0,
            0,
            engine_state.computed_state,
            build_geography_guard([]),
            events=[],
            engine_state=engine_state,
            now_ts=now_ts,
        )
        transition_computed_state(engine_state, next_computed_state, now_ts)
        display_state = merge_display_state(None, engine_state.computed_state, engine_state, now_ts)
        display_simple = build_simple_status(display_state)
        display_message = build_calculated_message(display_state, dashboard_nearest, 0, 0)
        display_reasoning = build_state_reasoning(display_state, {"score": 0}, {"score": 0, "trajectory": {}}, "LOW", "—")
        return {
            "state": display_state, "riskScore": 0, "rocketScore": 0, "uavScore": 0, "confidence": "LOW", "eta": "—",
            "possibleApproach": "אין כרגע מסלול גישה ברור", "areas": [], "reasons": [], "nearest": None, "uniqueCount": 0,
            "activeText": active_now_text(dashboard_events), "lastAlertsHtml": recent_alerts_list(dashboard_events), "clusterText": f"{dashboard_unique_count} התרעות ייחודיות ב־{dashboard_unique_areas} יישובים",
            "simpleTitle": display_simple["title"], "simpleBody": display_simple["body"],
            "stateReasoning": display_reasoning, "rocketReasoning": "אין כרגע פעילות רקטית רלוונטית לחיפה",
            "uavReasoning": "אין כרגע פעילות כלי טיס רלוונטית לחיפה", "rocketTechnical": "No active rocket factors", "uavTechnical": "No active UAV factors",
            "mapPoints": build_map_points(dashboard_events), "uavTrackLine": [],
            "generatedAtTs": now_ts,
            "generatedAtIso": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "generatedAtText": datetime.now().strftime("%H:%M:%S"),
            "nearestText": display_message["nearestText"],
            "message": display_message,
            "computedState": engine_state.computed_state,
            "officialState": "POST_ALERT_HIGH" if official_hold_active(engine_state, now_ts) else None,
        }

    rocket = build_rocket_score(events)
    uav = build_uav_score(events)
    nearest = nearest_event(events)
    unique_count = weighted_unique_alert_count(events)
    unique_areas = len({e["area"] for e in events})
    geography = uav.get("geography") or build_geography_guard(events)

    next_computed_state = derive_state_with_hysteresis(
        rocket["score"],
        uav["score"],
        engine_state.computed_state,
        geography,
        rocket,
        uav,
        events,
        engine_state,
        now_ts,
    )
    transition_computed_state(engine_state, next_computed_state, now_ts)

    confidence = build_confidence(events, rocket, uav)
    eta = build_eta(uav, nearest)
    display_state = merge_display_state(None, engine_state.computed_state, engine_state, now_ts)
    simple = build_simple_status(display_state)
    state_reasoning = build_state_reasoning(display_state, rocket, uav, confidence, eta)
    message = build_calculated_message(display_state, nearest, round(rocket["score"]), round(uav["score"]))
    risk_score = max(rocket["score"], uav["score"])
    reasons = (uav["reasons"] + rocket["reasons"])[:8]
    areas = []
    for e in events:
        if e["area"] not in areas:
            areas.append(e["area"])
    areas = areas[:10]
    map_points = build_map_points(events)
    uav_track_line = ((uav.get("trajectory") or {}).get("line") or [])
    possible_approach = "אין כרגע מסלול גישה מספיק קרוב לחיפה" if geography.get("hardBlockPre") or geography.get("allFarNorth") else ((uav.get("trajectory") or {}).get("possibleApproach") or "אין כרגע מסלול גישה ברור")
    return {
        "state": display_state,
        "riskScore": round(risk_score),
        "rocketScore": round(rocket["score"]),
        "uavScore": round(uav["score"]),
        "confidence": confidence,
        "eta": eta,
        "possibleApproach": possible_approach,
        "areas": areas,
        "reasons": reasons,
        "nearest": nearest,
        "uniqueCount": unique_count,
        "activeText": active_now_text(events),
        "lastAlertsHtml": recent_alerts_list(events),
        "clusterText": f"{unique_count} התרעות ייחודיות ב־{unique_areas} יישובים",
        "simpleTitle": simple["title"],
        "simpleBody": simple["body"],
        "stateReasoning": state_reasoning,
        "rocketReasoning": rocket["reasoningText"],
        "uavReasoning": uav["reasoningText"],
        "rocketTechnical": rocket["technicalText"],
        "uavTechnical": uav["technicalText"],
        "mapPoints": map_points,
        "uavTrackLine": uav_track_line,
        "generatedAtTs": now_ts,
        "generatedAtIso": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "generatedAtText": datetime.now().strftime("%H:%M:%S"),
        "nearestText": message["nearestText"],
        "message": message,
        "computedState": engine_state.computed_state,
        "officialState": "POST_ALERT_HIGH" if official_hold_active(engine_state, now_ts) else None,
    }
