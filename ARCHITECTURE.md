# Architecture

```text
Official alert feeds (optional live profile)
                |
          oref-monitor
                |
         shared runtime/api
          |              |
          |    beready-snapshot-poller
          |              |           |
          |         snapshot    internal mailer (disabled by default)
          |                          |
          |                      optional SMTP
          v
        Nginx <--- static Hebrew/Russian frontend
          |
    localhost preview
```

`oref-monitor` fetches and merges live and historical data, deduplicates alerts and atomically publishes `status`, `history`, `latest_event` and `meta`. `beready-snapshot-poller` reads the shared data and writes `beready_snapshot`; an optional internal SMTP worker receives transition notifications. The experimental scoring engine is not a validated safety system.

Docker Compose starts only the localhost Nginx preview by default. The three Python services require the explicit `live` profile. Geographic data is operator-provided and not distributed. Nginx mounts the API directory read-only and exposes only allowlisted feed names. The SMTP endpoint is never proxied. No production identity, certificate, deployment target or secret is required for preview.

Frontend pages poll JSON endpoints; no WebSocket layer is required. Map layers use Leaflet and optionally MapLibre with an operator-provided MapTiler browser key. OpenStreetMap attribution is retained.
