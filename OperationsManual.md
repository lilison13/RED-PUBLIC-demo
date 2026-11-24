# Operations and validation

## Public portfolio validation

The public repository currently contains documentation and sanitized configuration, not a complete runnable application. The GitHub Actions workflow in `.github/workflows/validate-portfolio.yml` uses a GitHub-hosted runner to verify that the expected portfolio files exist and that Docker Compose accepts the configuration. It does not build images, execute application tests, contact Vault, ingest live data or deploy anything.

To check the Compose configuration locally, in a clean checkout with Docker Compose installed:

```sh
cp .env.example .env
docker compose --profile live config --quiet
```

Do not overwrite an existing environment file. The example contains placeholder values only.

## Original private deployment flow

1. Commit and push changes to the private GitHub repository.
2. GitHub Actions schedules the deployment on the authorized self-hosted runner.
3. Check out the repository, create an ephemeral SSH key, and request a signed certificate from Vault using the Vault Agent authentication context.
4. Authenticate over SSH, synchronize the repository using rsync, and invoke the private deployment script on the application host.
5. Inspect the deployment result and verify service health and logs on the target host.

The target host retains its own local application environment configuration. See [the reconstructed workflow](examples/deploy-vault.example.yml) for a sanitized illustration. The example omits real endpoints, runner labels, signing roles, tokens, server paths and scripts. It is deliberately outside `.github/workflows` and is not executed by GitHub Actions.

## Troubleshooting approach

| Layer | Checks |
| --- | --- |
| GitHub Actions | Workflow trigger, job logs, runner availability and matching labels |
| Private networking | Internal DNS resolution, network reachability, TLS trust |
| Vault | Agent authentication, token validity, signing policy, certificate expiry |
| SSH and file sync | Host-key verification, certificate principal and permissions, rsync result |
| Application host | Deployment script exit status, Docker Compose service state and container logs |
| Application | Data timestamps, feed availability, Nginx endpoints, frontend behavior |

Never print or upload authentication tokens, private keys or environment secrets in diagnostics. Never attach a production runner to this public repository.

## Future isolated preview

Only after reviewed source files and Nginx/frontend configuration are added may an isolated preview be attempted. Use authorized datasets and keep optional mail disabled. Start with the loopback-only configuration; do not expose it directly to the Internet. Live data is not required for portfolio validation. Missing or stale data must never be interpreted as an indication of safety.
