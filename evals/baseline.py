"""Baseline: the same model with NO system prompt and NO tools, asked the three README questions.
Writes evals/baselines.md (raw outputs, model, timestamp).

    uv run python -m evals.baseline
"""

import datetime as dt
from pathlib import Path

import litellm

from atlas import config
from evals.common import CASES

MODEL = config.DEFAULT_MODEL


def ask(messages: list[dict]) -> str:
    r = litellm.completion(model=MODEL, vertex_location="global", messages=messages, timeout=90, num_retries=2)
    return r.choices[0].message.content or ""


def main() -> None:
    out = [f"# No-tools baselines\n\nModel: `{MODEL}`, no system prompt, no tools. Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC.\n"]
    for name, turns in CASES:
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
