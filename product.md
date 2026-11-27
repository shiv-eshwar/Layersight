# Product

## 1. Vision

LayerSight helps organizations measure and reduce phishing risk end to end. It explains why an email is dangerous, models how far that email would get through the organization's defenses, and identifies the change that would reduce risk the most.

**Positioning:** phishing resilience intelligence for security teams. Detection tools stop at "is this bad?". LayerSight continues to "how exposed are we, where do our defenses fail, and what should we fix next?"

- **Hackathon goal:** win problem 1-18 with a working, honest, explainable product.
- **Product goal:** B2B SaaS for enterprises, security operations teams, universities and MSSPs.

## 2. The problem

- Teams see phishing verdicts, not end-to-end exposure. A gateway catching 35% of attacks says nothing about how many reach a protected system.
- Awareness training is hard to justify because its effect isn't connected to technical controls. Click rates aren't risk.
- Investment decisions (more training, better antivirus, stricter filtering) are made on intuition. Nobody can say which control buys the biggest reduction for *their* attack mix.
- Scores aren't explainable to the people who must act: users and executives.

## 3. Users

| Persona | Role | Job to be done | Primary screens |
|---|---|---|---|
| Priya, SOC analyst | Triages reported email | "Tell me quickly which emails are dangerous and why, so I can act and advise the user." | Triage, Investigation, Intelligence |
| Marcus, CISO / security manager | Owns risk and budget | "Show me our residual risk and which investment reduces it most, in a form I can take to the board." | Command Center, Defense, Simulator, Compare, Reports |
| Elena, awareness lead | Runs training | "Prove training reduces real risk, and train people on realistic examples." | Compare, Academy |
| Employees | Receive mail | "Help me recognize phishing." | Academy, advice |
| MSSP operator (future) | Serves many clients | "Compare clients' resilience and sell the right improvements." | All, multi-tenant |
| Hackathon judges | Evaluate in three minutes | "Is it correct, real and different?" | Demo path |

## 4. Differentiators

| Differentiator | What the user gets |
|---|---|
| Explainable risk scoring | Each score breaks into evidence items with their contribution, in plain language |
| Vector-aware attack simulation | 10,000 runs per email through only the layers that apply to its attack type, with a chart of where attacks stop |
| What-if analysis | Change any layer and see residual risk update immediately |
| Intelligent recommendations | Improvements ranked by modeled risk reduction for this organization's email mix |
| Reproducible validation | Accuracy, confusion matrix and errors on the 20 labeled emails, with seeds and versions recorded |

## 5. Product principles

1. **Explain, don't assert.** Every score, probability and recommendation opens to show why.
2. **Honest numbers.** Modeled results are labeled modeled. Assumptions are visible and editable. Validation errors are shown, not hidden.
3. **Actionable by default.** Every screen ends with a next step: advice for the user, a fix for the CISO.
4. **Calm precision.** Linear's precision, Stripe's analytical clarity, an enterprise security tool's restraint. No decorative hacker graphics, heavy gradients or gratuitous animation. Motion only where it carries information, as in the attack flow.
5. **One source of truth.** Same engine, same number in CLI, API and UI.

## 6. Information architecture

Top navigation on every screen:

`Command Center · Triage · Intelligence · Defense · Simulator · Compare · Academy · Reports`

Threat Investigation is a detail page under Triage. The top bar also holds the **active dataset**, the **configuration pair** (baseline and comparison; defaults Untrained v1 and Trained v2), and a "Modeled estimates" icon that opens the assumptions panel.

| # | Screen | Route | Primary persona |
|---|---|---|---|
| 01 | Security Command Center | `/` | CISO |
| 02 | Email Triage | `/triage` | Analyst |
| 03 | Threat Investigation | `/triage/[emailId]` | Analyst |
| 04 | URL & Domain Intelligence | `/intelligence` | Analyst |
| 05 | Defense Layer Builder | `/defense` | CISO |
| 06 | Attack Simulator | `/simulator` | CISO |
| 07 | Before vs After | `/compare` | CISO, awareness lead |
| 08 | Awareness Academy | `/academy` | Employees, awareness lead |
| 09 | Validation & Reports | `/reports` | Judges, CISO |

The concept images use other nav labels ("Dashboard", "Training") and swirling gradients. Standardize on the labels above and the flat design system in §9.

## 7. Screens

### 01 Security Command Center
**Purpose:** organization-wide exposure and defense effectiveness at a glance.
**Shows:** KPI cards (emails analyzed, phishing, genuine, accuracy when labels exist); residual risk before and after training with relative reduction; blocked-versus-passed donut; compact where-attacks-stop funnel; top recommendation with its modeled reduction; highest-risk emails; most-impersonated brands.
**Acceptance:** every number links to the screen that produced it; empty state guides the user to upload.

### 02 Email Triage
**Purpose:** upload, classify, search and prioritize.
**Shows:** drag-and-drop for many `.eml`/`.txt` files or a `.zip`, optional labels file; table with subject, sender, prediction, risk score (monospace, colored by band), attack vector, top evidence, date; tabs All / Phishing / Genuine with counts; search by sender, subject, domain; default sort by risk.
**Acceptance:** 20 emails upload and classify in under 2 seconds.

### 03 Threat Investigation
**Purpose:** everything about one email.
**Shows:**
- Verdict header: label, risk score, band, attack vector.
- Headers: From (display name and address), Reply-To, Return-Path, Date, Subject, with mismatches highlighted.
- Authentication badges: SPF, DKIM, DMARC (pass / fail / none).
- Evidence list ordered by contribution, as a score breakdown.
- Links: visible text vs real destination, registrable domain, similarity to the closest brand.
- Attachments: name, type, risk class, with "metadata only" stated.
- Body: sanitized text, defanged links, suspicious phrases highlighted.
- User advice card.
- Defense outlook: this email's pass-through before and after training, mini funnel, "Simulate this email".
**Acceptance:** an analyst can explain the verdict to a colleague using only this page.

### 04 URL & Domain Intelligence
**Purpose:** look-alike domains, deceptive URLs, similarity scoring across the dataset.
**Shows:** every domain seen (sender, Reply-To, links) with closest protected brand, similarity score, technique, occurrences and linked emails; character diff (`micros0ft` vs `microsoft`, the `0` highlighted); deceptive-link list (text vs real address); a checker that scores any typed domain.
**Acceptance:** `paypa1.com` returns a high score, technique "homoglyph", closest brand `paypal.com`.
*No concept image yet. Design it in the same system before building.*

### 05 Defense Layer Builder
**Purpose:** configure the five layers.
**Shows:** one card per layer in order: Email Filter (base catch rate plus rules list with toggle and catch rate per rule), User Training (None / Basic / Advanced or custom rate), Application Control (effectiveness plus macro and executable blocking), Antivirus (detection rate), Segmentation (containment rate). Config versions (v1, v2), save as new version, YAML import/export, live residual-risk preview, applicability matrix, assumptions panel.
**Acceptance:** both official config files import unedited and display the same values as the files.

### 06 Attack Simulator (flagship)
**Purpose:** run 10,000 simulated attacks per email and show where they stop.
**Shows:**
- Controls: configuration, scope (all phishing or one email), runs (1,000 / 10,000 / 100,000), seed.
- Animated attack flow: particles move through the layers and drop out where stopped. Each particle is a real run sampled from the results, so the animation is data, not decoration.
- Funnel with counts and stop percentages.
- Results: blocked, passed, pass-through with 95% interval, closed-form value alongside.
- Breakdown by attack vector and by email (stacked bars).
- Sensitivity chart and recommendations.
**Acceptance:** results for a seed match the CLI exactly; full-dataset simulation returns in under 300 ms.

### 07 Before vs After
**Purpose:** compare two configurations.
**Shows:** two result cards; relative risk reduction in large type; a generated sentence ("Improving user training from None to Advanced, with all other controls unchanged, reduces the modeled chance an attack passes every layer from 9.21% to 3.29%, a 64.3% reduction."); a config diff of exactly what changed; layer-by-layer stop comparison; per-email table sorted by improvement.
**Acceptance:** a non-technical executive gets the point in under 10 seconds.

### 08 Awareness Academy
**Purpose:** interactive phishing-identification quiz.
**Shows:** questions built from analyzed emails ("Phishing or legitimate?", "Which element is most suspicious?", "Where does this link really go?"); instant feedback using engine evidence; progress, score, weak areas.
**Stretch:** "Use our quiz accuracy as the user layer," feeding a measured catch rate into the simulator.
**Acceptance:** a 10-question session completes with an explanation for every answer.

### 09 Validation & Reports
**Purpose:** prove it works.
**Shows:** total, actual phishing, actual genuine, correct, accuracy; confusion matrix; precision, recall, F1, false-positive rate; per-email results; misclassification panel explaining each error; pass-through summary for both configs; reproducibility footer (engine version, weights hash, seeds); JSON, CSV and PDF export.
**Acceptance:** shows ≥ 18/20 on the official set, computed live.

## 8. Key journeys

1. **Analyst triage:** upload → sort by risk → open the top email → read evidence → copy advice.
2. **CISO what-if:** Command Center → Defense → raise training → residual risk drops → Compare → export.
3. **Awareness case:** Compare → Academy quiz on real examples → (stretch) feed quiz accuracy into the user layer.
4. **Judge demo:** `plan.md` §7.

## 9. Design system

### Color

| Token | Hex | Use |
|---|---|---|
| Midnight | `#0B1120` | App background |
| Graphite | `#172334` | Cards, panels, table rows |
| Intelligence | `#38BDF8` | Primary actions, links, focus, neutral data |
| Protected | `#10B981` | Blocked attacks, passing checks, genuine |
| Warning | `#F59E0B` | Suspicious, soft failures |
| Threat | `#EF4444` | Phishing, passed attacks, failed checks |

Suggested neutrals: border `#24324A`, text `#E6EDF7`, muted text `#8A9BB4`.
**Rule:** green always means stopped or safe; red always means got through or dangerous. Never decorative.

### Typography
- **Inter** for UI: page titles 28–32 px semibold, section titles 16 px semibold, body 14 px.
- **JetBrains Mono** for technical data: scores, domains, URLs, headers, counts, percentages, seeds.

### Components
shadcn/ui primitives restyled with tokens (Card, Table, Tabs, Badge, Slider, Switch, Select, Dialog, Tooltip, Toast). Custom: RiskScore, EvidenceItem, AuthBadge, DomainDiff, LayerCard, AttackFlow, Funnel, ConfusionMatrix.

### Data visualization
- Layers always in the same order with the same icons.
- Pass-through to two decimals; counts with thousands separators.
- Every chart has a title, units and a "Modeled estimate" label where relevant.

### States and accessibility
- Empty, loading (skeleton) and error states on every screen.
- WCAG AA contrast; color never the only signal (icons and text accompany pass/fail).
- Keyboard navigation for Triage and Academy.

## 10. Copy guidelines

- Plain language first, technical detail beneath: "Replies go to a different domain", then `ms-account-verify.com` in monospace.
- Use "modeled", "estimated", "based on your configuration". Never "guaranteed" or "measured".
- Simulation footer: "Figures are model estimates from the assumptions shown, not measured outcomes."

## 11. Success metrics

| Context | Metric | Target |
|---|---|---|
| Hackathon | Correct on official set | ≥ 18/20 |
| Hackathon | Pass-through for both configs | Per email and aggregate |
| Hackathon | Demo | Under 3:00, two clean rehearsals |
| Product | Time to verdict for a reported email | < 1 minute |
| Product | Verdicts accepted without override | > 90% |

## 12. Business model (post-hackathon)

- Tiers by mailbox count: Team (self-serve), Business (integrations, scheduled reports), Enterprise (SSO, custom layers, on-premise engine).
- MSSP edition: multi-tenant workspaces, cross-client benchmarking.
- Education edition: Academy-led, discounted.

## 13. Roadmap after the hackathon

1. Mailbox integrations (Microsoft Graph, Gmail) and a report-phish add-in feeding Triage.
2. More layers: MFA / phishing-resistant authentication, web proxy, EDR.
3. Calibrate layer rates from real data: campaign click rates (GoPhish import), gateway logs, endpoint detections.
4. Correlated-layer modeling and uncertainty bands.
5. Multi-tenancy, SSO, audit log, roles.
6. Scheduled board reports and trends over time.
