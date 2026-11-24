# Publication checklist

This is a sanitized portfolio snapshot, not a production release.

- Start a new Git repository from these files; do not import, fork or mirror private history.
- Review the original repository history independently and rotate any previously exposed credentials. In particular, replace or restrict the previous browser map key.
- Verify that you own or are authorized to redistribute all remaining source code. The removed GiliMap component was identified in prior review as potentially derived from `maorcc/oref-map`; confirm whether any remaining code also derives from it, and comply with applicable license and attribution obligations before publishing. No repository-wide license has been assigned without that confirmation.
- Bundled location datasets were excluded because redistribution rights were not established. Use authorized local copies only; do not add them back to source control without permission.
- External frontend dependencies and tile providers have their own terms. Preserve their notices and attribution. This demo is not official and must not be used for public safety decisions.
- Run a dedicated secret scanner, review the result, and validate the full stack in an isolated environment before changing visibility. Do not expose the demo server directly to the Internet.
