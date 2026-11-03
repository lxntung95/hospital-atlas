"""Agent definitions for the researchers. Each tool-using agent ends on a terminal submit_* tool (StopAtTools),
with tool_choice required, so a small model cannot wander off into free text."""

from dataclasses import replace

from agents import Agent, AgentOutputSchema
from agents.agent import StopAtTools

from atlas.config import MODEL, SETTINGS
from atlas.schemas import Claim, CohortSpec, Finding, Gap, Report, ResearchTask  # re-exported for callers
from atlas.tools import COST_TOOLS, QUALITY_TOOLS, RETRIEVER_TOOLS

__all__ = ["Claim", "Report", "WRITER", "CohortSpec", "Finding", "Gap", "ResearchTask", "COHORT_RETRIEVER", "COST_RESEARCHER", "QUALITY_RESEARCHER", "MAX_TURNS"]

TOOL_SETTINGS = replace(SETTINGS, tool_choice="required")  # every turn must be a tool call
MAX_TURNS = {"retriever": 6, "cost": 6, "quality": 6}

RULES = """Rules:
- Use only your tools. Never invent hospital names, CCNs, DRG codes, measure ids or numbers.
- Only New York hospitals exist in your data. If something is not found, say so in your submission; do not guess.
- Your tools return a table handle (T#) and source ids (S#). Cite only handles and ids your tools returned.
- Finish by calling the submit tool exactly once. Do not write a final answer in free text."""

COHORT_RETRIEVER = Agent(
    name="Cohort Retriever",
    instructions=f"""You turn a user request into a cohort of New York hospitals plus the DRG codes and measure ids to study.
Steps:
1. For every hospital the user names, call find_hospitals. Keep the CCNs it returns.
2. If a condition or procedure is mentioned, call find_services to get DRG codes and measure ids.
3. Call build_cohort: pass the named hospitals' CCNs plus the counties the user asked about (for example "other Bronx hospitals" means ccns of the named hospital and counties ["Bronx"]). Use statewide=true when the user asks about New York as a whole.
4. Call submit_cohort with the handle, focus_ccns (the hospitals the user named), the drg_codes and measure_ids, a short region_label, and unresolved (names you could not match, with the reason, for example "Mass General: outside NY scope").
{RULES}""",
    model=MODEL, model_settings=TOOL_SETTINGS, tools=RETRIEVER_TOOLS,
    tool_use_behavior=StopAtTools(stop_at_tool_names=["submit_cohort"]), reset_tool_choice=False,
)

COST_RESEARCHER = Agent(
    name="Cost Researcher",
    instructions=f"""You research what Medicare pays New York hospitals for specific DRGs (CY2024). Your input is a JSON research task.
Steps:
1. Call get_drg_costs with the task's cohort_handle and drg_codes.
2. Call get_cost_benchmarks with the same drg_codes so results can be compared with the New York and national averages.
3. Call submit_finding with the task id, a 2-4 sentence summary that uses only numbers your tools returned, the table handles and source ids, and gaps (for example hospitals missing from the data).
{RULES}""",
    model=MODEL, model_settings=TOOL_SETTINGS, tools=COST_TOOLS,
    tool_use_behavior=StopAtTools(stop_at_tool_names=["submit_finding"]), reset_tool_choice=False,
)

QUALITY_RESEARCHER = Agent(
    name="Quality Researcher",
    instructions=f"""You research hospital quality for New York hospitals. Your input is a JSON research task whose measure_ids say what to look at.
Steps:
1. If measure_ids include ids starting with READM-30- call get_readmissions with those ids. A ratio above 1.0 means more readmissions than expected.
2. If measure_ids include MORT_30_*, COMP_*, Hybrid_HWM or PSI_* ids call get_outcomes with those ids. Those scores have no confidence interval, so describe differences from the national rate as direction only.
3. If the task asks about patient experience call get_patient_experience.
4. Call submit_finding with the task id, a 2-4 sentence summary using only numbers your tools returned, the table handles and source ids, and gaps (for example hospitals with too few cases).
{RULES}""",
    model=MODEL, model_settings=TOOL_SETTINGS, tools=QUALITY_TOOLS,
    tool_use_behavior=StopAtTools(stop_at_tool_names=["submit_finding"]), reset_tool_choice=False,
)

WRITER = Agent(
    name="Writer",
    instructions="""You write the final answer for a New York hospital cost and quality question. Your input is JSON with the question, facts, gaps, caveats and sources.
Rules:
- Use ONLY the facts provided. Every number you write must be copied character for character from a fact's `display`. Never round, convert, compute or restate a number any other way.
- Each claim lists the ids (F#) of the facts it uses and ends with the source markers of those facts, for example [S1][S2].
- Lead with the answer in the headline. Then 3 to 6 short claims (1-3 sentences each). Total under 350 words.
- Do not write fact ids (F#) in the text; only [S#] markers. A signed display such as +33.5% already means above (or below if negative): write "33.5% above" only if you copy +33.5% verbatim, never add the word "higher" next to it.
- Facts with caveats (small samples, direction only) must be described with that caveat in the same sentence.
- Mortality and complication rates have no confidence interval: say "higher/lower than the national rate (direction only)". Readmission ratio above 1.000 means more readmissions than expected.
- Payments are Medicare fee-for-service payments, not prices or quality. Do not recommend a hospital; describe what the data shows.
- State gaps plainly. data_cannot_tell_you must have at least 2 items specific to this question.
- If facts are missing for part of the question, say so instead of guessing.""",
    model=MODEL, model_settings=SETTINGS,
    output_type=AgentOutputSchema(Report, strict_json_schema=False),
)
