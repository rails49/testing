# testing

gate: scripts/check.sh

## Agent skills

The rules every rails49 repository shares are the organisation's
[`docs/agents/`](https://github.com/rails49/.github/tree/main/docs/agents):
`issue-tracker.md`, `triage-labels.md` and `domain.md`.

- Issue tracker: GitHub Issues on rails49/testing, via the `gh` CLI.
- Triage labels: `needs-triage`, `needs-info`, `ready-for-agent`,
  `ready-for-human`, `wontfix`.
- Domain docs: `GLOSSARY.md` and `docs/adr/` at the repo root. What each kind
  of doc holds: org
  [ADR-0025](https://github.com/rails49/.github/blob/main/docs/adr/0025-each-fact-has-one-owner-and-an-adr-is-written-after-its-decision-has-run.md).
