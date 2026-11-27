# Plan

How we build, demo and win. Engineering tasks are in `phases.md`; this covers people, time, demo, risks and decisions.

## 1. Objective

1. Classify ≥ 18/20 official test emails correctly, with evidence.
2. Compute pass-through for both official configurations, per email and overall.
3. Show where attacks stop across five layers and how training changes it.
4. Tell the story in three minutes: detection → explanation → simulation → business value → proof.

## 2. Likely judging criteria

Update when the rubric is published.

| Criterion | What we show |
|---|---|
| Core target | Reports page and CLI: 18+/20, both rates |
| Technical depth | Vector-aware layer model, Monte Carlo with closed-form check, common random numbers, domain similarity |
| Honesty | Confusion matrix with errors, assumptions panel, "modeled estimate" labels |
| Innovation | Ranked "what to improve next"; credential theft bypassing endpoint controls |
| UX | Nine consistent screens, calm design system |
| Presentation | One clear message in three minutes |

## 3. Team and roles

For four people; merge for smaller teams.

| Role | Owns | Phases |
|---|---|---|
| Detection engineer | Parser, rules, similarity, scoring, advice, validation, dev dataset | 0, 1 |
| Simulation and backend engineer | Config + adapter, layer model, Monte Carlo, comparison, recommendations, API, DB, seed | 0, 2, 3 |
| Frontend engineer | Shell, Triage, Investigation, Reports, Intelligence, API client | 0, 4, 6 |
| Design, frontend and pitch | Tokens, Defense, Simulator, Compare, animation, Command Center, Academy, demo, video | 0, 5, 6, 7 |

Three people: the detection engineer also takes the API. Two: one on engine + API, one on all UI; apply the cut line early.

## 4. Timeline

Template for 48 hours; scale for other lengths.

| Hours | Milestone | Done when |
|---|---|---|
| 0–2 | M0 Foundations | Phase 0 exit |
| 2–12 | M1 Core target in CLI | `validate` ≥ 18/20; `compare` prints both rates |
| 12–20 | M2 Integrated core | API live; Triage, Investigation, Reports on real data |
| 20–32 | M3 Flagship | Defense, Simulator, Compare; what-if, recommendations |
| 32–40 | M4 Complete | Intelligence, Command Center, Academy (per cut line) |
| 40–46 | M5 Demo-ready | Phase 7 exit |
| 46–48 | M6 Submit | Repo, README, video, slides; buffer |

Integration checkpoints at hours 6, 12, 20, 32, 40: merge, `make test`, `make demo`, walk the demo path. **Feature freeze at hour 40.**

## 5. Ways of working

- Every commit follows `github.md`: shiv-eshwar is the only author, committer and contributor, and each commit is pushed to `origin main` right away.
- `main` always runs; CI green before merge.
- Contracts change only by agreement; run `make types` and fix compile errors in the same commit.
- Every weight or assumption change: `make validate`, then a line in §11.
- Stand-up at each checkpoint: done, next, blocked.

## 6. Definition of done

- **Task:** code, tests, lint, types; committed and pushed per `github.md`.
- **Screen:** real data; empty, loading, error states; design system; no console errors.
- **Demo:** two clean timed rehearsals; offline; backup video.

## 7. Three-minute demo

| Time | On screen | Say |
|---|---|---|
| 0:00–0:30 | Triage: drop the 20 official emails, sort by risk | "Security teams are flooded with suspicious email. LayerSight reads each one, scores it and shows why. Here are the 20 test emails, classified live." |
| 0:30–1:00 | Investigation of the top phishing email: Reply-To mismatch, DMARC fail, look-alike domain, link text vs real address, advice | "Every point of this score is evidence: replies go elsewhere, authentication failed, and this link imitates Microsoft with a zero for an O. And here's what we tell the user." |
| 1:00–1:45 | Simulator: 10,000 runs per email, untrained config; flow animates | "Now the question nobody else answers: if it gets in, does it reach us? Ten thousand attacks, each through only the layers that apply. Credential phishing walks past antivirus, so we don't pretend antivirus stops it. X% get through everything." |
| 1:45–2:15 | Compare (or Defense slider): trained users | "Change one thing, training, and residual risk falls from X to Y, a Z% reduction. And LayerSight ranks what to improve next for your attack mix." |
| 2:15–2:45 | Reports: confusion matrix, per-email results, any error | "And it's real: N out of 20 correct on the official set, every result reproducible from a seed." |
| 2:45–3:00 | Title card | "Traditional phishing tools tell you what is dangerous. LayerSight tells you how vulnerable you are, where your defenses fail, and what to improve next." |

Use the numbers the engine produces on the official data, not the illustrative 9.21% / 3.29%.

**Fallbacks:** upload fails → demo mode already has the data; browser fails → CLI (`make validate`, `layersight compare …`); everything fails → video.

## 8. Judge Q&A

| Question | Answer |
|---|---|
| Are these real numbers? | Accuracy is measured on the official set. Pass-through is a modeled estimate from the configured layer rates, made email-specific by each email's features. All assumptions are visible and editable. |
| Why rules, not ML? | Twenty emails can't train a model without overfitting, and the brief asks for evidence. Weights are in a config file and were tuned on a separate dev set. |
| How do you know the simulation is right? | Every Monte Carlo result is checked against the exact closed form, within the 95% interval, in automated tests. The illustrative scenario reproduces exactly. |
| Why Monte Carlo if a formula exists? | It gives the distribution of where attacks stop, and extends to uncertain or correlated layer rates where the simple product breaks. |
| Aren't layers correlated? | Yes; independence is a stated assumption, partly offset by deriving all layer rates from the same email's features. Correlated modeling is on the roadmap. |
| False positives? | Confusion matrix and false-positive rate are shown; the threshold is configurable. |
| Versus SpamAssassin and GoPhish? | SpamAssassin scores mail but doesn't model layers. GoPhish runs campaigns but doesn't analyze email or model defenses. We connect detection, awareness and layered defense. |
| Why doesn't antivirus affect some emails? | Credential-harvesting and payment-fraud emails carry no malware, so endpoint controls can't stop them, which is why training matters most there. |

## 9. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Email format differs from assumptions | High | High | Tolerant parser; inspect data in hour one |
| Config format differs | High | Medium | Adapter with warnings |
| Below 18/20 | Medium | High | Hard-case dev set; error analysis from hour 6 |
| Overfitting to test set | Medium | Medium | Tune on dev only; disclose any test-informed change |
| Simulation credibility challenged | Medium | High | Closed-form check, intervals, assumptions panel, applicability matrix |
| Nine screens too much | High | Medium | Cut line; core path first |
| Demo network or hardware failure | Low | High | Offline mode, CLI, video, second laptop |
| Late integration breakage | Medium | High | Frozen contracts, generated types, checkpoints, freeze |
| Wrong commit authorship | Low | High | `.githooks` enforce identity and strip co-author trailers; verify per `github.md` §5 |
| Inconsistent concept visuals | High | Low | One design system; replace gradients and mismatched nav |

## 10. Pre-demo checklist

- [ ] `make demo` on the demo laptop with Wi-Fi off
- [ ] Full screen, notifications off, other tabs closed
- [ ] Reports and Compare show the rehearsed numbers
- [ ] Seed fixed to the rehearsed value
- [ ] Video on the desktop; CLI commands ready in a terminal tab
- [ ] Spoken numbers match the screen
- [ ] GitHub contributors list shows only shiv-eshwar

## 11. Decision log

| Date | Decision | Reason | Validation effect |
|---|---|---|---|
| 2026-11-27 | Explainable rule-based scoring | Dataset size; evidence requirement | — |
| 2026-11-27 | Vector-aware layer applicability | Antivirus and app control don't stop credential theft | — |
| 2026-11-27 | Common random numbers for comparisons | Fair before/after | — |
| 2026-11-27 | Git hooks enforce shiv-eshwar as sole author and committer | Contributor rule in `github.md` | — |

## 12. Open questions

- Official email, label and config formats.
- Event length, team size, rubric.
- Hosted URL required?
- Live demo only, or slides too?

## 13. First two hours

1. Monorepo skeleton and docker compose.
2. Open the official data; write its format into `context.md` §10.
3. Freeze contracts in `engine/layersight/models.py`; generate mocks.
4. Start the dev dataset (detection) and the config adapter (simulation).
5. Web shell with tokens and nav (frontend).
6. Agree the demo story and screen order (design and pitch).
