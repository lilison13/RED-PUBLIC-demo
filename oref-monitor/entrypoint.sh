#!/usr/bin/env sh
set -eu

mkdir -p /opt/oref-monitor/data
mkdir -p /opt/oref-monitor/logs
mkdir -p /opt/oref-monitor/web/api
mkdir -p /opt/oref-monitor/web/api-mock

case "$*" in
  *oref_monitor.py*|*beready_snapshot_poller.py*)
    python3 -c 'import json, pathlib; p=pathlib.Path("/opt/oref-monitor/web/api"); specs={"zones":dict,"localities":list,"location_polygons":dict}; assert all(isinstance((v:=json.loads((p/k).read_text(encoding="utf-8-sig"))),t) and v for k,t in specs.items()), "Authorized geographic datasets required"' || { echo "Missing or invalid geographic datasets. See README." >&2; exit 1; }
    ;;
esac
exec "$@"
