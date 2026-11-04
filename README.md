# NAME

**hospital-atlas**: a cited New York hospital cost and quality benchmarking agent over live CMS data.
Columbia IEOR E4570, Project 2 (Data Exploration Agent, deep-research path). Author: `ant2150`.

Deployed: https://hospital-atlas-git-622869374309.us-east1.run.app (Cloud Run, IAP: Columbia accounts only).

# PROJECT OBJECTIVE

Answer comparative questions about New York hospitals ("which hospitals charge Medicare the most for a knee replacement,
and are they any better?") with a short report in which **every number is computed by code from a CMS API response and
carries a citation** to the exact query that produced it. The agent plans, fans out parallel researchers, fills gaps in a
second round, and writes only from verified Facts. Anything it cannot support is stated in a "What the data can't tell you"
section instead of guessed.

# TARGET USER

A hospital-finance or health-policy analyst, a payer or employer benefits analyst, or an informed patient advocate who needs
a defensible, sourced comparison and not a ranking blog post. They can reproduce every figure by opening the URL next to it.

# WHY THIS IS DIFFERENT

- **Live, reproducible data.** Seven CMS datasets are queried at request time (cached 6 h, with a shipped fallback that is disclosed in the answer).
- **The model never does arithmetic or writes a number.** A deterministic Analyst turns tables into Facts (`display` strings, source ids). The Writer sees only Facts; a validator checks every `[S#]` exists and every number matches a Fact within 0.5%, repairs once, then strips what it cannot verify and reports an Audit line.
- **Real multi-agent work.** Cohort Retriever, then Cost and Quality Researchers in parallel, then a gap round (for example the sibling DRG), all visible as lanes in a live timeline.
- **Honest scope.** Medicare fee-for-service averages for New York only. Questions about out-of-pocket prices or other states get a short, correct refusal with the reason.
- **An evidence panel, not just a chat box.** Map (ZIP-centroid markers by cost/quality quadrant), sortable tables with CSV, charts, and a Sources tab wired to the `[S#]` citations.

# SAMPLE QUERIES

Expected answers come from `scripts/expected_answers.py`, which calls the CMS endpoints directly and shares no code with the agent (last run **2026-11-03**). Baselines are the same model with **no system prompt and no tools** (`evals/baseline.py` -> `evals/baselines.md`). Agent answers were captured by `evals/capture_answers.py` (`evals/agent_answers.md`; captured against a local run of the same code that Cloud Run deploys).

## Q1. Cost benchmark

> For major hip/knee replacement without complications (DRG 470), which five NY hospitals had the highest average total Medicare payment in 2024, and how do they compare with the NY and national averages?

| | Result |
|---|---|
| **Expected** (endpoints: `690ddc6c…` `Rndrng_Prvdr_State_Abrvtn=NY, DRG_Cd=470`; `2941ab09…` `DRG_Cd=470`) | 1 Montefiore 330059 $31,015 (186 discharges); 2 South Shore University 330043 $28,653 (102); 3 Brooklyn Hospital Center 330056 $27,728 (12, low volume); 4 Mount Sinai 330024 $27,622 (158); 5 Lenox Hill 330119 $26,238 (136). NY average $23,235, national $17,364; 56 NY hospitals have data. |
| **No tools** | Declines to give 2024 figures, then lists HSS, NewYork-Presbyterian, NYU, Mount Sinai and North Shore from memory. Its "typical" ranges ($11.5-13.5K national, $14.5-17K NY, $18-22K top hospitals) are all below the real values. Montefiore, the real #1, is missing. |
| **hospital-atlas** | Same five hospitals, same dollar figures, +33.5% / +23.3% / +19.3% / +18.9% / +12.9% vs the NY average, flags Brooklyn Hospital Center as a 12-discharge sample, cites S4 and S5. Audit clean. 12.7 s. |

## Q2. Cost versus quality (shows the gap round and the parallel researchers)

> How does Montefiore compare with other Bronx hospitals on heart failure — Medicare payment, 30-day readmissions and mortality?

| | Result |
|---|---|
| **Expected** (DRG 291; `xubh-q36u` Bronx; `9n3s-kdb3` `READM-30-HF-HRRP`; `ynj2-r877` `MORT_30_HF`; `qqw3-t4ie`) | BronxCare $23,266 (54), ERR 1.1867, mortality 8.3; **Montefiore $24,163 (390), ERR 0.9349, mortality 5.2**; St Barnabas $27,390 (27), 1.0618, 11.1 (n=28, small); Jacobi $29,655 (89), 1.0321, 7.4; Lincoln $31,893 (39), 0.9848, 8.5. National HF mortality 11.1. NY DRG 291 average $16,034, national $12,053. NY has no DRG 293 (sibling is 292). |
| **No tools** | Prose only: readmissions "around 21-23%", mortality "no different than national", payments "higher than average". Every statement is generic or wrong in direction (Montefiore's payment is above the NY average, but its readmission ratio is better than expected and its mortality 5.2 vs 11.1 nationally). No hospital-level numbers. |
| **hospital-atlas** | Montefiore $24,163 (4th of 5 by payment, +50.7% vs NY average), ERR 0.935 "better than expected", mortality 5.2% (-5.9 pp vs national); ranking table of all five Bronx hospitals with the correct payments; quadrant: lower cost / better quality. Audit clean. 10.7 s. |

## Q3. Vague question, clarification, then a real answer

> Turn 1: "Which NY hospitals are the best?"  Turn 2: "Hip and knee replacement in New York City, both cost and quality."

| | Result |
|---|---|
| **Expected** (`xubh-q36u` NYC counties; DRG 469/470; `ynj2-r877` `COMP_HIP_KNEE`; `9n3s-kdb3` hip/knee) | Turn 1: ask one question with options (condition, region, cost or quality). Turn 2: 33 acute-care NYC hospitals; DRG 470 ranked by payment: Montefiore $31,015 (COMP 2.8, ERR 0.9730), Brooklyn Hospital Center $27,728, Mount Sinai $27,622, Lenox Hill $26,238, HSS $25,507 (1,332 discharges)…; national COMP_HIP_KNEE 4.1. |
| **No tools** | Never asks anything; answers immediately with a U.S. News-style list of famous hospitals and no cost figures. |
| **hospital-atlas** | Turn 1 returns one clarifying question with four options (1.2 s). Turn 2 builds a 12-hospital DRG 470 and 4-hospital DRG 469 ranking with the exact values above, readmission ratios, and small-sample flags. 11.5 s. |

## More to try (including questions the data cannot answer)

- "What will I pay out of pocket for a knee replacement at NYU?" -> the agent gives NYU's Medicare average ($38,267 for DRG 469, $25,403 for DRG 470) and states plainly that out-of-pocket and commercial prices are not in the data.
- "Cheapest knee replacement in Boston?" -> a short refusal: the data covers New York only.
- "Compare Mount Sinai and NYU on pneumonia." / "Which Long Island hospitals have the best heart failure readmission ratios?" / "Is the Bronx VA expensive?" (no fee-for-service data exists for VA hospitals).

# ARCHITECTURE

```
 browser (web/index.html)  --POST /chat {message, run_id, model, effort}-->  FastAPI (app.py)
        ^  GET /progress?run_id= every 1 s (live timeline)                         |
        |                                                                          v
        |                                                          orchestrator.answer()
        |                                                           Lead agent (Gemini, tools)
        |            ask_clarifying_question <-+                      |  resolve_cohort
        |                                      |                      v
        |                          Cohort Retriever --> CohortSpec  (find_hospitals, find_services, build_cohort)
        |                                                           |
        |                dispatch_researchers (round 1: 3-4 tasks, asyncio.gather)
        |                   Cost Researcher R1 | Quality Researcher R2 | Quality Researcher R3
        |                   (get_drg_costs, get_cost_benchmarks, get_readmissions, get_outcomes, get_patient_experience)
        |                                                           |  tables + sources stored in RequestContext
        |                                                           v
        |                  Analyst (deterministic Python): Facts, Gaps, T_rank, T_quadrant
        |                        fillable gap? -> round 2 (max 2 gap rounds) -> Analyst again
        |                                                           v
        |                  write_report -> Writer (Facts only) -> validator (citations, numbers, repair once) -> renderer
        |                                                           v
        +-- {response, session_id, tool_calls, artifacts, meta} <---+  (artifacts: cohort + coordinates, tables, charts, sources)
```

Mapping to the assignment's deep-research checklist:

| Requirement | Where |
|---|---|
| Tools over real data | `atlas/tools.py` (10 tools over `atlas/cms.py`), live CMS APIs |
| Multi-agent | Lead, Cohort Retriever, Cost/Quality Researchers, Writer (OpenAI Agents SDK, `atlas/agents.py`, `atlas/orchestrator.py`) |
| Parallel work and a second round | `dispatch_researchers` (`asyncio.gather`); gap rounds only for fillable gaps such as the sibling DRG |
| Planning and clarification | Lead prompt; `ask_clarifying_question` (never asks twice) |
| Citations and verification | `atlas/sources.py`, `atlas/validate.py`; Audit line; Sources section with reproducible URLs |
| Time budget and failure handling | 240 s request budget, per-agent timeouts, `render_partial` safety net, `ATLAS_FAULT=timeout\|error` fault injection |
| Deployment | Cloud Run from GitHub `main` (continuous deploy), IAP restricted to columbia.edu |

Models (selectable in the UI, through Vertex AI and LiteLLM): Gemini 3.5 Flash-Lite (default, about 20 s per question), Gemini 3.5 Flash and Gemini 3.1 Pro preview (both much slower, 2 minutes or more). Claude, Grok and OpenAI gpt-oss were tried and are not usable on this project (no Anthropic quota, xAI not enabled, gpt-oss does not drive the tool loop reliably). Effort: Fast / Balanced / Thinking (measured on Q1 and Q2 with Flash-Lite: about 21 s / 26 s / 40 s, with occasional slow Vertex calls). Balanced gives the Lead medium reasoning. Thinking adds a **Critic**: an LLM reads the analysed facts against the question, unanswered parts are stated in the report, and valid extra lookups (checked against the real measure list) run as one more round. Thinking also allows 2 gap rounds. Researchers and the Writer always run at low reasoning to protect latency.

# DATA SOURCES

All from CMS (data.cms.gov), filtered to New York (`state=NY`). Each request records a Source with dataset, period, retrieval time and the reproducible URL.

| Dataset | ID | Used for | Example |
|---|---|---|---|
| Medicare Inpatient Hospitals by Provider and Service (CY2024) | `690ddc6c-2767-4618-b277-420ffb2bf27c` | payment, discharges per hospital and DRG | `curl 'https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470'` |
| Medicare Inpatient Hospitals by Geography and Service | `2941ab09-8cee-49d8-9703-f3c5b854e388` | NY and national benchmarks | `curl 'https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=470'` |
| Hospital General Information | `xubh-q36u` | hospital list, county, type | provider-data API |
| Hospital Readmissions Reduction Program | `9n3s-kdb3` | excess readmission ratios | provider-data API |
| Complications and Deaths, Hospital | `ynj2-r877` | mortality, hip/knee complications, PSIs | provider-data API |
| Complications and Deaths, National | `qqw3-t4ie` | national rates | provider-data API |
| HCAHPS Patient Survey | `dgck-syfz` | star ratings | provider-data API |

Provider-data pattern: `https://data.cms.gov/provider-data/api/1/datastore/query/<id>/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&limit=1500`.

**Why live-first plus a shipped `data/`:** a grader's answer must reflect what CMS publishes, so slices are fetched at request time (cached 6 h, single-flight, stale-while-error). If CMS is unreachable the agent falls back to `data/fallback/*.json.gz` (built by `scripts/build_fallback.py`) and the answer says it is serving stored data. `data/` also holds small hand-curated reference files: condition-to-DRG/measure crosswalk, measure metadata, regions, and NY ZIP centroids (`scripts/build_zip_centroids.py`, Census gazetteer) for map positions.

# TESTS AND EVALS

```bash
uv run pytest -m "not network"       # ~110 offline tests: adapters, tools, dispatch, analyst, validator, renderer, API, UI static checks
uv run pytest -m network             # live CMS paging checks
uv run python evals/run_evals.py     # E1-E8 end-to-end cases against a local run (add --url/--token for the deployed app)
uv run python scripts/expected_answers.py   # recompute the README's expected answers from CMS
uv run python evals/baseline.py      # regenerate the no-tools baselines
uv run python -m evals.capture_answers      # capture agent answers for Q1-Q3
```

CI (`.github/workflows/tests.yml`) runs the offline suite on every pull request. Every phase was merged through a pull request with that check.

# LIMITATIONS

- Medicare fee-for-service averages only; no commercial or cash prices and no out-of-pocket estimates. Charges are list prices, not payments.
- New York only; VA, psychiatric and children's hospitals have no comparable payment data.
- CMS suppresses hospital-DRG rows with fewer than 11 discharges; small samples are flagged, not hidden.
- Cost is calendar 2024 while quality measures cover different periods, so cost-versus-quality quadrants are directional.
- Mortality and complication scores are compared with the national rate by direction only (the CMS dataset publishes no confidence interval for the mortality measures).
- Known weaknesses: for "compared with other hospitals" questions the Retriever can build a narrow cohort, and in Q2 the cost-versus-quality table lists only the hospital asked about although the cost ranking covers all five Bronx hospitals. Ratio and quadrant thresholds are heuristics documented in `atlas/analyst.py`.
- One Cloud Run instance, two concurrent research runs, in-memory sessions (a restart loses server-side history; the browser keeps saved chats and re-seeds them).

# PROJECT STRUCTURE

```
app.py                 FastAPI: /chat, /models, /progress, /health, /clear, static UI
atlas/                 config, http (cache, retries, fallback), cms (typed adapters), crosswalk, sources, store, context,
                       tools, agents, orchestrator, analyst, validate, render, progress, schemas
data/                  crosswalk, measures, regions, ZIP centroids, fallback/*.json.gz
web/index.html         single-page UI (chat, timeline, map, tables, charts, sources)
evals/                 cases.jsonl, run_evals.py, baseline.py (+ baselines.md), capture_answers.py (+ agent_answers.md)
scripts/               expected_answers.py, build_fallback.py, build_zip_centroids.py, smoke scripts
tests/                 offline and network tests
submission.json        deploy_url, authors, path
```

# SETUP / DEPLOY

```bash
gcloud auth application-default login        # Vertex AI access for Gemini
uv sync
uv run uvicorn app:app --port 8080           # open http://localhost:8080
```

Environment: `ATLAS_MODEL` overrides the default model; `ATLAS_FAULT=timeout|error` injects a fault for testing the safety net.

Deploy: Cloud Run service `hospital-atlas-git` (us-east1) builds from this GitHub repository's `main` branch (Python 3.13, `.python-version`), request timeout 600 s, concurrency 8, 1 GiB, max instances 1, IAP limited to columbia.edu. The runtime service account needs `roles/aiplatform.user`.

# UI

Left: saved research with search, rename, delete and undo. Centre: the conversation with a live research timeline (one lane per agent, parallel researchers side by side, a round divider for gap fills, expandable tool calls) and citation superscripts that jump to the Sources tab. Right: Map (marker size = discharges, colour and shape = quadrant, ringed = hospital you asked about, popups with an "Ask about this hospital" button), Tables (sortable, CSV), Charts (payment by hospital with NY and national reference lines; cost versus quality) and Sources. Light and dark themes, model and effort pickers, phone layout.
