"""Baseline: the same model with NO system prompt and NO tools, asked the three README questions.
Writes evals/baselines.md (raw outputs, model, timestamp).

    uv run python evals/baseline.py
"""

import datetime as dt
from pathlib import Path

import litellm

from atlas import config

Q1 = "For major hip/knee replacement without complications (DRG 470), which five NY hospitals had the highest average total Medicare payment in 2024, and how do they compare with the NY and national averages?"
Q2 = "How does Montefiore compare with other Bronx hospitals on heart failure — Medicare payment, 30-day readmissions and mortality?"
Q3 = ["Which NY hospitals are the best?", "Hip and knee replacement in New York City, both cost and quality."]
MORE = ["What will I pay out of pocket for a knee replacement at NYU?", "Cheapest knee replacement in Boston?"]
MODEL = config.DEFAULT_MODEL


def ask(messages: list[dict]) -> str:
    r = litellm.completion(model=MODEL, vertex_location="global", messages=messages, timeout=90, num_retries=2)
    return r.choices[0].message.content or ""


def main() -> None:
    out = [f"# No-tools baselines\n\nModel: `{MODEL}`, no system prompt, no tools. Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC.\n"]
    for name, turns in [("Q1", [Q1]), ("Q2", [Q2]), ("Q3", Q3), ("More 1", [MORE[0]]), ("More 2", [MORE[1]])]:
        msgs: list[dict] = []
        out.append(f"## {name}\n")
        for t in turns:
            msgs.append({"role": "user", "content": t})
            a = ask(msgs)
            msgs.append({"role": "assistant", "content": a})
            out.append(f"**User:** {t}\n\n**Model:**\n\n{a}\n")
    Path(__file__).with_name("baselines.md").write_text("\n".join(out))
    print("wrote evals/baselines.md")


if __name__ == "__main__":
    main()
