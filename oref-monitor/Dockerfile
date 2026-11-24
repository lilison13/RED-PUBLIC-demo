FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/oref-monitor

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

COPY oref-monitor /opt/oref-monitor
COPY oref-monitor/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
 && mkdir -p /opt/oref-monitor/data \
 && mkdir -p /opt/oref-monitor/logs \
 && mkdir -p /opt/oref-monitor/web/api \
 && mkdir -p /opt/oref-monitor/web/api-mock

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "/opt/oref-monitor/app/oref_monitor.py"]
