// The approve step (pipeline step 8) and the run log (US5). Always a person; nothing is ever sent.
// The log lives in this browser's localStorage only: it shows what would be logged, it isn't a database.
const LOG_KEY = "qbc-runlog";

function readLog() {
  try { return JSON.parse(localStorage.getItem(LOG_KEY)) || []; } catch { return []; }
}
function writeLog(entries) {
  try { localStorage.setItem(LOG_KEY, JSON.stringify(entries)); } catch { /* storage blocked: log just won't persist */ }
}

// % edited = word-level edit distance / longer draft. Words, not characters,
// so fixing one typo doesn't look like the same effort as rewriting a sentence.
function percentEdited(before, after) {
  const a = before.split(/\s+/).filter(Boolean), b = after.split(/\s+/).filter(Boolean);
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const row = [i];
    for (let j = 1; j <= b.length; j++) {
      row[j] = Math.min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = row;
  }
  return Math.round((100 * prev[b.length]) / Math.max(a.length, b.length, 1));
}

function renderReply(run, openedAt) {
  const r = run.reply;
  if (!r) {
    $("reply").innerHTML = `<p class="empty">${run.route === "route_to_person"
      ? "No draft, on purpose: an upset customer needs a person, not a template."
      : "No draft: this isn't a customer enquiry."}</p>`;
    return;
  }
  let banner;
  if (r.blocked) banner = `<p class="banner bad"><strong>Blocked, do not send.</strong> The screen found ${r.hits.map((h) => `${h.rule} “${esc(h.text)}”`).join(", ")}. Edit it before approving.</p>`;
  else if (r.warnings?.length) banner = `<p class="banner warn"><strong>Check before sending.</strong> ${r.warnings.map(esc).join(" ")}</p>`;
  else banner = `<p class="banner ok">Passed the price and date screen. Read it, then decide.</p>`;

  $("reply").innerHTML = `${banner}
    <textarea id="draft" class="draft" readonly aria-label="Draft reply to the customer">${esc(r.text)}</textarea>
    <div class="actions">
      <button id="approve" class="primary"${r.blocked ? " disabled" : ""}>Approve</button>
      <button id="edit">Edit</button>
      <button id="reject">Reject</button>
      <span id="decision" class="hint" aria-live="polite"></span>
    </div>`;

  const draft = $("draft");
  $("edit").onclick = () => { draft.readOnly = false; draft.focus(); };
  // A blocked draft can only be approved once a person has changed it.
  draft.oninput = () => { if (r.blocked) $("approve").disabled = draft.value === r.text; };
  $("approve").onclick = () => decide(run, "approved", draft.value, openedAt);
  $("reject").onclick = () => decide(run, "rejected", draft.value, openedAt);
}

function decide(run, decision, finalText, openedAt) {
  const entries = readLog();
  entries.unshift({
    at: new Date().toLocaleString("en-AU"),
    enquiry: run.text ? "Your own" : run.enquiry_id,
    decision,
    secondsToDraft: run.seconds,
    secondsToDecide: Math.round((Date.now() - openedAt) / 1000),
    edited: percentEdited(run.reply.text, finalText),
    flagged: [...run.brief.flags, ...run.reply.hits.map((h) => `guardrail: ${h.text}`)],
  });
  writeLog(entries);
  for (const id of ["approve", "edit", "reject"]) $(id).disabled = true;
  $("draft").readOnly = true;
  $("decision").textContent = decision === "approved"
    ? "Approved and logged. Not sent: this prototype never sends."
    : "Rejected and logged. A person writes this one instead.";
  renderSteps(run, decision);
  renderLog();
}

function renderLog() {
  const entries = readLog();
  $("runlog-count").textContent = entries.length ? `${entries.length} decision${entries.length > 1 ? "s" : ""}` : "";
  if (!entries.length) {
    $("runlog").innerHTML = `<p class="empty">No decisions yet. Approve or reject a draft above.</p>`;
    return;
  }
  const rows = entries.map((e) => `<tr><td>${esc(e.at)}</td><td>${esc(e.enquiry)}</td>
    <td><span class="chip ${e.decision === "approved" ? "ok" : "bad"}">${e.decision}</span></td>
    <td class="num">${e.secondsToDraft}s</td><td class="num">${e.secondsToDecide}s</td><td class="num">${e.edited}%</td>
    <td>${e.flagged.length ? e.flagged.map(esc).join("; ") : "—"}</td></tr>`).join("");
  $("runlog").innerHTML = `<div class="table-wrap"><table>
    <tr><th>When</th><th>Enquiry</th><th>Decision</th><th class="num">Time to draft</th>
    <th class="num">Time to decide</th><th class="num">Edited</th><th>Flagged</th></tr>${rows}</table></div>
    <div class="actions"><button id="clear-log">Clear log</button></div>`;
  $("clear-log").onclick = () => { writeLog([]); renderLog(); };
}
