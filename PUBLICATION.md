# Public portfolio scope and publication checklist

This repository is a sanitized portfolio edition of an independent project, not a production release. The original environment is private.

- The original private delivery flow used GitHub Actions, a self-hosted runner, Vault Agent/AppRole, SSH certificate signing and deployment over SSH/rsync.
- `examples/deploy-vault.example.yml` is a reconstructed illustration, not a copy of the original private workflow or evidence of a public deployment run.
- `.github/workflows/validate-portfolio.yml` is a newly prepared public configuration-only check. It has no deployment credentials and uses a GitHub-hosted runner.
- Do not connect the public repository to the private runner, Vault instance or application host. Do not import or mirror private Git history.
- Exclude credentials, tokens, private keys, infrastructure identifiers, actual deployment scripts, local `.env` files and runtime data. Review private history and rotate previously exposed credentials; replace or restrict any exposed map key.
- Confirm ownership and redistribution rights before adding source code or data. Review any remaining code derived from third-party projects, including possible `maorcc/oref-map` material, and preserve applicable license notices and attribution. No repository-wide license is asserted without that review.
- Do not distribute location datasets without permission. External map tiles and frontend dependencies have their own terms.
- Run secret scanning and validate any future runnable release in an isolated environment before publication.

This independent project is not an official emergency warning service and must not be used for safety decisions.
