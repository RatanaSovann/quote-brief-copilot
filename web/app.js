// Tab 2 wiring: pick an example (saved runs from runs.json, made by src/run_all.py)
// or write your own (a live run from the local server, src/serve.py), then show it.
const state = { data: null, run: null, field: null, openedAt: 0, example: null, custom: null };

// Starting points for "Write your own". Contacts use ACMA's fictional number range.
const PRESETS = {
  "Complete kitchen": { Name: "Jo Bennett", Contact: "0491 570 162", Suburb: "Glenroy", Product: "Kitchen",
    Message: "New kitchen for a room about 3.6 x 2.8m. Two-pac doors in Dove Grey with a stone benchtop. Supply and install please. Hoping to start in March." },
  "Vague, wants a price": { Name: "Sam", Contact: "", Suburb: "", Product: "Vanity", Message: "how much for a vanity??" },
  "Something we don't sell": { Name: "Alex Chen", Contact: "alex.chen@example.com", Suburb: "Coburg North", Product: "Other",
    Message: "Could you build us a timber deck out the back? About 5 x 4 metres." },
  "Unhappy customer": { Name: "Chris Lam", Contact: "0491 570 163", Suburb: "", Product: "",
    Message: "Third time asking. Where is my quote?! This is unacceptable." },
};

const enquiryText = (run) => run.text ?? state.data.enquiries[run.enquiry_id].text;

function display(run) {
  state.run = run;
  state.field = null;
  state.openedAt = Date.now();
  renderSteps(run);
  renderMessage(run, enquiryText(run), null);
  renderReply(run, state.openedAt);
  renderCard(run, null);
  renderBrief(run);
}

function selectField(name) {
  state.field = state.field === name ? null : name;
  renderMessage(state.run, enquiryText(state.run), state.field);
  renderCard(state.run, state.field);
}

function renderExamples() {
  $("mode-examples").innerHTML = state.data.runs.map((run) => {
    const [tone, words] = outcome(run);
    const pressed = state.example === run.enquiry_id;
    return `<button class="example" data-example="${run.enquiry_id}" aria-pressed="${pressed}">
      <span class="id">${run.enquiry_id}</span>
      <span class="title">${esc(state.data.enquiries[run.enquiry_id].title)}</span>
      <span class="chip ${tone}">${words}</span></button>`;
  }).join("");
}

function pickExample(id) {
  state.example = id;
  renderExamples();
  display(state.data.runs.find((r) => r.enquiry_id === id));
}

function setMode(mode) {
  for (const b of document.querySelectorAll("[data-mode]")) b.setAttribute("aria-selected", b.dataset.mode === mode);
  $("mode-examples").hidden = mode !== "examples";
  $("mode-custom").hidden = mode !== "custom";
  if (mode === "examples") display(state.data.runs.find((r) => r.enquiry_id === state.example));
  else if (state.custom) display(state.custom);
}

// The form becomes a web-form style enquiry, like E2 and E6. Blank fields are left out,
// so they're genuinely missing for the pipeline rather than filled with "N/A".
function composeEnquiry(form) {
  const v = (name) => form.elements[name].value.trim();
  const contact = v("Contact");
  const lines = [
    v("Name") && `Name: ${v("Name")}`,
    contact && `${contact.includes("@") ? "Email" : "Phone"}: ${contact}`,
    v("Suburb") && `Suburb: ${v("Suburb")}`,
    v("Product") && `Product: ${v("Product")}`,
    v("Message") && `Message: ${v("Message")}`,
  ];
  return lines.filter(Boolean).join("\n");
}

async function runCustom(event) {
  event.preventDefault();
  const text = composeEnquiry($("mode-custom"));
  if (!$("mode-custom").elements.Message.value.trim()) { $("custom-status").textContent = "Write a message first."; return; }
  $("custom-run").disabled = true;
  $("custom-status").textContent = "Running: classify, extract, check, draft… about 10 seconds.";
  try {
    const res = await fetch("api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    // A static host has no /api/run: it answers 404, 405 or 501 instead.
    if ([404, 405, 501].includes(res.status)) throw new Error("Live runs need the local server: python src/serve.py");
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || `Server said ${res.status}`);
    state.custom = body;
    display(body);
    $("custom-status").textContent = `Done in ${body.seconds}s for ${cents(body.cost_aud)}. Results below.`;
  } catch (e) {
    $("custom-status").textContent = e.message;
  } finally {
    $("custom-run").disabled = false;
  }
}

function setupPresets() {
  const box = document.querySelector(".presets");
  for (const [name, values] of Object.entries(PRESETS)) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = name;
    b.onclick = () => { for (const [k, val] of Object.entries(values)) $("mode-custom").elements[k].value = val; };
    box.append(b);
  }
}

function setupTabs() {
  for (const tab of document.querySelectorAll("[role=tab][data-tab]")) {
    tab.onclick = () => {
      for (const t of document.querySelectorAll("[role=tab][data-tab]")) {
        t.setAttribute("aria-selected", t === tab);
        $(`tab-${t.dataset.tab}`).hidden = t !== tab;
      }
    };
  }
}

async function init() {
  setupTabs();
  try {
    state.data = await (await fetch("runs.json")).json();
  } catch {
    $("load-error").hidden = false;
    $("load-error").textContent = "Couldn't load runs.json. Start the local server (python src/serve.py) rather than opening the file directly.";
    return;
  }
  const { enquiries, profiles, runs } = state.data;
  const business = profiles[Object.values(enquiries)[0].profile];
  $("business").textContent = business.business_name;
  $("products").textContent = business.product_types.join(", ");

  renderMethod(state.data);
  setupPresets();
  $("mode-custom").onsubmit = runCustom;
  for (const b of document.querySelectorAll("[data-mode]")) b.onclick = () => setMode(b.dataset.mode);
  // One delegated listener: example cards, job card fields and highlighted quotes.
  document.addEventListener("click", (e) => {
    const ex = e.target.closest("[data-example]");
    if (ex) return pickExample(ex.dataset.example);
    const field = e.target.closest("[data-field]");
    if (field) selectField(field.dataset.field);
  });
  pickExample(runs[0].enquiry_id);
  renderLog();
}

init();
