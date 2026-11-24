#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import html
import json
import os
import smtplib
import ssl
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

BASE_DIR = Path(os.environ.get("OREF_MONITOR_BASE_DIR", "/opt/oref-monitor"))
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "beready_mailer_state.json"

LISTEN_HOST = os.environ.get("BEREADY_MAILER_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("BEREADY_MAILER_PORT", "8788"))

ENABLE_MAIL = os.environ.get("BEREADY_ENABLE_MAIL", "false").strip().lower() == "true"

SMTP_HOST = os.environ.get("BEREADY_SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("BEREADY_SMTP_PORT", "587"))
SMTP_SECURITY = os.environ.get("BEREADY_SMTP_SECURITY", "starttls").strip().lower()
SMTP_USER = os.environ.get("BEREADY_SMTP_USER", "").strip()
SMTP_PASS = os.environ.get("BEREADY_SMTP_PASS", "").strip()
SMTP_FROM = os.environ.get("BEREADY_SMTP_FROM", "").strip()
SMTP_TO = os.environ.get("BEREADY_SMTP_TO", "").strip()
SUBJECT_PREFIX = os.environ.get("BEREADY_MAIL_SUBJECT_PREFIX", "BeReady").strip() or "BeReady"
MAILER_MIN_INTERVAL_SEC = int(os.environ.get("BEREADY_MAILER_MIN_INTERVAL_SEC", "20"))


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_state(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    import threading
    import time

    tmp = STATE_FILE.with_name(
        f"{STATE_FILE.name}.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.tmp"
    )
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def state_color(state: str) -> str:
    return {
        "SHELTER_NOW": "#ff4d6d",
        "OFFICIAL_EARLY_WARNING": "#55c1ff",
        "PRE_SHELTER": "#ff8fab",
        "POST_ALERT_HIGH": "#ff7b54",
        "HIGH": "#f59e0b",
        "READY": "#9d4edd",
        "NORMAL": "#7b2cbf",
    }.get(state, "#7b2cbf")


def mail_transition_key(snapshot: dict) -> str:
    message = snapshot.get("message") or {}
    return json.dumps({
        "state": snapshot.get("state", "NORMAL"),
        "simpleTitle": snapshot.get("simpleTitle", ""),
        "simpleBody": snapshot.get("simpleBody", ""),
        "messageTitle": message.get("title", ""),
        "messageBody": message.get("body", ""),
    }, ensure_ascii=False, sort_keys=True)


def compact_areas(snapshot: dict) -> str:
    areas = snapshot.get("areas") or []
    if not areas:
        return "אין"
    trimmed = [html.escape(str(x)) for x in areas[:5]]
    suffix = "" if len(areas) <= 5 else f" ועוד {len(areas) - 5}"
    return " • ".join(trimmed) + suffix


def compact_reasons(snapshot: dict) -> str:
    reasons = snapshot.get("reasons") or []
    if not reasons:
        return "אין אינדיקציות חריגות כרגע"
    return "<br>".join(html.escape(str(x)) for x in reasons[:4])


def render_html_email(s: dict) -> str:
    accent = state_color(str(s.get("state", "NORMAL")))
    generated_at = html.escape(str(s.get("generatedAtText") or "—"))
    nearest_text = html.escape(str(s.get("nearestText") or (s.get("message") or {}).get("nearestText") or "לא זוהו אירועים קרובים רלוונטיים"))
    message = s.get("message") or {}
    message_title = html.escape(str(message.get("title") or s.get("simpleTitle") or ""))
    message_body = html.escape(str(message.get("body") or s.get("simpleBody") or ""))
    possible_approach = html.escape(str(s.get("possibleApproach") or "אין כרגע מסלול גישה ברור"))
    state_reasoning = html.escape(str(s.get("stateReasoning") or "אין פירוט"))
    confidence = html.escape(str(s.get("confidence") or "LOW"))
    eta = html.escape(str(s.get("eta") or "—"))
    active_text = html.escape(str(s.get("activeText") or "לא פעיל כרגע"))
    areas_html = compact_areas(s)
    reasons_html = compact_reasons(s)

    return f'''<!doctype html>
<html lang="he" dir="rtl">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:24px;background:#0b0814;font-family:Arial,sans-serif;color:#f7f1ff;">
  <div style="max-width:760px;margin:0 auto;background:#161022;border:1px solid #33204d;border-radius:24px;padding:24px;">
    <div style="font-size:28px;font-weight:700;margin-bottom:8px;">BeReady Status Change</div>
    <div style="color:#ccb8f5;margin-bottom:24px;">נשלח רק בשינוי סטטוס. זמן חישוב backend: {generated_at}</div>

    <div style="background:#201631;border-radius:18px;padding:18px;margin-bottom:18px;border-right:6px solid {accent};">
      <div style="font-size:13px;color:#ccb8f5;">Current state</div>
      <div style="font-size:30px;font-weight:700;margin-top:6px;">{html.escape(str(s.get('state', 'NORMAL')))}</div>
      <div style="margin-top:12px;font-size:19px;font-weight:600;">{message_title}</div>
      <div style="margin-top:8px;color:#e9dcff;">{message_body}</div>
    </div>

    <table role="presentation" width="100%" cellspacing="0" cellpadding="8" style="margin-bottom:18px;">
      <tr>
        <td style="background:#201631;border-radius:16px;">Risk Score<br><strong>{int(s.get('riskScore', 0))}/100</strong></td>
        <td style="background:#201631;border-radius:16px;">Rocket Score<br><strong>{int(s.get('rocketScore', 0))}</strong></td>
        <td style="background:#201631;border-radius:16px;">UAV Score<br><strong>{int(s.get('uavScore', 0))}</strong></td>
      </tr>
      <tr>
        <td style="background:#201631;border-radius:16px;">Confidence<br><strong>{confidence}</strong></td>
        <td style="background:#201631;border-radius:16px;">ETA<br><strong>{eta}</strong></td>
        <td style="background:#201631;border-radius:16px;">Unique alerts<br><strong>{int(s.get('uniqueCount', 0))}</strong></td>
      </tr>
    </table>

    <div style="background:#201631;border-radius:18px;padding:18px;margin-bottom:14px;"><div style="font-weight:700;margin-bottom:8px;">אות רלוונטי קרוב</div><div>{nearest_text}</div></div>
    <div style="background:#201631;border-radius:18px;padding:18px;margin-bottom:14px;"><div style="font-weight:700;margin-bottom:8px;">Possible approach</div><div>{possible_approach}</div></div>
    <div style="background:#201631;border-radius:18px;padding:18px;margin-bottom:14px;"><div style="font-weight:700;margin-bottom:8px;">למה הסטטוס נקבע כך</div><div>{state_reasoning}</div></div>
    <div style="background:#201631;border-radius:18px;padding:18px;margin-bottom:14px;"><div style="font-weight:700;margin-bottom:8px;">מצב האירוע כרגע</div><div>{active_text}</div></div>
    <div style="background:#201631;border-radius:18px;padding:18px;margin-bottom:14px;"><div style="font-weight:700;margin-bottom:8px;">יישובים רלוונטיים</div><div>{areas_html}</div></div>
    <div style="background:#201631;border-radius:18px;padding:18px;margin-bottom:14px;"><div style="font-weight:700;margin-bottom:8px;">סיבות מרכזיות</div><div>{reasons_html}</div></div>
  </div>
</body>
</html>'''


def send_email(snapshot: dict):
    if not SMTP_HOST or not SMTP_FROM or not SMTP_TO:
        raise RuntimeError("Missing SMTP configuration")
    subject = f"{SUBJECT_PREFIX} | {snapshot.get('state', 'NORMAL')} | Risk {int(snapshot.get('riskScore', 0))}/100 | Rocket {int(snapshot.get('rocketScore', 0))} | UAV {int(snapshot.get('uavScore', 0))}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = SMTP_TO
    msg.attach(MIMEText(render_html_email(snapshot), "html", "utf-8"))
    if SMTP_SECURITY == "ssl":
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20, context=ctx) as smtp:
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.sendmail(SMTP_FROM, [SMTP_TO], msg.as_string())
        return
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
        if SMTP_SECURITY == "starttls":
            smtp.starttls(context=ssl.create_default_context())
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASS)
        smtp.sendmail(SMTP_FROM, [SMTP_TO], msg.as_string())


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self._reply(200, {"ok": True})
        else:
            self._reply(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/snapshot":
            self._reply(404, {"ok": False, "error": "not found"})
            return
        if not ENABLE_MAIL:
            self._reply(403, {"ok": False, "error": "mail disabled"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1048576:
                self._reply(400, {"ok": False, "error": "invalid payload size"})
                return
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            now = int(time.time())
            state = load_state()
            transition_key = mail_transition_key(payload)
            last_transition_key = str(state.get("last_transition_key", ""))
            last_sent_ts = int(state.get("last_sent_ts", 0) or 0)

            if transition_key == last_transition_key:
                self._reply(200, {"ok": True, "changed": False, "reason": "duplicate transition"})
                return
            if last_sent_ts and (now - last_sent_ts) < MAILER_MIN_INTERVAL_SEC:
                self._reply(200, {"ok": True, "changed": False, "reason": "cooldown"})
                return

            send_email(payload)
            state["last_state"] = payload.get("state", "NORMAL")
            state["last_transition_key"] = transition_key
            state["last_sent_ts"] = now
            save_state(state)
            self._reply(200, {"ok": True, "changed": True})
        except Exception as e:
            print(f"[beready-mailer] POST /snapshot failed: {e}", flush=True)
            self._reply(500, {"ok": False, "error": "mail request failed"})

    def log_message(self, fmt, *args):
        return


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f"[beready-mailer] listening on http://{LISTEN_HOST}:{LISTEN_PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
