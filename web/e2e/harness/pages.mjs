import {
  assumptions,
  comparisonNarrative,
  counts,
  DATASET_ID,
  emails,
  ENGINE_VERSION,
  formatCount,
  formatPct,
  formatReduction,
  narrative,
  reduction,
  RUNS,
  SEED,
  SHOWCASE,
  validationRows,
  WEIGHTS_HASH,
  wilsonInterval,
} from "./fixture.mjs";

const TITLES = {
  "/": "Security Command Center",
  "/triage": "Email Triage",
  "/intelligence": "URL & Domain Intelligence",
  "/defense": "Defense Layer Builder",
  "/simulator": "Attack Simulator",
  "/compare": "Before vs After",
  "/academy": "Awareness Academy",
  "/reports": "Validation & Reports",
  "/demo/title": "LayerSight",
};

export function render(pathname, state) {
  const title = titleFor(pathname);
  if (!title) return null;
  const main =
    state === "loading" || state === "empty" || state === "error"
      ? stateBlock(state, pathname)
      : `<div data-testid="screen-ready">${bodyFor(pathname)}</div>`;
  return layout(title, main);
}

function titleFor(pathname) {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/triage/")) return "Threat Investigation";
  return null;
}

function stateBlock(state, pathname) {
  if (state === "loading") {
    return `<div data-testid="screen-loading">Loading this screen.</div>`;
  }
  if (state === "empty") {
    return `<div data-testid="screen-empty"><p>Nothing to show yet. Upload emails (.eml, .txt, or .zip) to classify them and open this screen.</p></div>`;
  }
  return `<div data-testid="screen-error"><p>This screen could not load.</p><a data-testid="retry" href="${escapeHtml(pathname)}">Retry</a></div>`;
}

function bodyFor(pathname) {
  if (pathname.startsWith("/triage/")) return investigation(pathname.slice("/triage/".length));
  switch (pathname) {
    case "/":
      return commandCenter();
    case "/triage":
      return triage();
    case "/intelligence":
      return intelligence();
    case "/defense":
      return defense();
    case "/simulator":
      return simulator();
    case "/compare":
      return compare();
    case "/academy":
      return academy();
    case "/reports":
      return reports();
    case "/demo/title":
      return titleCard();
    default:
      return "";
  }
}

function layout(title, main) {
  const assumptionItems = assumptions
    .map(
      ([id, text]) =>
        `<li data-assumption="${id}"><strong>${id}.</strong> ${escapeHtml(text)}</li>`,
    )
    .join("");
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)} · LayerSight</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <div data-testid="app-shell">
    <nav aria-label="Primary">
      <a href="/" data-testid="nav-command">Command Center</a>
      <a href="/triage" data-testid="nav-triage">Triage</a>
      <a href="/intelligence" data-testid="nav-intelligence">Intelligence</a>
      <a href="/defense" data-testid="nav-defense">Defense</a>
      <a href="/simulator" data-testid="nav-simulator">Simulator</a>
      <a href="/compare" data-testid="nav-compare">Compare</a>
      <a href="/academy" data-testid="nav-academy">Academy</a>
      <a href="/reports" data-testid="nav-reports">Reports</a>
    </nav>
    <header class="topbar">
      <span data-testid="dataset-select">Official test set</span>
      <span data-testid="config-pair">Untrained v1 → Trained v2</span>
      <details data-testid="assumptions-panel">
        <summary data-testid="assumptions-button">Modeled estimates</summary>
        <ul>${assumptionItems}</ul>
        <p>Figures are model estimates from the assumptions shown, not measured outcomes.</p>
      </details>
    </header>
    <main>
      <h1 data-testid="screen-title">${escapeHtml(title)}</h1>
      ${main}
    </main>
  </div>
</body>
</html>`;
}

function caption(text) {
  return `<p data-testid="demo-caption">${escapeHtml(text)}</p>`;
}

function commandCenter() {
  const tally = counts();
  return `
    ${figuresNote()}
    <section class="kpis">
      <p>Emails analyzed <strong>${tally.total}</strong></p>
      <p>Phishing <strong>${tally.phishing}</strong></p>
      <p>Genuine <strong>${tally.genuine}</strong></p>
      <p>Accuracy <strong>${SHOWCASE.validation.correct}/${SHOWCASE.validation.total}</strong></p>
    </section>
    <p>Residual risk before training ${formatPct(SHOWCASE.passRateUntrained)}, after ${formatPct(SHOWCASE.passRateTrained)}.</p>
    <p data-testid="top-recommendation">Advance user training. ${modeledReduction()}</p>
    <p><a href="/triage">Open triage</a> · <a href="/simulator">Open the simulator</a> · <a href="/reports">Open reports</a></p>
  `;
}

function triage() {
  const tally = counts();
  const rows = emails
    .map(
      (email) => `<a data-testid="triage-row" data-risk="${email.risk}" data-label="${email.label}" data-email-id="${escapeHtml(email.id)}" href="/triage/${escapeHtml(email.id)}">
        <span>${escapeHtml(email.subject)}</span>
        <span>${escapeHtml(email.sender)}</span>
        <span>${escapeHtml(email.label)}</span>
        <span class="mono">${email.risk.toFixed(2)}</span>
        <span>${escapeHtml(email.attackVector)}</span>
        <span>${escapeHtml(email.topEvidence)}</span>
      </a>`,
    )
    .join("");
  return `
    <div data-testid="triage-dropzone">Drop .eml, .txt, or .zip files. Demo mode already loaded the official set, so the walkthrough does not depend on this upload.</div>
    <p>
      <span data-testid="triage-tab-all">All ${tally.total}</span>
      <span data-testid="triage-tab-phishing">Phishing ${tally.phishing}</span>
      <span data-testid="triage-tab-genuine">Genuine ${tally.genuine}</span>
    </p>
    <p><a data-testid="sort-risk" href="/triage?sort=risk">Sort by risk</a></p>
    <input data-testid="triage-search" type="search" aria-label="Search sender, subject, or domain">
    <div data-testid="triage-table">${rows}</div>
    ${caption("Security teams are flooded with suspicious email. LayerSight reads each one, scores it and shows why. Here are the 20 test emails, classified live.")}
  `;
}

function investigation(id) {
  const email = SHOWCASE.email;
  if (id !== email.id) {
    const row = emails.find((item) => item.id === id);
    if (!row) return `<div data-testid="screen-error"><p>That email is not in the demo set.</p><a data-testid="retry" href="/triage">Retry</a></div>`;
    return `
      <p data-testid="verdict">${escapeHtml(row.label)}</p>
      <p data-testid="risk-score" class="mono">${row.risk.toFixed(2)}</p>
      <p data-testid="band">${escapeHtml(row.band)}</p>
      <p data-testid="attack-vector">${escapeHtml(row.attackVector)}</p>
      <p data-testid="header-from">${escapeHtml(row.sender)}</p>
      <p data-testid="header-reply-to" data-mismatch="false">${escapeHtml(row.sender)}</p>
      <p data-testid="header-return-path">${escapeHtml(row.sender)}</p>
      <p><span data-testid="auth-spf" data-status="pass">SPF pass</span>
         <span data-testid="auth-dkim" data-status="pass">DKIM pass</span>
         <span data-testid="auth-dmarc" data-status="pass">DMARC pass</span></p>
      <ul data-testid="evidence-list"><li data-testid="evidence-item" data-rule="G01">${escapeHtml(row.topEvidence)}</li></ul>
      <div data-testid="advice"><p>No strong warning signs. Still confirm unexpected requests for money or credentials through a separate channel.</p></div>
    `;
  }
  const evidence = email.evidence
    .map(
      (item) =>
        `<li data-testid="evidence-item" data-rule="${item.rule_id}"><strong>${escapeHtml(item.title)}</strong> ${escapeHtml(item.detail)}</li>`,
    )
    .join("");
  const advice = email.advice.map((line) => `<p>${escapeHtml(line)}</p>`).join("");
  return `
    <p data-testid="verdict">Phishing</p>
    <p data-testid="risk-score" class="mono">${email.risk.toFixed(2)}</p>
    <p data-testid="band">${escapeHtml(email.band)}</p>
    <p data-testid="attack-vector">${escapeHtml(email.attackVector)}</p>
    <p data-testid="header-from">${escapeHtml(email.sender)}</p>
    <p data-testid="header-reply-to" data-mismatch="true">${escapeHtml(email.replyTo)}</p>
    <p data-testid="header-return-path">${escapeHtml(email.returnPath)}</p>
    <p>
      <span data-testid="auth-spf" data-status="${email.auth.spf}">SPF ${email.auth.spf}</span>
      <span data-testid="auth-dkim" data-status="${email.auth.dkim}">DKIM ${email.auth.dkim}</span>
      <span data-testid="auth-dmarc" data-status="${email.auth.dmarc}">DMARC ${email.auth.dmarc}</span>
    </p>
    <ul data-testid="evidence-list">${evidence}</ul>
    <table>
      <tr data-testid="link-row" data-deceptive="true">
        <td>${escapeHtml(email.linkText)}</td>
        <td class="mono">${escapeHtml(email.linkHref)}</td>
      </tr>
    </table>
    <div data-testid="advice">${advice}</div>
    <p data-testid="defense-outlook">Illustrative pass-through for this malware-style scenario: ${formatPct(SHOWCASE.passRateUntrained)} untrained, ${formatPct(SHOWCASE.passRateTrained)} trained. <a href="/simulator">Simulate this email</a></p>
    ${caption("Every point of this score is evidence: replies go elsewhere, authentication failed, and this link imitates Microsoft with a zero for an O. And here's what we tell the user.")}
  `;
}

function intelligence() {
  return `
    ${figuresNote()}
    <table>
      <tr>
        <td class="mono">micros0ft.com</td>
        <td>microsoft.com</td>
        <td class="mono">0.98</td>
        <td>homoglyph</td>
      </tr>
    </table>
    <form method="get" action="/intelligence">
      <label>Check a domain <input name="domain" value="paypa1.com"></label>
    </form>
  `;
}

function defense() {
  const layers = ["Email filter", "User training", "Application control", "Antivirus", "Segmentation"];
  const cards = layers.map((layer) => `<article><h2>${layer}</h2></article>`).join("");
  return `${figuresNote()}<div class="layers">${cards}</div><p>Import untrained.yaml and trained.yaml without editing them. Save creates a new version.</p>`;
}

function simulator() {
  const [low, high] = wilsonInterval(SHOWCASE.passRateUntrained, RUNS);
  const steps = SHOWCASE.funnel
    .map(
      (step) =>
        `<li><span>${escapeHtml(step.layer)}</span> <span class="mono">${formatCount(step.stopped)} stopped</span> <span class="mono">${formatCount(step.remaining)} remaining</span></li>`,
    )
    .join("");
  return `
    ${figuresNote()}
    <p data-testid="sim-config">Untrained users (v1)</p>
    <p data-testid="sim-runs" data-value="${RUNS}">${formatCount(RUNS)} runs per email</p>
    <p data-testid="sim-seed" data-value="${SEED}">Seed ${SEED}</p>
    <ol data-testid="funnel">${steps}</ol>
    <p data-testid="pass-rate" data-value="${SHOWCASE.passRateUntrained}">Pass-through ${formatPct(SHOWCASE.passRateUntrained)}</p>
    <p data-testid="closed-form" data-value="${SHOWCASE.passRateUntrained}">Closed form ${formatPct(SHOWCASE.passRateUntrained)}</p>
    <p data-testid="ci95">95% interval ${formatPct(low)} to ${formatPct(high)}</p>
    <p data-testid="attack-flow">Static funnel. Particles follow these stop counts when motion is allowed.</p>
    ${caption(`Illustrative: ten thousand attacks through the layers that apply. ${formatPct(SHOWCASE.passRateUntrained)} get through every layer. Credential phishing skips antivirus, so its pass-through is higher. Figures are modeled estimates.`)}
  `;
}

function compare() {
  return `
    ${figuresNote()}
    <article data-testid="result-card-a" data-pass-rate="${SHOWCASE.passRateUntrained}">
      <h2>Untrained users</h2>
      <p class="mono">${formatPct(SHOWCASE.passRateUntrained)}</p>
    </article>
    <article data-testid="result-card-b" data-pass-rate="${SHOWCASE.passRateTrained}">
      <h2>Trained users</h2>
      <p class="mono">${formatPct(SHOWCASE.passRateTrained)}</p>
    </article>
    <p data-testid="relative-reduction" data-value="${reduction}">${formatReduction(reduction)} relative reduction</p>
    <p data-testid="comparison-narrative">${escapeHtml(narrative)}</p>
    <pre data-testid="config-diff">user_training.level: none → advanced</pre>
    <p data-testid="top-recommendation">Advance user training from None to Advanced. ${modeledReduction()}</p>
    ${caption(`Change training, and illustrative residual risk falls from ${formatPct(SHOWCASE.passRateUntrained)} to ${formatPct(SHOWCASE.passRateTrained)}, a ${formatReduction(reduction)} reduction. LayerSight ranks what to improve next for this attack mix.`)}
  `;
}

function academy() {
  return `
    <article>
      <h2>Phishing or legitimate?</h2>
      <p>${escapeHtml(SHOWCASE.email.subject)}</p>
      <p>Feedback: ${escapeHtml(SHOWCASE.email.evidence[2].detail)}</p>
    </article>
  `;
}

function reports() {
  const rows = validationRows();
  const correct = rows.filter((row) => row.correct).length;
  const accuracy = correct / rows.length;
  const matrix = confusion(rows);
  const table = rows
    .map(
      (row) =>
        `<tr><td>${escapeHtml(row.filename)}</td><td>${row.actual}</td><td>${row.predicted}</td><td>${row.correct ? "correct" : "miss"}</td><td class="mono">${row.risk.toFixed(2)}</td></tr>`,
    )
    .join("");
  return `
    ${figuresNote()}
    <p data-testid="report-total" data-value="${rows.length}">${rows.length} emails</p>
    <p data-testid="report-correct" data-value="${correct}">${correct} correct</p>
    <p data-testid="accuracy" data-value="${accuracy}">Accuracy ${formatPct(accuracy)}</p>
    <table data-testid="confusion-matrix">
      <tr><th></th><th>Predicted phishing</th><th>Predicted genuine</th></tr>
      <tr><th>Actual phishing</th><td>${matrix.tp}</td><td>${matrix.fn}</td></tr>
      <tr><th>Actual genuine</th><td>${matrix.fp}</td><td>${matrix.tn}</td></tr>
    </table>
    <table data-testid="per-email-table">
      <tr><th>File</th><th>Actual</th><th>Predicted</th><th>Result</th><th>Risk</th></tr>
      ${table}
    </table>
    <p><a data-testid="export-json" href="/api/v1/datasets/${DATASET_ID}/report.json">JSON</a>
       <a data-testid="export-csv" href="/api/v1/datasets/${DATASET_ID}/report.csv">CSV</a></p>
    <p data-testid="reproducibility" data-engine-version="${ENGINE_VERSION}" data-weights-hash="${WEIGHTS_HASH}" data-seed="${SEED}">
      Engine ${ENGINE_VERSION}. Weights hash ${WEIGHTS_HASH}. Seed ${SEED}. ${formatCount(RUNS)} runs.
      Figures are model estimates from the assumptions shown, not measured outcomes.
    </p>
    <p><a data-testid="show-title-card" href="/demo/title">End on the title card</a></p>
    ${caption(`${SHOWCASE.validation.correct} out of ${SHOWCASE.validation.total} correct on this illustrative report. Every result is reproducible from a seed. The live app replaces these figures with the engine.`)}
  `;
}

function titleCard() {
  return `<section data-testid="title-card"><p>Traditional phishing tools tell you what is dangerous. LayerSight tells you how vulnerable you are, where your defenses fail, and what to improve next.</p></section>`;
}

function figuresNote() {
  return `<p data-testid="modeled-estimate">Modeled estimate</p>
    <p data-testid="figures-note" data-figures="illustrative">Illustrative figures for the published five-layer scenario. The running app replaces them with engine results.</p>`;
}

function modeledReduction() {
  return `Modeled reduction ${formatReduction(reduction)}.`;
}

function confusion(rows) {
  const matrix = { tp: 0, fn: 0, fp: 0, tn: 0 };
  for (const row of rows) {
    if (row.actual === "phishing" && row.predicted === "phishing") matrix.tp += 1;
    else if (row.actual === "phishing") matrix.fn += 1;
    else if (row.predicted === "phishing") matrix.fp += 1;
    else matrix.tn += 1;
  }
  return matrix;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function comparisonSentence() {
  return comparisonNarrative(SHOWCASE.passRateUntrained, SHOWCASE.passRateTrained);
}
