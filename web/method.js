// Tab 3: method and cost. Every number here is read from runs.json (src/run_all.py)
// or eval.json (src/eval.py). Nothing is typed by hand, so re-running those updates this tab.
// Layout rule: the headline first, detail behind "more" links, so the tab reads in a minute.
const CHANNEL = { email: "email", web_form: "web form", call_notes: "call notes" };
// Plain-English names for the eval checks; the measured values still come from eval.json.
const CHECK_NAME = {
  "Field accuracy (stated fields)": "Details read correctly",
  "Invented facts": "Made-up details",
  "Missing-info recall": "Missing info asked for",
  "Price guardrail breaches": "Prices or dates in drafts",
  "Routing": "Messages sent the right way",
  "In / out of scope": "Out-of-scope requests spotted",
  "Reply length": "Replies kept short",
};
const ROLE = { classify: "Sorts every message", extract_and_reply: "Reads enquiries and drafts replies" };

// "claude-sonnet-5-5" -> "Claude Sonnet 5.5": derived from the id in config.py, never typed.
const modelName = (id) => id.replace(/^claude-(\w+)-(\d+)-(\d+).*$/, (_, f, a, b) => `Claude ${f[0].toUpperCase()}${f.slice(1)} ${a}.${b}`);
const tally = (items) => items.reduce((m, k) => ({ ...m, [k]: (m[k] || 0) + 1 }), {});
const tile = (value, label) => `<div class="tile"><span class="value">${value}</span><span class="label">${label}</span></div>`;
const more = (summary, html) => `<details class="more"><summary>${summary}</summary>${html}</details>`;

function renderTiles(ev, data) {
  const passed = ev.bars.filter((b) => b.passed).length;
  const accuracy = ev.bars.find((b) => b.check.startsWith("Field accuracy")).measured.split(" ")[0];
  $("m-tiles").innerHTML = tile(`${passed}/${ev.bars.length}`, "quality checks passed")
    + tile(accuracy, "of details read correctly")
    + tile(`${(data.cost.avg_aud_drafted * 100).toFixed(2)}¢`, "per enquiry (AUD)")
    + tile(`A$${Math.ceil(data.cost.monthly_aud_100_per_week)}`, "a month at most, at 100 a week");
}

function renderEval(ev, data) {
  const checks = ev.bars.map((b) => `<li><span class="chip ${b.passed ? "ok" : "bad"}">${b.passed ? "pass" : "fail"}</span>
    <span>${CHECK_NAME[b.check] || esc(b.check)}</span><span class="measure">${esc(b.measured)}</span></li>`).join("");
  const rows = ev.enquiries.map((e) => {
    const ok = e.stated.filter(([, good]) => good).length;
    const problems = [...e.invented.map((n) => `made up ${nice(n)}`), ...e.missed_asks.map((n) => `didn't ask ${nice(n)}`),
      ...e.guardrail_hits.map((h) => `screen: ${h.text}`), ...(e.route_ok ? [] : ["wrong route"]), ...(e.scope_ok === false ? ["wrong scope"] : [])];
    return `<tr><td>${e.id}</td><td>${esc(data.enquiries[e.id]?.title ?? "")}</td>
      <td class="num">${e.stated.length ? `${ok}/${e.stated.length}` : "—"}</td>
      <td>${problems.length ? `<span class="chip bad">${problems.map(esc).join("; ")}</span>` : `<span class="chip ok">ok</span>`}</td></tr>`;
  }).join("");
  $("m-eval").innerHTML = `<p class="hint">Each test message was answered by hand first; code compares the copilot's answers to them.</p>
    <ul class="checks">${checks}</ul>
    ${more("Per message", `<div class="table-wrap"><table><tr><th>ID</th><th>Scenario</th><th class="num">Details right</th><th>Result</th></tr>${rows}</table></div>`)}
    ${more("What testing caught while building", `<ul>
      <li>Real customers were skipped when they asked for something the business doesn't sell. Product decisions moved into code.</li>
      <li>A new field broke out-of-scope detection. The scope check caught it before it shipped.</li>
      <li>Drafts repeated details and offered things nobody asked for. Fixed with a stricter reply structure.</li></ul>
      <p class="hint">Passing ${ev.enquiries.length} hand-written tests shows the bars can be met, not that it never fails. A pilot would re-run this on real enquiries.</p>`)}
    <p class="hint">Last run ${new Date(ev.run_at).toLocaleDateString("en-AU")}.</p>`;
}

function renderCost(data) {
  const c = data.cost;
  const total = Object.values(c.by_model).reduce((t, m) => t + m.cost_aud, 0);
  const split = Object.entries(data.models).map(([job, model]) => {
    const share = Math.round((100 * c.by_model[model].cost_aud) / total);
    return `<div class="split-row"><div class="split-label"><strong>${modelName(model)}</strong><span class="hint">${ROLE[job]}</span></div>
      <div class="bar"><span style="width:${share}%"></span></div><span class="measure">${share}%</span></div>`;
  }).join("");
  const others = c.per_enquiry.filter((e) => e.route !== "draft_reply");
  const cheap = others.reduce((t, e) => t + e.cost_aud, 0) / Math.max(others.length, 1);
  const rows = c.per_enquiry.map((e) => `<tr><td>${e.enquiry_id}</td><td>${esc(data.enquiries[e.enquiry_id].title)}</td>
    <td class="num">${e.seconds.toFixed(1)}s</td><td class="num">${(e.cost_aud * 100).toFixed(2)}¢</td></tr>`).join("");
  const prices = Object.values(data.models).map((m) => `${modelName(m)} US$${data.prices_usd_per_mtok[m].join(" / ")}`).join(", ");
  $("m-cost").innerHTML = `<p>Share of the bill by model:</p>${split}
    <p class="hint">Complaints and spam stop after the cheap model: about ${(cheap * 100).toFixed(2)}¢ each.</p>
    ${more("Per message and pricing", `<div class="table-wrap"><table><tr><th>ID</th><th>Scenario</th><th class="num">Time</th><th class="num">AUD</th></tr>${rows}</table></div>
      <p class="hint">Prices per million tokens in / out: ${prices}. AUD at a fixed ${data.aud_per_usd} per USD.
      The monthly figure is a ceiling: it prices every message as a full enquiry. Token counts come from the API's own usage figures, which the bill is based on.</p>`)}`;
}

function renderData(data) {
  const profile = data.profiles[Object.values(data.enquiries)[0].profile];
  const channels = Object.entries(tally(Object.values(data.enquiries).map((e) => e.channel)))
    .map(([k, n]) => `${n} ${CHANNEL[k] || k}`).join(", ");
  const checklist = Object.entries(profile.required_by_product).map(([product, fields]) =>
    `<tr><td>${esc(product)}</td><td>${[...profile.always_required, ...fields].map(nice).join(", ")}</td></tr>`).join("");
  $("m-data").innerHTML = `<ul class="facts">
      <li><strong>${data.runs.length} test messages</strong>, written by hand (${channels}). No real customer data.</li>
      <li><strong>${Object.keys(data.runs.find((r) => r.card).card).length} details</strong> per job card, each backed by words from the message.</li>
      <li><strong>The business decides</strong> what "complete" means, in a settings file. No code change needed.</li>
    </ul>
    ${more("The checklist, and what a real business would provide", `<div class="table-wrap"><table>
      <tr><th>Product</th><th>Needed before quoting</th></tr>${checklist}</table></div>
      <ul><li>Its products and the details each one needs</li><li>Its tone of voice and sign-off</li>
      <li>Past enquiries, anonymised, to re-run these tests on</li><li>Anything a reply must never say</li></ul>`)}`;
}

async function renderMethod(data) {
  renderCost(data);
  renderData(data);
  try {
    const ev = await (await fetch("eval.json")).json();
    renderTiles(ev, data);
    renderEval(ev, data);
  } catch {
    $("m-eval").innerHTML = `<p class="banner bad">Couldn't load eval.json. Run <code>python src/eval.py</code>.</p>`;
  }
}
