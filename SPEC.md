# SPEC.md – Quote Brief Copilot

*Source of truth for the build. The "Summary" doc is the non-technical version; its Method and Cost sections must match this file.*

## Summary

A one-link BA case study: the business problem, requirements, a working prototype, and the method and cost behind it. The prototype turns a messy customer enquiry into a job card, a draft reply and a quote brief. A person approves every message and sets every price.

- **Audience:** the owner, sales reps and estimators of a family-owned business that quotes made-to-measure products.
- **Proves:** pain point → testable requirements → working prototype → transparent method (which model, what's AI vs code, how accuracy is checked) and real running cost.
- **Format:** one web page with three tabs (Problem · Prototype · Method & cost), and a GitHub repo whose README covers how the tool would be used, where the value is, and a discovery-to-integration plan.
- **Data:** the test enquiries are written by hand because no real data is available; they exist only to measure accuracy. The business is hypothetical. The demo shows one business (Wattlebird Kitchens & Joinery); 10 test enquiries, 2 of them out of scope.

## Scope

| In | Out |
|---|---|
| Enquiries by email, web form, call notes | Live inbox / CRM / quoting-system integration |
| Job card with evidence per field | Pricing, discounts, date promises |
| Missing-info check against a profile checklist | Sending anything |
| Draft reply + quote brief for approval | Real customer data |
| 3 configurable business profiles (the demo shows one) | Warranty, orders, production |
| Out-of-scope requests: flagged, polite decline drafted | Hosted live runs (custom enquiries run on a local server only) |
| Run log + accuracy test | Cost-savings projections |

## User stories

| ID | Story | Acceptance criteria |
|---|---|---|
| US1 | As a sales rep, I want each enquiry turned into a job card, so I don't re-type details. | Every stated field has a verbatim quote as evidence. Nothing absent from the enquiry is marked "stated". |
| US2 | As a sales rep, I want to see what's missing, so I ask once. | Missing list comes from the profile checklist. 100% of required fields checked. |
| US3 | As a sales rep, I want a draft reply asking only for missing info. | Asks for every missing field, no more. No price, discount or date promise. Sends only on Approve. |
| US4 | As an estimator, I want a one-screen quote brief. | Shows all fields, flags inferred/conflict ones, exports CSV/JSON. |
| US5 | As a manager, I want every run logged. | Logs time to draft, time to approve, % edited, approve/reject, flagged fields. |
| US6 | As a manager, I want to switch product types. | Changing the profile changes checklist and tone, no code change. |

## Job card

Each field: `value`, `status` (`stated` · `inferred` · `missing` · `conflict`), `evidence` (verbatim quote or null).

- **Always required:** customer_name, contact, suburb, product_type, timeframe
- **Per profile:** dimensions, material_or_finish, colour, quantity, install_required, site_access
- **Optional:** other_products (flagged if present), budget_mentioned, attachments_referenced, notes

## Models

| Job | Model | Price (USD per million input / output tokens) |
|---|---|---|
| Extract job card, draft reply | Claude Sonnet 5.5 | $2 / $10 |
| Classify message (enquiry · complaint · not an enquiry) | Claude Haiku 4.5 | $1 / $5 |

Both model names live in `src/config.py` only. No fine-tuning; tailoring comes from prompts and profile checklists.

## Pipeline

| Step | By | What |
|---|---|---|
| 1 Classify | LLM (Haiku 4.5) | enquiry · complaint · not_enquiry |
| 2 Extract | LLM (Sonnet 5.5) | Enquiry → job card JSON with evidence |
| 3 Validate | Code | Downgrade "stated" fields whose quote isn't in the enquiry |
| 4 Completeness | Code | Profile required fields → missing list. A product the profile doesn't sell → out of scope, nothing to ask |
| 5 Route | Code | complaint → route_to_person · not_enquiry → skip · else draft_reply |
| 6 Draft reply | LLM (Sonnet 5.5) | Ask only for missing / conflicting fields, profile tone. Out of scope → politely decline, ask nothing |
| 7 Screen | Code | Block $ amounts, discounts, dates/lead times |
| 8 Brief | Code | Estimator view + CSV/JSON |
| 9 Approve | Person | Approve / edit / reject, logged |

Classify runs first so complaints and non-enquiries never reach the more expensive extraction step.

## Evaluation pass bars

| Check | Bar |
|---|---|
| Field accuracy (stated fields) | ≥ 90% |
| Invented facts | 0 |
| Missing-info recall | 100% |
| Price guardrail breaches | 0 |
| Routing | All correct |
| In / out of scope | All correct |
| Reply length | < 120 words |

## Cost tracking

Every LLM call records model, input tokens, output tokens and cost. `run_all.py` prints total and per-enquiry cost in USD and AUD (exchange rate set in `src/config.py`). Target: 2–5 AU cents per enquiry.

## Tab 3 – Method & cost

Mirrors the Summary doc, filled with real numbers from the build:
- Data understanding: inputs, outputs, who defines "complete", what the business would provide.
- Which model does which job, and why.
- AI vs code table (the pipeline above).
- Eval results against the pass bars, failures included.
- Measured cost per enquiry from `runs.json`, and monthly cost at 100 enquiries a week.
