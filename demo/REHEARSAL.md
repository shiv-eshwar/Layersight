# Demo rehearsal

The judge path is Triage, one investigation, the simulator, the comparison, then Reports, and a title card. `make rehearse` runs that path three times and writes `demo/rehearsals/latest.json`. The exit is two consecutive clean runs under 3:00.

Say the lines below. Use the numbers on the screen. On the offline harness those numbers are labeled illustrative (9.21%, 3.29%, 64.3%). On the live app, the practice set at seed 42 is 20/20, untrained 9.59%, trained 3.82%, a 60.2% reduction. `make e2e-app` walks that path while `make dev` is running.

| Time | Screen | Say |
|---|---|---|
| 0:00–0:30 | Triage, sorted by risk | Security teams are flooded with suspicious email. LayerSight reads each one, scores it and shows why. Here are the 20 test emails, classified live. |
| 0:30–1:00 | Top phishing email | Every point of this score is evidence: replies go elsewhere, authentication failed, and this link imitates Microsoft with a zero for an O. And here's what we tell the user. |
| 1:00–1:45 | Simulator, 10,000 runs, untrained, seed 42 | Now the question nobody else answers: if it gets in, does it reach us? Ten thousand attacks, each through only the layers that apply. Credential phishing walks past antivirus, so we don't pretend antivirus stops it. The pass-through on screen is how many get through everything. |
| 1:45–2:15 | Compare | Change one thing, training, and residual risk falls from the untrained rate to the trained rate. LayerSight ranks what to improve next for this attack mix. |
| 2:15–2:45 | Reports | And it's real: the correct count out of 20 is on screen, and every result is reproducible from seed 42. |
| 2:45–3:00 | Title card | Traditional phishing tools tell you what is dangerous. LayerSight tells you how vulnerable you are, where your defenses fail, and what to improve next. |

## Before the room

- `make offline-check` with the demo machine's Wi-Fi off, or with the offline spec, which blocks every non-loopback request.
- `make video`, then copy `demo/backup/demo-fallback.webm` to the desktop. Record `E2E_TARGET=app make video` once the app is serving the same screens, so the backup matches the engine.
- Full screen, notifications off, other tabs closed.
- A terminal tab ready with `make compare` if the browser fails.

## Fallbacks

1. Upload fails: the demo set is already loaded. `POST /api/v1/demo/reset` restores it.
2. Browser fails: `make validate` when the official labels are present, and `make compare`.
3. Everything fails: play the backup video.
