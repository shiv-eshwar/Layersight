# Context

The single source of background for anyone, human or AI agent, working on LayerSight. Read this first. If another document disagrees with this one about requirements or constraints, this one wins; update it rather than working around it.

## 1. The hackathon brief

**Problem 1-18: Phishing Triage and Layered Defense Simulator.**
Build a tool that analyzes phishing emails and then estimates how well a set of defense layers would stop them.

- **Input:** email files as text (headers and body, with attachments described only by name and type), and a layer configuration (email filter rules, user training level, application control, antivirus detection rate, segmentation).
- **Output:** risk score and evidence per email, user advice, and the chance that an attack passes all layers, before and after training.
- **Features:**
  - Header checks (sender and Reply-To mismatch, authentication results) and link checks (look-alike domains, text versus real address).
  - Simulation of the layers for each phishing email (for example 10,000 runs) with a chart of where attacks stop.
  - Comparison of two configurations, such as untrained and trained users.
- **Core target:** classify at least 18 of 20 test emails correctly and compute the pass-through rate for two configurations.
- **Stretch goals:** domain similarity score, quiz mode for users.
- **Test data:** 20 emails (12 phishing, 8 genuine) and two layer configuration files.
- **Expected outcome:** a tool that shows why awareness and layered defense work together.
- **Comparison:** SpamAssassin scores mail but does not show how defense layers combine; GoPhish only runs campaigns.

## 2. Requirements traceability

Priority: P0 = needed for the core target, P1 = differentiator, P2 = stretch.

| ID | Requirement | How we meet it | Engine module | Screen | Priority |
|---|---|---|---|---|---|
| R1 | Read emails as text, attachment metadata only | Tolerant parser; attachments reduced to name, extension, declared type | `parsing` | 02 | P0 |
| R2 | Read a layer configuration | Canonical YAML schema plus an adapter for the official format | `config` | 05 | P0 |
| R3 | Risk score per email | Weighted rules mapped to 0–1 with a logistic curve | `scoring` | 02, 03 | P0 |
| R4 | Evidence per email | Each fired rule becomes a readable evidence item with its contribution | `scoring` | 03 | P0 |
| R5 | User advice | Templates keyed by evidence type | `scoring.advice` | 03 | P0 |
| R6 | Sender vs Reply-To mismatch | Registrable-domain comparison of From, Reply-To, Return-Path | `features.headers` | 03 | P0 |
| R7 | Authentication results | Parse `Authentication-Results` and `Received-SPF` for SPF, DKIM, DMARC | `features.auth` | 03 | P0 |
| R8 | Look-alike domains | Similarity to protected brands and org domains | `features.domains` | 03, 04 | P0 |
| R9 | Link text vs real address | Compare anchor-text domain with `href` domain | `features.links` | 03, 04 | P0 |
| R10 | Per-email simulation, 10,000 runs | Seeded, vectorized Monte Carlo with closed-form check | `simulation` | 06 | P0 |
| R11 | Chart of where attacks stop | Funnel and stacked bars from simulation counts | — | 06 | P0 |
| R12 | Compare two configurations | Same random draws for both (common random numbers); relative reduction | `simulation.compare` | 07 | P0 |
| R13 | Pass-through before and after training | Comparison output per email and aggregate | `simulation.compare` | 03, 07 | P0 |
| R14 | ≥ 18/20 correct | Validation command and CI gate | `validation` | 09 | P0 |
| R15 | Domain similarity score | 0–1 score with technique label and character diff | `features.domains` | 04 | P1 |
| R16 | Quiz mode | Questions generated from analyzed emails | `quiz` | 08 | P2 |
| R17 | Show awareness and layers working together | Comparison narrative, funnel, recommendations | `simulation.recommend` | 01, 06, 07 | P1 |

## 3. Inputs: known and assumed

**Known:** 20 test emails (12 phishing, 8 genuine) as text; two layer configuration files.

**Not yet known, so we design for it:**

- **Email format.** Could be RFC 5322 `.eml`, MIME multipart, or simplified text. Attachments may appear as MIME parts with `Content-Disposition: attachment`, or as pseudo-lines like `Attachment: invoice.pdf.exe (application/x-msdownload)`. We read only name and type in every case.
- **Labels.** May be a CSV, part of file names, or a header. Only the validation module reads labels, never the classifier.
- **Config format.** Unknown keys and scales (percent vs fraction, numeric vs named training level). We define a canonical schema (`engineering.md` §9) and write an adapter once the files arrive.

When the official data lands: record its exact format in §10, write the adapter, and copy the files unchanged into `data/test/`.

## 4. Hard constraints

1. Attachments are metadata only: name, extension, declared type. Never decode or inspect content.
2. Analysis is offline and deterministic: no DNS, WHOIS, URL fetching or external APIs.
3. The classifier never sees labels or file names. Classifying by file name invalidates the core target.
4. Every number in the UI comes from the engine. The frontend never computes metrics.
5. Every simulation records its seed, run count, config snapshot and engine version.
6. Illustrative or demo numbers are labeled as such. Simulation results are always called modeled estimates.
7. Email content is hostile input. Never render email HTML; show sanitized text with defanged links.

## 5. Domain primer

### 5.1 Email authentication

| Mechanism | What it proves | Where we read it | Phishing signal |
|---|---|---|---|
| SPF | The sending server may send for the envelope domain (`Return-Path`) | `Authentication-Results: spf=…`, `Received-SPF` | `fail`, `softfail` |
| DKIM | A domain signed the message and it wasn't altered | `Authentication-Results: dkim=…` | `fail`, `none` |
| DMARC | SPF or DKIM passed **and** aligns with the visible From domain | `Authentication-Results: dmarc=…` | `fail` |

Users never see these results; filters do. So authentication failures raise the email filter's catch probability, not the user's.

### 5.2 Header deception

- **Reply-To mismatch:** `From: security@microsoft.com`, `Reply-To: support@ms-account-verify.com`. Replies go to the attacker.
- **Display-name spoofing:** `"Microsoft Account Team" <alert@random-domain.xyz>`.
- **Return-Path mismatch:** envelope sender differs from the visible sender.
- **Free-mail impersonation:** a "CEO" or "IT department" writing from free webmail.

### 5.3 Link deception

- **Text versus real address:** the link reads `https://microsoft.com/verify` but points to `http://micros0ft-login.net`.
- **Look-alike techniques:**

| Technique | Example | Imitates |
|---|---|---|
| Homoglyph / character swap | `micros0ft.com`, `paypa1.com` | microsoft.com, paypal.com |
| Typosquatting | `amazom.com` | amazon.com |
| Combosquatting | `amazon-support.net` | amazon.com |
| Subdomain abuse | `paypal.com.secure-login.io` | paypal.com |
| TLD swap | `microsoft.co` | microsoft.com |
| Punycode / IDN | `xn--pypal-4ve.com` | paypal.com |

- Other signals: IP-address URLs, shorteners, `@` inside URLs, plain-HTTP login pages, unusual TLDs.

The **registrable domain** (eTLD+1, such as `example.co.uk`) is the unit we compare, using `tldextract` with a bundled public suffix list.

### 5.4 Attack vectors and which layers apply

The most important modeling rule in the product: layers only stop what they can see.

| Attack vector | Email filter | User | Application control | Antivirus | Segmentation |
|---|---|---|---|---|---|
| Malware attachment | ✓ | ✓ opens or enables content | ✓ | ✓ | ✓ |
| Malware via link (download) | ✓ | ✓ clicks and runs | ✓ | ✓ | ✓ |
| Credential harvesting | ✓ | ✓ enters credentials | — | — | ✓ limits what stolen credentials reach |
| Payment fraud / BEC (no link, no attachment) | ✓ | ✓ acts on the request | — | — | — |

"Passes all layers" means the attack reaches its objective: code running with access to a protected asset, credentials that reach a protected system, or a fraudulent payment.

### 5.5 Defense in depth and the math

If layer $i$ stops an attack with probability $p_i$ and layers act independently, the chance an attack passes every applicable layer is

$$P_{\text{pass}} = \prod_{i \in \text{applicable}} (1 - p_i)$$

Monte Carlo draws each run layer by layer and records where it stops. We use it because it gives the "where attacks stop" distribution for charts and extends to uncertain or correlated parameters. The closed form above verifies it. At 10,000 runs, the 95% confidence interval around 9.21% is about ±0.57 percentage points.

**Known limitation:** independence is an assumption. Sophisticated attacks tend to beat several layers at once. We partly capture this by deriving every layer's probability from the same email's features, and we state the limitation on screen.

## 6. The illustrative scenario

These numbers appear in the concept designs. The engine must reproduce them exactly as a golden test, using an email where all five layers apply and no filter rule or user-cue modifier changes the base rates.

| Layer | Stop rate (untrained) | Remaining of 10,000 | Stop rate (trained) |
|---|---|---|---|
| Email filter | 35% | 6,500 | 35% |
| User | 30% | 4,550 | 75% |
| Application control | 25% | 3,413 | 25% |
| Antivirus | 55% | 1,536 | 55% |
| Segmentation | 40% | 921 | 40% |

- Untrained: 0.65 × 0.70 × 0.75 × 0.45 × 0.60 = 0.0921 → 9.21% pass, 90.79% blocked.
- Trained: 0.65 × 0.25 × 0.75 × 0.45 × 0.60 = 0.0329 → 3.29% pass.
- Relative reduction: (9.21 − 3.29) / 9.21 = 64.3%.

The same untrained config gives very different results by vector. Credential harvesting passes 27.3% of the time (0.65 × 0.70 × 0.60). Payment fraud passes 45.5% (0.65 × 0.70). Endpoint controls don't help against either, which is exactly the insight the product should surface.

## 7. Competitive landscape

| Product type | What it does | Gap LayerSight fills |
|---|---|---|
| SpamAssassin | Rule-based mail scoring | No model of how layers combine; no awareness link |
| GoPhish | Runs phishing campaigns, tracks clicks | No email analysis, no defense modeling |
| Secure email gateways | Block mail at the perimeter | One layer; no end-to-end residual risk |
| Awareness platforms | Training and simulated phishing | Measure clicks, not end-to-end risk across technical controls |

## 8. Glossary

| Term | Meaning |
|---|---|
| Pass-through rate | Share of simulated attacks that get past every applicable layer |
| Residual risk | The pass-through rate, framed for executives |
| Layer configuration | The five layer settings that parameterize a simulation |
| Attack vector | How an email does harm: malware attachment, malware link, credential harvesting, payment fraud |
| Evidence | One fired rule: what was found, where, and how much it moved the score |
| Risk band | Low, Suspicious, High, Critical, derived from the risk score |
| User cue score | 0–1 measure of how many warning signs a person could notice |
| Common random numbers | Same random draws for two configurations, so their difference reflects only the config change |
| Registrable domain | Domain plus public suffix, such as `micros0ft.com` |
| BEC | Business email compromise: impersonation to trigger payments or data release |

## 9. Assumptions log

| ID | Assumption | Revisit when |
|---|---|---|
| A1 | Layers are independent, given the email | Correlated modeling is added |
| A2 | Training levels map to base user catch rates: none 0.30, basic 0.55, advanced 0.75 | The official config defines its own scale |
| A3 | Each email has one primary attack vector, chosen by severity | A test email clearly has two |
| A4 | Password-protected archives halve antivirus detection | Never without data; labeled as assumption |
| A5 | Aggregate pass-through weights each phishing email equally | Prevalence data exists |
| A6 | Simulation runs on emails predicted as phishing; validation mode can use ground truth | — |
| A7 | Classification threshold is 0.50 | Dev-set error analysis suggests better |

## 10. Official test data notes

Inspected 2026-11-27. The official 20 emails and the two layer configuration files have not been delivered. `data/test/` holds a local practice set in that shape (12 phishing, 8 genuine, untrained and trained configs) so the validation path can be exercised. It is not the official set. See `data/test/README.md`. Replace those files byte for byte when the real ones arrive.

Until the official files exist:

- Format, label location, and config schema stay unknown. The engine accepts RFC 5322, MIME, and the simplified text shape described in section 3, and it validates configs against the canonical schema in `engineering.md` section 9.
- Tuning and rule coverage use `data/dev/` (36 labeled messages, plus `untrained.yaml` and `trained.yaml`). That corpus is not a substitute for the official score.
- Do not report an accuracy number against `data/test/` while it is empty. The validation gate stays in place and will fail closed until the real files are copied in unchanged.

## 11. Non-goals for the hackathon

- Live mailbox integration (Microsoft 365, Google Workspace).
- ML classifiers trained on 20 emails.
- Sandboxing, URL detonation, attachment content scanning.
- Authentication, multi-tenancy, billing (the data model leaves room).

## 12. Rules for contributors and AI agents

1. Read this file, then the doc for your area, before changing code.
2. Never use file names, labels or test-set knowledge in the classifier. Weights live in `engine/layersight/scoring/weights.yaml`, not in code.
3. Never add network calls to the analysis or simulation path.
4. Never render email HTML. Use the sanitized text and defanged links from the API.
5. Every UI metric comes from an API response. No hardcoded numbers except clearly labeled demo copy.
6. Every simulation is seeded. Tests use fixed seeds.
7. After changing a weight or assumption, run `layersight validate` and log the result in `plan.md` §11.
8. The engine imports no web or database code.
9. Use the glossary terms consistently in code, UI and docs.
10. Follow `github.md` for every commit: shiv-eshwar is the only author, committer and contributor, and every commit is pushed right away.

## 13. Open questions

- Exact format of emails, labels and config files.
- Event length, team size, judging criteria.
- Hosted URL required, or local demo acceptable?
- Is there an official list of protected brands or org domains?
