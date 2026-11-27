# LayerSight

Phishing resilience intelligence. Detect the threat, understand the risk, and prove the defenses.

Hackathon problem 1-18, Phishing Triage and Layered Defense Simulator. The product, architecture, and build plan live in the markdown files at the root. Start with `whatthis.md`, then `context.md`.

## What runs today

The engine classifies mail and estimates how far an attack gets through five defense layers. The API stores an upload, imports layer configs, simulates, compares two configs, and reports validation. Open http://localhost:8000/docs and follow that order, or `POST /api/v1/demo/reset` to reload the practice set.

`data/test/` is a local practice set (20 messages, both configs), not the official drop. `data/dev/` is the tuning corpus. When the official files arrive, replace `data/test/` byte for byte.

## Setup

Git identity and the authorship hooks are a one-time step, documented in `github.md` section 3. Then:

```bash
uv python install 3.12
uv sync
pnpm install --dir web
```

## Run

```bash
make dev
```

- Web application: http://localhost:3000
- API health: http://localhost:8000/health
- API assumptions: http://localhost:8000/api/v1/meta
- Postgres 16: localhost:5432, database `layersight`, user and password `layersight`

`make dev` starts Postgres with Docker, then the API and the web app on the host. Ctrl-C stops the API and the web app. `make db-stop` stops Postgres.

`docker compose up` builds and runs all three in containers.

## Checks

```bash
make test
```

That runs Ruff, mypy, pytest, the TypeScript check, and ESLint.

## Demo

One command runs the judge path offline, with no database and no request off the machine:

```bash
make e2e
```

That installs the Playwright package on first use, then walks Triage, the top phishing email, the simulator, the comparison, and Reports. The same path is timed three times with `make rehearse`. Two consecutive clean runs must finish under 3:00. `make offline-check` fails the run if a page asks for anything other than loopback, which is the Wi-Fi-off case: localhost still serves the demo. `make perf` checks the budgets in `engineering.md` section 24. `make video` writes `demo/backup/demo-fallback.webm`. Copy that file to the desktop before presenting.

The product demo, once the stack is up, is `make dev` and then http://localhost:3000. `make e2e-app` walks Triage, the top phishing email, the simulator, the comparison, and Reports against that app. On the practice set, seed 42, the engine reports 20/20 and a modeled pass-through of 9.59% untrained, 3.82% trained, a 60.2% reduction. `web/components/layersight/screen-state.tsx` is the loading, empty, and error shell those screens use.

The harness on port 4173 is labeled illustrative. It uses the published five-layer scenario (9.21% untrained, 3.29% trained, 64.3% reduction) so the path can be rehearsed before the engine is seeded. The live app replaces those figures with engine results. Spoken lines and the backup-video steps are in `demo/REHEARSAL.md`.

## CLI fallback

If the browser fails, the terminal still answers the core target. From a checkout with the engine installed (`make setup`):

```bash
make validate
make simulate
make compare
```

`make validate` scores `data/test/`. `make simulate` and `make compare` use the same set, seed 42, and 10,000 runs. The same commands with explicit paths:

```bash
layersight validate data/test/emails --labels data/test/labels.csv
layersight compare data/test/emails \
  --a data/test/configs/untrained.yaml \
  --b data/test/configs/trained.yaml \
  --seed 42
```

`layersight simulate --from-report report.json` reproduces an exported report. Seed 42 is the rehearsed seed.

## Assumptions

Pass-through is a modeled estimate. The assumptions are visible in the app (Modeled estimates) and at `GET /api/v1/meta`. The log is `context.md` section 9:

| ID | Assumption |
|---|---|
| A1 | Layers are independent, given the email |
| A2 | Training catch rates: none 0.30, basic 0.55, advanced 0.75 |
| A3 | One primary attack vector per email |
| A4 | Password-protected archives halve antivirus detection |
| A5 | Aggregate pass-through weights each phishing email equally |
| A6 | Simulation runs on emails predicted as phishing |
| A7 | Classification threshold is 0.50 |

Independence is a stated limitation. Credential-harvesting and payment-fraud emails do not give antivirus or application control a chance to stop them.

## Documentation

| Doc | What it covers |
|---|---|
| `whatthis.md` | How the documents fit together |
| `product.md` | Screens, journeys, design system |
| `context.md` | Domain, assumptions, glossary |
| `architecture.md` | Containers and request flows |
| `engineering.md` | Stack, rules, API, commands |
| `phases.md` | Build phases and exit criteria |
| `plan.md` | Demo script, risks, judge Q&A |
| `github.md` | Commits, authorship, push |
| `demo/REHEARSAL.md` | Timed spoken demo and fallbacks |
