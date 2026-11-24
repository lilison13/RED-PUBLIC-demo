# Lil-RedAlert — public portfolio edition

Independent, unofficial alert-monitoring engineering project. Python services normalize alert feeds, maintain history, compute an experimental BeReady snapshot and serve a Hebrew/Russian web interface via Nginx. **This edition is for technical demonstration only, not emergency guidance or a replacement for official instructions.**

## Project motivation: Vault and DevSecOps

This independent project began as a technical integration exercise to deepen my understanding of HashiCorp Vault and improve my ability to support the product in real-world customer scenarios. The goal was to explore how Vault fits into an automated software delivery workflow, particularly certificate-based access to on-premises infrastructure.

The original private implementation uses:

- **GitHub Actions** to trigger an automated deployment workflow on changes to the main branch.
- **An on-premises self-hosted runner** to execute the workflow inside the private environment.
- **HashiCorp Vault SSH secrets engine** to sign an SSH public key generated for each deployment run.
- **SSH certificate authentication** to synchronize application files and trigger a remote deployment.
- **Docker Compose and Nginx** to run and serve the application stack on premises.

The exercise evolved into an operational alert-monitoring platform. It illustrates product integration, infrastructure automation and independent technical learning rather than a professional software development or DevOps engagement.

The public edition contains the application source and a separate GitLab CI source-validation configuration. The original GitHub Actions deployment workflow, Vault configuration, credentials and private infrastructure details are intentionally excluded. See [Architecture](ARCHITECTURE.md#original-private-deployment-architecture) for the logical deployment flow.

## Architecture

- Python ingestion, normalization, history merging and deduplication
- Independent snapshot computation and optional internal SMTP worker
- Static dashboards, Leaflet and optional MapLibre rendering
- Docker Compose, shared runtime data directory and isolated service network
- Nginx read-only public API allowlist; localhost-only demo binding
- GitLab CI configuration for offline source validation (not production deployment)

## Local preview (no live ingestion or mail)

```sh
docker compose up -d nginx
```

Open http://127.0.0.1:8081/ (Hebrew), `/ru/`, `/map/` or `/red/beready/`. Geographic overlays and alert feeds are intentionally unavailable until authorized datasets and live services are configured. Empty or missing feeds do not mean that an area is safe. The interface may show unavailable/empty data. Map tiles and frontend libraries require Internet access; the source archive does not bundle them.

## Optional isolated live-development mode

Only proceed if you have permission to use the upstream services and geographic datasets. Never connect this demo to a production runner, network or secret store.

1. Copy `.env.example` to `.env`; leave `BEREADY_ENABLE_MAIL=false`.
2. Populate the ignored `runtime/api/` directory with your own authorized UTF-8 JSON files: `localities` (array), `zones` (object), and `location_polygons` (object). File names have no extension. Data must match the expected schemas in the frontend and backend. No source data or license to third-party datasets is supplied.
3. Run `docker compose --profile live up -d --build`.
4. Check container logs and `/red/api/status`, `/red/api/history`, `/red/api/meta`, and `/red/api/beready_snapshot` at the localhost preview address.

The live profile contacts the upstream alert API. Its availability and data correctness have not been verified for this edition. Only enable SMTP explicitly in a controlled environment using your own credentials and TLS-enabled SMTP server. The mailer is not routed by Nginx. MapTiler is optional; set your own domain-restricted public browser key in `frontend/red/map/index.html` if needed. Without it, the map uses OpenStreetMap tiles; respect the provider's usage policy. The HTTP-only preview is deliberately bound to loopback. Configure TLS and review the threat model before any network exposure.

## Validation

```sh
python -m unittest discover -s tests -v
python scripts/check_javascript.py  # requires Node.js
```

`.gitlab-ci.yml` runs the checks in separate jobs. No credentials, deployments or self-hosted production runners are configured. The pipeline has not been run on GitLab yet.

## Publication and third-party material

This sanitized source snapshot excludes production deployment configuration, private endpoints, keys, bundled third-party geographic datasets, and the removed map component and media. No Git history is included. See `PUBLICATION.md` for remaining publication checks. A repository-wide license is not asserted here: confirm ownership and applicable upstream licenses before public release.
