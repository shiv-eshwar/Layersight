# Engineering

How to build LayerSight: stack, layout, algorithms, schemas, API, frontend, testing, conventions. System structure and flows are in `architecture.md`.

## 1. Stack

| Area | Choice | Why |
|---|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript | File routes map to the nine screens |
| UI | Tailwind CSS v4, shadcn/ui | Tokens plus accessible primitives |
| Server state | TanStack Query | Caching by dataset and config |
| Client state | Zustand | Draft configs, quiz progress |
| Forms | react-hook-form + zod | Defense builder validation |
| Charts | Apache ECharts | Funnel, donut, heatmap, stacked bars, tornado |
| Custom viz | D3 + Motion | Attack-flow animation |
| API client | openapi-typescript + openapi-fetch | Types generated from FastAPI |
| Backend | Python 3.12, FastAPI, Pydantic v2, uvicorn | Typed contracts |
| Persistence | PostgreSQL 16, SQLAlchemy 2, Alembic, psycopg 3 | SQLite fallback via `DATABASE_URL` |
| Simulation | NumPy | Vectorized Monte Carlo |
| Parsing | Python `email` (policy.default), BeautifulSoup4 + lxml | Standard parsing, HTML links |
| Domains | tldextract (bundled list), RapidFuzz, idna | Registrable domain, similarity, punycode |
| CLI | Typer + Rich | Readable validation output |
| Testing | pytest, Hypothesis, httpx, Vitest, Playwright | Unit, property, API, E2E |
| Tooling | uv, ruff, mypy, pnpm, ESLint, Prettier | |

Deliberately skipped: ML frameworks, job queues, auth providers, threat-intel APIs.

## 2. Repository layout

```
layersight/
  engine/
    pyproject.toml
    layersight/
      parsing/      eml.py, attachments.py, html.py, auth_results.py
      features/     headers.py, auth.py, links.py, domains.py, content.py, attachments.py
      scoring/      rules.py, scorer.py, advice.py, weights.yaml
      config/       schema.py, adapter.py, assumptions.yaml
      simulation/   vectors.py, model.py, montecarlo.py, analytic.py, compare.py, recommend.py
      validation/   metrics.py
      quiz/         generator.py
      reference/    brands.yaml, freemail.txt, shorteners.txt, tlds.yaml, homoglyphs.yaml, public_suffix_list.dat
      models.py     Pydantic contracts shared with the API
      cli.py
    tests/
  api/
    app/
      main.py, settings.py
      routers/      datasets, emails, domains, configs, simulations, comparisons,
                    recommendations, quiz, validation, reports, meta, demo
      db/           models.py, session.py, migrations/
      services/     DB <-> engine orchestration
    tests/
  web/
    app/            routes (see architecture.md §8)
    components/     ui/ (shadcn), layersight/ (RiskScore, EvidenceItem, AttackFlow, …)
    lib/            api client, query keys, formatters
    e2e/            Playwright
  data/
    test/           official emails, labels, two configs (never edited)
    dev/            our tuning set (≥ 30 emails) with labels and configs
  .githooks/        authorship hooks (see github.md)
  docker-compose.yml
  Makefile
```

## 3. Parsing

1. Normalize line endings. If there's no blank line between headers and body, treat leading `Key: value` lines as headers.
2. `email.message_from_string(text, policy=email.policy.default)`.
3. `email.utils.getaddresses` for From, Reply-To, Return-Path, To, Sender → display name, address, domain, registrable domain.
4. Walk MIME parts; keep `text/plain` and `text/html`. From HTML, extract `(anchor_text, href)` with BeautifulSoup plus a text rendering. From plain text, extract URLs with a conservative regex.
5. Attachments, metadata only:
   - Parts with `Content-Disposition: attachment` or a filename: read name and declared type, **ignore the payload**.
   - Pseudo-lines: `Attachment: name (type)`, `[Attachment: name; type]`, `X-Attachment: name; type=…`.
   - Derive extensions, double-extension flag, risk class: `executable` (exe, scr, com, msi, bat, cmd), `script` (js, vbs, ps1, hta, wsf, jar), `macro_document` (docm, xlsm, pptm), `archive` (zip, rar, 7z, iso, img), `html` (htm, html, svg), `document` (pdf, docx, xlsx), `image`, `other`.
6. Parse every `Authentication-Results` for `spf=`, `dkim=`, `dmarc=`, `header.from=`, `smtp.mailfrom=`; fall back to `Received-SPF`. Missing → `none`.
7. Return `ParsedEmail`. Never raise on malformed input; record `parse_warnings`.

## 4. Rules

Each rule is `(ParsedEmail, refs) -> Finding | None`. A finding has id, category, strength (0–1 for graded rules), location, user-visibility flag and template variables. Weights are log-odds points in `weights.yaml`, tuned on `data/dev`.

| ID | Check | Weight |
|---|---|---|
| H01 | Reply-To registrable domain ≠ From | +1.5 |
| H02 | Display name has a brand or role not matching the address domain | +1.5 |
| H03 | Return-Path domain ≠ From | +0.8 |
| H04 | Free-mail address claiming an organization, brand or executive | +1.0 |
| A01 | SPF fail (softfail +0.8) | +1.5 |
| A02 | DKIM fail (none +0.4) | +1.2 |
| A03 | DMARC fail | +2.0 |
| A04 | SPF, DKIM, DMARC all pass and align with From | −1.5 |
| L01 | Link text shows a URL/domain different from the real destination | +2.0 |
| L02 | Link or sender domain is a look-alike (× similarity) | up to +2.5 |
| L03 | IP-address URL | +1.5 |
| L04 | Punycode / IDN host | +1.5 |
| L05 | URL shortener | +0.7 |
| L06 | Brand in subdomain or path, unrelated registrable domain | +1.5 |
| L07 | Suspicious TLD | +0.6 |
| L08 | Plain-HTTP link labeled login/verify | +0.5 |
| L09 | Links point to domains unrelated to the sender | +0.5 |
| C01 | Urgency ("within 24 hours", "immediately", "final notice") | +0.8 |
| C02 | Credential request ("verify your account", "confirm your password") | +1.2 |
| C03 | Payment request (wire, gift cards, new bank details) | +1.2 |
| C04 | Generic greeting ("Dear user") | +0.4 |
| C05 | Threat of loss (suspended, locked, deleted) | +0.6 |
| T01 | Executable or script attachment | +2.5 |
| T02 | Double extension | +2.5 |
| T03 | Macro-enabled Office document | +1.5 |
| T04 | Archive (+0.5 if a password is in the body) | +0.8 |
| T05 | HTML attachment | +1.2 |
| G01 | Organization domain with aligned authentication | −1.0 |
| G02 | All links on the sender's own registrable domain | −0.5 |

Content cues use curated phrase lists, case-insensitive with word boundaries, firing once per email.

**Dev set must include hard negatives** (genuine password resets, newsletters with tracking links and shorteners, genuine PDF invoices, internal IT notices with urgency, shipping notifications) **and hard positives** (phishing from a compromised legitimate domain with passing auth, BEC with no links or attachments, subdomain-abuse links).

## 5. Domain similarity

`similarity(candidate, protected) -> {score, closest, technique, diff}`

1. Registrable domain via tldextract with the bundled list (`suffix_list_urls=()`). Split label (`micros0ft`) and suffix (`com`).
2. Decode punycode with `idna`; flag IDN.
3. Exact match to protected set or allowlist → score 0, legitimate.
4. Skeleton: map confusables (`0→o`, `1→l`, `3→e`, `5→s`, `rn→m`, `vv→w`, `cl→d`, small Unicode table), lowercase, strip hyphens. Skeleton equals a protected label → **homoglyph**, 0.98.
5. Same label, different suffix → **TLD swap**, 0.90.
6. Protected domain inside the subdomain → **subdomain abuse**, 0.90.
7. Protected label as a token in the candidate (`amazon-support`) → **combosquat**, 0.85.
8. Max of `DamerauLevenshtein.normalized_similarity` and `JaroWinkler.similarity` on labels ≥ 0.80 → **typosquat**, that score.
9. Return the highest score, technique, closest domain and a character diff.

Protected set: `reference/brands.yaml` plus `org_domains` from the config. Look-alike threshold 0.80. L02 contribution = 2.5 × score.

## 6. Risk scoring

```python
logit = BIAS + sum(f.weight * f.strength for f in findings)   # BIAS starts at -2.0
risk = 1 / (1 + math.exp(-logit))
label = "phishing" if risk >= THRESHOLD else "genuine"           # THRESHOLD = 0.50
```

| Band | Risk score | Label |
|---|---|---|
| Critical | ≥ 0.85 | phishing |
| High | 0.70–0.85 | phishing |
| Suspicious | 0.50–0.70 | phishing |
| Low | < 0.50 | genuine |

Each finding becomes `Evidence` with its signed contribution and share of the total, for the score breakdown. Bias, threshold and weights live in `weights.yaml`; its hash is stored with every analysis.

**Tuning protocol:** tune only on `data/dev`, evaluate on `data/test`. Any change made after looking at test results goes in the decision log and is disclosed on the Reports page.

## 7. Advice

Templates keyed by evidence id, ordered by contribution, max three plus a closing action.

- H01: "Replies would go to `{reply_domain}`, not `{from_domain}`. Don't reply; contact the sender through a channel you already know."
- L01/L02: "The link goes to `{domain}`, which imitates `{brand}`. Don't click it. Type `{brand_domain}` into your browser instead."
- T01/T02: "Don't open `{filename}`. Real invoices and documents are never executable files."
- A03: "This message failed sender authentication, so the sender address is probably forged."
- Phishing close: "Report it with the Report Phish button, then delete it."
- Genuine: "No strong warning signs. Still confirm unexpected requests for money or credentials through a separate channel."

## 8. Attack vector classification

First match wins:

1. `malware_attachment`: an attachment with risk class executable, script, macro_document, archive or html.
2. `malware_link`: a link path ending in a risky extension, or download wording beside a link.
3. `credential_harvest`: links plus a credential request, login wording or look-alike link.
4. `payment_fraud`: no links or risky attachments, payment request present.
5. Fallback: `credential_harvest` if links exist, else `payment_fraud`.

Vector and reason are stored; Investigation lets users override.

## 9. Layer configuration

```yaml
schema_version: 1
name: "Untrained users (v1)"
org_domains: ["company.com"]
email_filter:
  base_catch_rate: 0.35
  rules:
    - id: quarantine_dmarc_fail
      description: Quarantine messages that fail DMARC
      match: { feature: auth.dmarc, op: eq, value: fail }
      catch_rate: 0.85
      enabled: true
    - id: block_executables
      match: { feature: attachment.risk_class, op: in, value: [executable, script] }
      catch_rate: 0.98
      enabled: true
user_training:
  level: none            # none | basic | advanced
  catch_rate: null       # optional override, 0-1
application_control:
  effectiveness: 0.25
  overrides: { macro_document: 0.90, executable: 0.95 }
antivirus:
  detection_rate: 0.55
segmentation:
  containment_rate: 0.40
  applies_to_credential_harvest: true
simulation:
  runs: 10000
  seed: 42
```

- Filter rules use a small safe DSL (`eq`, `ne`, `in`, `gte`, `lte`, `contains`, `exists`) over flat feature names (`auth.dmarc`, `header.reply_to_mismatch`, `links.max_lookalike_score`, `attachment.risk_class`, `content.urgency`, `risk_score`). Never `eval`.
- `config/adapter.py` maps the official format onto this schema (percent → fraction, training scales, key names). Unknown keys warn; validation errors name the field and expected range.

## 10. Layer probability model

Each layer gets a stop probability and reasons. Non-applicable layers (matrix in `context.md` §5.4) get 0 and display "not applicable".

**Email filter:** noisy-OR of the base rate and every matched enabled rule.

$$p_F = 1 - (1 - b)\prod_{r \in \text{matched}} (1 - c_r)$$

**User:** base rate by training level, adjusted by visible warning signs.

$$p_U = \mathrm{clamp}\left(\text{base}_\ell + s_\ell\,(\text{cue}(e) - 0.5),\ 0.02,\ 0.98\right)$$

| Level | base | sensitivity |
|---|---|---|
| none | 0.30 | 0.10 |
| basic | 0.55 | 0.25 |
| advanced | 0.75 | 0.35 |

`cue(e)` is the weighted share of user-visible findings present (generic greeting, urgency, threats, visible link mismatch, misspelled domain, unexpected attachment, credential or payment request). Authentication results aren't visible and don't count. Trained users are more sensitive to cues. An explicit `catch_rate` overrides the table.

**Application control:** malware vectors only; `overrides[risk_class]` if set, else `effectiveness`.
**Antivirus:** malware vectors only; `detection_rate`, × 0.5 for password-protected archives (A4).
**Segmentation:** malware vectors, plus credential harvesting when enabled; `containment_rate`.

Defaults live in `config/assumptions.yaml` and are served by `GET /api/v1/meta` to the assumptions panel.

## 11. Monte Carlo

```python
LAYERS = ("email_filter", "user", "application_control", "antivirus", "segmentation")

def run(p_stop: np.ndarray, u: np.ndarray) -> np.ndarray:
    """p_stop: (5,), 0.0 for non-applicable layers. u: (runs, 5) uniforms.
    Returns (6,) counts: stops per layer, last element = passed all layers."""
    stopped = u < p_stop
    first = np.where(stopped.any(axis=1), stopped.argmax(axis=1), p_stop.size)
    return np.bincount(first, minlength=p_stop.size + 1)

def uniforms(seed: int, email_sha256: str, runs: int) -> np.ndarray:
    ss = np.random.SeedSequence([seed, int(email_sha256[:16], 16)])
    return np.random.default_rng(ss).random((runs, len(LAYERS)))
```

- Funnel: entering layer i = runs − stops before i.
- Pass rate = passed / runs, with a 95% Wilson interval.
- Closed form ∏(1 − p_i) returned alongside; a test asserts it falls inside the interval.
- Aggregate: equal-weighted mean of per-email rates and funnels (A5).
- 10,000 × 5 per email is sub-millisecond.

## 12. Comparison

- One `u` per email, evaluated against both configs.
- Output: both results, absolute difference, relative reduction (P_A − P_B) / P_A, per-layer and per-email deltas, config diff, narrative.
- Narrative template: "Improving {changed_layer} from {a} to {b}, with all other controls unchanged, reduces the modeled chance an attack passes every layer from {pa} to {pb}, a {rel} reduction."

## 13. Recommendations and sensitivity

| Intervention | Change |
|---|---|
| Next training level | none → basic → advanced |
| Quarantine DMARC failures | add rule if missing |
| Look-alike filter | add `links.max_lookalike_score gte 0.85` |
| Block macros | app-control override for macro documents |
| Better endpoint detection | antivirus +15 points |
| Tighter segmentation | containment +20 points |

Evaluate aggregate pass-through with the closed form, rank by absolute reduction, explain which vectors benefit. Sensitivity (tornado): each layer ±10 points. Expected insight: in a credential-heavy mix, antivirus barely matters and training dominates.

## 14. Parameter uncertainty (stretch)

Sample each layer rate per run from a Beta distribution with the configured mean and concentration κ (default 50). Show the 5th–95th percentile band. Off by default.

## 15. Validation

- Labels from `labels.csv` (`filename,label`), else a label header or file-name convention, loaded only here.
- Accuracy, precision, recall, F1, FPR, FNR, confusion matrix, per-email rows with top evidence.
- Misclassification report: the evidence behind each error and its distance from the threshold.
- CI gate: `pytest -m validation` fails if accuracy on `data/test` < 0.90.

## 16. Quiz generation

- **Phish or legit:** ground truth when available, else prediction; explanation from top evidence.
- **Most suspicious element:** options from the email's top user-visible findings plus distractors; correct = highest contribution.
- **Where does this link go:** visible text vs options including the real registrable domain.

## 17. Reproducibility

Analyses store `engine_version` and `weights_hash`. Runs store config snapshot, seed, runs and engine version. `layersight simulate --from-report report.json` reproduces exported numbers.

## 18. CLI

```bash
layersight analyze    data/test/emails --out out/analysis.json
layersight validate   data/test/emails --labels data/test/labels.csv
layersight simulate   data/test/emails --config data/test/configs/untrained.yaml --runs 10000 --seed 42
layersight compare    data/test/emails --a data/test/configs/untrained.yaml --b data/test/configs/trained.yaml --seed 42
layersight similarity micros0ft.com
```

The CLI is also the fallback demo.

## 19. API

| Method | Path | Purpose | Screen |
|---|---|---|---|
| POST | `/api/v1/datasets` | Upload files or zip + optional labels; analyze | 02 |
| GET | `/api/v1/datasets` | List | all |
| GET | `/api/v1/datasets/{id}/summary` | KPIs | 01 |
| GET | `/api/v1/datasets/{id}/emails` | Rows: `q`, `label`, `band`, `sort` | 02 |
| GET | `/api/v1/emails/{id}` | Full analysis | 03 |
| PATCH | `/api/v1/emails/{id}` | Override attack vector | 03 |
| GET | `/api/v1/datasets/{id}/domains` | Domain intelligence | 04 |
| POST | `/api/v1/domains/similarity` | Ad-hoc check | 04 |
| GET, POST | `/api/v1/configs` | List, create | 05 |
| GET | `/api/v1/configs/{id}` | Read | 05 |
| POST | `/api/v1/configs/{id}/versions` | Save edits as new version | 05 |
| POST | `/api/v1/configs/import` | Import via adapter | 05 |
| GET | `/api/v1/configs/{id}/export` | YAML | 05 |
| POST | `/api/v1/simulations` | Run; `persist:false` for what-if | 05, 06 |
| GET | `/api/v1/simulations/{id}` | Stored run | 06 |
| POST | `/api/v1/comparisons` | A vs B | 03, 07 |
| POST | `/api/v1/recommendations` | Ranked interventions, sensitivity | 01, 06 |
| GET | `/api/v1/datasets/{id}/quiz` | Questions | 08 |
| POST | `/api/v1/quiz/attempts` | Answers | 08 |
| GET | `/api/v1/datasets/{id}/validation` | Metrics, matrix | 09 |
| GET | `/api/v1/datasets/{id}/report.json`, `.csv` | Exports | 09 |
| GET | `/api/v1/meta` | Versions, weights hash, assumptions | all |
| POST | `/api/v1/demo/reset` | Restore demo state | — |

## 20. Core contracts

```python
class Evidence(BaseModel):
    rule_id: str                 # "L02"
    category: Literal["header", "auth", "link", "domain", "content", "attachment", "trust"]
    title: str                   # "Look-alike domain"
    detail: str                  # "micros0ft.com imitates microsoft.com (homoglyph, 0.98)"
    location: str | None         # "link #1 href"
    contribution: float          # signed logit points
    user_visible: bool

class EmailAnalysis(BaseModel):
    email_id: str
    risk_score: float
    label: Literal["phishing", "genuine"]
    band: Literal["critical", "high", "suspicious", "low"]
    attack_vector: AttackVector
    vector_reason: str
    evidence: list[Evidence]
    advice: list[str]
    cue_score: float
    features: dict[str, Any]     # flat names used by filter rules
    engine_version: str
    weights_hash: str

class LayerOutcome(BaseModel):
    layer: Layer
    applicable: bool
    p_stop: float
    reasons: list[str]           # "Rule quarantine_dmarc_fail matched (0.85)"
    entered: int
    stopped: int

class EmailSimulation(BaseModel):
    email_id: str
    attack_vector: AttackVector
    layers: list[LayerOutcome]
    passed: int
    pass_rate: float
    ci95: tuple[float, float]
    closed_form: float

class SimulationResult(BaseModel):
    config_snapshot: LayerConfig
    runs: int
    seed: int
    per_email: list[EmailSimulation]
    aggregate: AggregateSimulation
    engine_version: str
```

## 21. Frontend

```css
/* app/globals.css */
@theme {
  --color-midnight: #0B1120;
  --color-graphite: #172334;
  --color-intelligence: #38BDF8;
  --color-protected: #10B981;
  --color-warning: #F59E0B;
  --color-threat: #EF4444;
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
}
```

- Fonts via `next/font` (self-hosted, offline).
- Query hooks per resource in `lib/queries.ts`; keys include dataset and config ids.
- One wrapper per chart (`Funnel`, `OutcomeDonut`, `StopBars`, `ConfusionMatrix`, `Tornado`) sharing an ECharts theme built from tokens.
- **Attack flow:** sample ~300 particles in proportion to where runs stopped; animate along the layer path with Motion; drop each at its stop layer. With `prefers-reduced-motion`, show the static funnel.
- **Email body:** render `body_text_sanitized` in a monospace block, links defanged with the real destination on hover. Never `dangerouslySetInnerHTML` for email content.
- Formatters: `formatPct(0.0921) → "9.21%"`, `formatCount(10000) → "10,000"`, scores to two decimals.

## 22. Security

- Emails are hostile: no HTML rendering, no fetching, no attachment content.
- Limits: 200 files, 2 MB each, 20 MB per request; zip member count and size caps; reject absolute paths and `..`.
- CORS restricted to the web origin; secrets only in env; `.env.example` committed.
- Logs exclude bodies and addresses.

## 23. Testing

| Level | What | Tool |
|---|---|---|
| Unit | Parser paths; each rule positive and negative; similarity techniques; advice | pytest |
| Golden | 9.21%, 3.29%, 64.3%; funnel 6,500 / 4,550 / 3,413 / 1,536 / 921 | pytest |
| Property | Raising any layer never raises pass-through; MC within Wilson interval of closed form; same seed → identical output; file order doesn't change per-email results | Hypothesis |
| Validation | Accuracy ≥ 0.90 on `data/test`; reported on `data/dev` | pytest marker |
| API | Every endpoint, happy path and errors; both official configs import | httpx |
| Frontend unit | Formatters, particle sampling | Vitest |
| E2E | Upload → triage → investigate → simulate → compare → reports | Playwright |

CI: ruff, mypy, pytest, ESLint, `tsc --noEmit`, Playwright against docker compose.

## 24. Performance budgets

| Operation | Budget |
|---|---|
| Analyze 20 emails | < 1 s |
| Simulate dataset, 10,000 runs per email | < 300 ms round trip |
| What-if update after slider stops | < 250 ms |
| Initial page load (local) | < 2 s |

## 25. Conventions

- Python: ruff, mypy strict on `engine`, Pydantic at every boundary, no global state, randomness only via passed generators.
- TypeScript: strict, no `any`, generated API types only.
- Glossary terms from `context.md` in code and UI.
- Conventional commits (`feat(engine): …`), small commits, each pushed right away. Authorship rules in `github.md`.

## 26. Commands

```bash
make setup     # uv sync, pnpm install, git config core.hooksPath .githooks
make dev       # db + api (reload) + web
make demo      # seed official data + configs, precompute comparison
make test      # Python + frontend tests
make validate  # layersight validate on data/test
make e2e       # Playwright
make types     # regenerate TS types from OpenAPI
```
