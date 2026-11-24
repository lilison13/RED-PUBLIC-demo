# Local development operations

## Start / stop

```sh
docker compose up -d nginx
docker compose ps
docker compose logs --tail=100 nginx
docker compose down
```

For optional live development, follow the prerequisites in README and use `docker compose --profile live up -d --build`. Mail remains disabled unless explicitly configured. Use `docker compose --profile live down` to stop the full stack.

## Checks

```sh
curl -I http://127.0.0.1:8081/
curl -I http://127.0.0.1:8081/map/
curl -I http://127.0.0.1:8081/red/beready/
curl -i http://127.0.0.1:8081/red/api/mail-snapshot
```

The last request must return 404. API files can be missing in preview mode. For live development check the monitor and snapshot-poller logs, authorized input files, timestamps and API fetch health. Never interpret an unavailable feed as a safe state. The local data directory may persist after stopping containers; do not commit it.

## Secrets and deployment

Keep `.env`, credentials, TLS material and runtime files outside source control. Use scoped credentials and TLS for any optional external integration. The public pipeline validates source only; production deployment and rollback are deliberately outside this edition. Never attach a production runner to a public project.
