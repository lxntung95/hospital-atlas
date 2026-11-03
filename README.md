# hospital-atlas

A multi-agent deep research agent that compares hospitals on cost and quality
using public CMS data, with cited reports. Work in progress (Project 2,
Agentic AI for Data Science).

Currently still the starter scaffold (FastAPI + LiteLLM + Gemini):

- The harness loop is wrapped in `run_agent()`.
- The model string is `vertex_ai/gemini-3.5-flash-lite`.
- `/chat` also returns the tool calls the harness made, and the page shows them
  above the assistant's answer.

## Setup

1. A GCP project with billing and the Agent Platform API enabled
   (older docs and the endpoint itself still call it Vertex AI)
2. `gcloud auth application-default login`
3. `uv run app.py`, then open http://localhost:8000

Try: "Is it nice enough to go for a walk in New York?"

To run the same server against the local model from class, no Google account needed:

```bash
MODEL=ollama_chat/qwen2.5:1.5b uv run app.py
```

The weather comes from Open-Meteo, which needs no API key.
