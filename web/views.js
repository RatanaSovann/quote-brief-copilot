// Draws one run: the pipeline strip, the message, the job card and the quote brief.
// Pure display: every value shown comes from a measured run (runs.json or the local server).
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const show = (v) => (v === null || v === undefined ? "—" : v === true ? "yes" : v === false ? "no" : String(v));
const nice = (name) => name.replaceAll("_", " ");
const cents = (aud) => `${(aud * 100).toFixed(2)} AU cents`;
const TONE = { stated: "ok", inferred: "warn", missing: "bad", conflict: "bad" };

// Fields the estimator cares about: everything present, plus required fields that are absent.
// Optional and absent (e.g. no budget mentioned) is noise, same rule as brief.as_text().
const visibleFields = (brief) => brief.fields.filter((f) => f.status !== "missing" || f.required);

// One label for the example cards: what the pipeline ended up doing.
function outcome(run) {
  if (run.route === "skip") return ["muted", "Skipped"];
  if (run.route === "route_to_person") return ["bad", "To a person"];
  if (run.gaps.out_of_scope) return ["warn", "Out of scope"];
  return ["ok", "Draft reply"];
}

// The 8 pipeline steps for this run. decision is set once a person approves or rejects.
function stepsFor(run, decision) {
  const call = (step) => run.calls.find((c) => c.step === step);
  const s = (name, by, state, detail, c) => ({ name, by, state, detail, call: c });
  const label = { enquiry: "Enquiry", complaint: "Complaint", not_enquiry: "Not an enquiry" }[run.classification.label];
  const steps = [s("Classify", "ai", "done", label, call("classify"))];
  if (run.route !== "draft_reply") {
    steps.push(s("Route", "code", "stop", run.route === "skip" ? "Skip it" : "Hand to a person"));
    for (const [name, by] of [["Extract", "ai"], ["Check quotes", "code"], ["What's missing", "code"], ["Draft", "ai"], ["Screen", "code"]]) {
      steps.push(s(name, by, "skipped", "Not run"));
    }
    steps.push(s("Decide", "person", run.route === "skip" ? "skipped" : "waiting", run.route === "skip" ? "Nothing to do" : "A person replies"));
    return steps;
  }
  const count = (st) => run.brief.fields.filter((f) => f.status === st).length;
  const fixes = run.evidence_changes.length;
  const asks = run.gaps.missing.length + run.gaps.conflicts.length;
  const r = run.reply;
  steps.push(
    s("Route", "code", "done", "Draft a reply"),
    s("Extract", "ai", "done", [`${count("stated")} stated`, count("inferred") && `${count("inferred")} guessed`,
      count("conflict") && `${count("conflict")} conflict`].filter(Boolean).join(" · "), call("extract")),
    s("Check quotes", "code", fixes ? "flag" : "done", fixes ? `${fixes} quote${fixes > 1 ? "s" : ""} not found, downgraded` : "Every quote found in the message"),
    s("What's missing", "code", run.gaps.out_of_scope ? "flag" : "done",
      run.gaps.out_of_scope ? "Out of scope" : asks ? `Ask about ${asks}` : "Nothing missing"),
    s("Draft", "ai", "done", run.gaps.out_of_scope ? "Polite decline" : `${r.body.split(/\s+/).length}-word reply`, call("reply")),
    s("Screen", "code", r.blocked ? "stop" : "done", r.blocked ? "Blocked: price or date" : "No price or date"),
    s("Decide", "person", decision === "approved" ? "done" : decision === "rejected" ? "stop" : "waiting",
      decision ? `${decision[0].toUpperCase()}${decision.slice(1)}` : "Your turn, below"),
  );
  return steps;
}

function renderSteps(run, decision) {
  $("steps").innerHTML = stepsFor(run, decision).map((st) => `<li class="${st.state}">
      <span class="by ${st.by}">${st.by === "ai" ? "AI" : st.by}</span>
      <span class="name">${st.name}</span>
      <span class="detail">${esc(st.detail)}</span>
      ${st.call ? `<span class="cost">${st.call.seconds}s · ${cents(st.call.cost_aud)}</span>` : ""}
    </li>`).join("");
  $("run-summary").textContent = `${run.text ? "Live run" : "Saved run"}: ${run.seconds}s and ${cents(run.cost_aud)}, measured. `
    + "AI steps read and write; code steps check; only a person can approve.";
}

function messageHtml(text, fields, selected) {
  // Underline every evidence quote; the selected field's quote is highlighted.
  // Quotes are verbatim (evidence.py enforces it), so a plain indexOf finds them.
  const order = [...fields].sort((a, b) => (b.field === selected) - (a.field === selected));
  const spans = [];
  const free = (at, end) => !spans.some((s) => at < s.end && end > s.at);
  for (const f of order) {
    const at = f.evidence ? text.indexOf(f.evidence) : -1;
    const end = at + (f.evidence || "").length;
    if (at >= 0 && free(at, end)) spans.push({ at, end, field: f.field });
  }
  // Form labels at the start of a line ("Name:", "Subject:") are dimmed so the customer's words stand out.
  // Evidence wins where they overlap (e.g. "Quantity: 2" is itself a quote).
  for (const m of text.matchAll(/^[A-Z][A-Za-z ]{0,20}:/gm)) {
    if (free(m.index, m.index + m[0].length)) spans.push({ at: m.index, end: m.index + m[0].length, key: true });
  }
  spans.sort((a, b) => a.at - b.at);
  let html = "", pos = 0;
  for (const s of spans) {
    const inner = esc(text.slice(s.at, s.end));
    html += esc(text.slice(pos, s.at)) + (s.key ? `<span class="key">${inner}</span>`
      : `<mark data-field="${s.field}"${s.field === selected ? ' class="active"' : ""}>${inner}</mark>`);
    pos = s.end;
  }
  return html + esc(text.slice(pos));
}

function renderMessage(run, text, selected) {
  $("message").innerHTML = messageHtml(text.trim(), run.brief ? run.brief.fields : [], selected);
}

function asksHtml(run) {
  const g = run.gaps;
  if (g.out_of_scope) return `<div class="asks"><span class="chip warn">out of scope</span> Not something this business sells, so nothing is asked. The reply declines politely.</div>`;
  const ask = [...g.missing.map(nice), ...g.conflicts.map((n) => `${nice(n)} (details disagree)`)];
  return `<div class="asks">${ask.length
    ? `<strong>The reply asks for:</strong><ul>${ask.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>`
    : "<strong>Nothing missing.</strong> Every required field for this product is here."}
    <p class="hint">Checklist comes from the business profile, not the AI.</p></div>`;
}

function renderCard(run, selected) {
  if (!run.brief) { $("card").innerHTML = `<p class="empty">No job card: extraction never ran, so the expensive model wasn't paid for.</p>`; return; }
  $("card").innerHTML = asksHtml(run) + visibleFields(run.brief).map((f) => {
    const open = f.field === selected;
    const evidence = f.evidence ? `“${esc(f.evidence)}”` : "No quote: nothing in the message supports a value.";
    return `<button class="field${open ? " selected" : ""}" data-field="${f.field}" data-status="${f.status}" aria-expanded="${open}">
      <span class="fname">${nice(f.field)}${f.required || run.gaps.out_of_scope ? "" : " (optional)"}</span>
      <span>${esc(show(f.value))}</span>
      <span class="chip ${TONE[f.status]}">${f.status}</span>
      ${open ? `<span class="evidence">From the message: ${evidence}</span>` : ""}
    </button>`;
  }).join("") + `<p class="legend"><span><span class="chip ok">stated</span> quoted</span><span><span class="chip warn">inferred</span> a guess, flagged</span><span><span class="chip bad">missing</span> <span class="chip bad">conflict</span> asked about</span></p>`;
}

function renderBrief(run) {
  const b = run.brief;
  if (!b) { $("brief").innerHTML = `<p class="empty">No brief: nothing to quote.</p>`; return; }
  const rows = visibleFields(b).map((f) =>
    `<tr><td>${nice(f.field)}</td><td>${esc(show(f.value))}</td><td><span class="chip ${TONE[f.status]}">${f.status}</span></td></tr>`).join("");
  $("brief").innerHTML = `<p><strong>Product:</strong> ${esc(b.product || "not one of ours")}
    · <strong>Flags:</strong> ${b.flags.length ? b.flags.map(esc).join("; ") : "none"}</p>
    <div class="table-wrap"><table><tr><th>Field</th><th>Value</th><th>Status</th></tr>${rows}</table></div>
    <div class="actions"><button id="export-csv">Export CSV</button><button id="export-json">Export JSON</button>
    <span class="hint">No price here. The estimator sets it.</span></div>`;
  $("export-csv").onclick = () => download(`${b.enquiry_id}_brief.csv`, briefCsv(b), "text/csv");
  $("export-json").onclick = () => download(`${b.enquiry_id}_brief.json`, JSON.stringify(b, null, 2), "application/json");
}

// Same columns as brief.to_csv() in Python, so both exports open the same way in Excel.
function briefCsv(b) {
  const cell = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const head = ["field", "value", "status", "evidence", "required"];
  return [head.join(","), ...b.fields.map((f) => head.map((k) => cell(f[k])).join(","))].join("\r\n");
}

function download(name, content, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([content], { type }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}
