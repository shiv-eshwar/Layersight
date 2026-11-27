# What is this?

**LayerSight — Phishing Resilience Intelligence**
*Detect the threat. Understand the risk. Prove your defenses.*

LayerSight is a phishing triage and layered-defense simulator. It reads emails as plain text, decides whether each one is phishing, and shows the evidence behind that decision. For every phishing email, it then estimates how likely the attack is to get past an organization's five defense layers (email filter, users, application control, antivirus and network segmentation), both before and after user awareness training.

Built for hackathon problem **1-18, Phishing Triage and Layered Defense Simulator**, and designed to grow into a B2B security SaaS product for enterprises, security operations teams, universities and managed security service providers.

## The question it answers

| Most phishing tools ask | LayerSight asks |
|---|---|
| Is this email dangerous? | If this phishing email enters our organization, how likely is it to reach a protected asset, and which security improvement would reduce that risk the most? |

## Inputs and outputs

| In | Out |
|---|---|
| Email files as text: headers and body; attachments described only by file name and type | A risk score (0 to 1), a phishing/genuine label, and the evidence for every email |
| A layer configuration: email filter rules, user training level, application control, antivirus detection rate, segmentation | Plain-language advice for the person who received the email |
| A second layer configuration (for example, trained users) | The chance an attack passes all layers, per email and overall, for both configurations, plus where attacks are stopped |
| Ground-truth labels for the test set | Accuracy, confusion matrix and per-email results |

## How it works

1. **Parse** each email into headers, authentication results, links, body text and attachment metadata.
2. **Check** it: sender versus Reply-To mismatch, SPF/DKIM/DMARC results, look-alike domains, link text that differs from the real destination, urgency and credential requests, risky attachment types.
3. **Score** it with transparent weighted rules. Every point in the score maps to a piece of evidence a person can read.
4. **Simulate** each phishing email 10,000 times through the layers that actually apply to it. Antivirus can't stop credential theft, so the simulator doesn't pretend it does.
5. **Compare** two configurations (untrained versus trained users) and report the risk reduction.
6. **Recommend** the change that gives the largest modeled reduction in risk.
7. **Validate** against the 20 labeled test emails and show the results honestly, including mistakes.

## Why it matters

No single defense layer is perfect. Each has holes, and an attack succeeds only when the holes line up (the "Swiss cheese" model). Training shrinks the human hole, and because layers multiply, a better human layer cuts end-to-end risk sharply.

Illustrative example (assumed numbers, not measurements): in a 10,000-attack simulation, 9.21% of attacks pass every layer with untrained users and 3.29% with trained users. That is a 64.3% risk reduction from training alone, with every other control unchanged.

## What it is not

- Not an email gateway. It doesn't block real mail.
- It never opens links, resolves domains or reads attachment contents. Attachments are metadata only.
- Not a campaign tool like GoPhish, and not just a mail scorer like SpamAssassin.
- Simulation outputs are modeled estimates built from stated assumptions, not measured security outcomes.

## Document map

| File | Read it for |
|---|---|
| `whatthis.md` | This one-page overview |
| `context.md` | The brief, constraints, domain background, assumptions and rules for contributors and AI agents. Read before writing code |
| `product.md` | Users, the nine screens, journeys, design system, success metrics |
| `architecture.md` | System structure, components, data flows, data model, architecture decisions |
| `engineering.md` | Algorithms, math, schemas, API, testing, conventions |
| `phases.md` | The build broken into phases with tasks and exit criteria |
| `plan.md` | Team, timeline, demo script, risks, next steps |
| `github.md` | How to commit and push, and the authorship rules every commit must follow |
