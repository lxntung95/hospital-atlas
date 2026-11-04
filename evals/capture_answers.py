"""Run the README questions through a running hospital-atlas server and save the final answers to evals/agent_answers.md.

    uv run python evals/capture_answers.py                       # local server on :8080
    uv run python evals/capture_answers.py --url https://... --token "$(gcloud auth print-identity-token)"
"""

import argparse
import datetime as dt
import uuid
from pathlib import Path

import httpx

from evals.common import CASES, auth_headers


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--token", default="")
    a = ap.parse_args()
    out = [f"# Agent answers\n\nServer: {a.url}. Captured {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC.\n"]
    with httpx.Client(timeout=300, headers=auth_headers(a.token)) as c:
        for name, turns in CASES:
            sid = str(uuid.uuid4())
            out.append(f"## {name}\n")
            for t in turns:
                d = c.post(f"{a.url}/chat", json={"message": t, "session_id": sid}).json()
                m = d.get("meta") or {}
                out.append(f"**User:** {t}\n\n*{m.get('elapsed_s')} s, rounds {m.get('rounds')}, audit {m.get('audit')}*\n\n{d['response']}\n")
                print(name, m.get("elapsed_s"), "s")
    Path(__file__).with_name("agent_answers.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
