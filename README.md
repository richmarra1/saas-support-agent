# SaaS Support Agent: Pipeline vs. Agentic Loop

Two architectures, one task. A sequential LLM pipeline (v1) vs. a true agentic loop (v2) where Claude autonomously selects its own tools via a Reason-Act-Observe cycle. Built to demonstrate the architectural difference between chaining prompts and genuine agentic behavior.

## Live Architecture Comparison

**v1 – Sequential Pipeline**: Three Claude agents run in a fixed order. Classifier → Researcher → Responder. Each agent has a defined role and hands off a structured output. Predictable, fast, and easy to debug.

**v2 – True Agentic Loop**: Claude receives the ticket and decides which tools to call, in what order, and when it has enough information to respond. No hardcoded sequence. The model reasons, acts, observes the result, and iterates. This is the Reason-Act-Observe loop in practice and the first genuinely agentic application in this portfolio.

## What This Project Demonstrates

- Agentic AI: Claude Sonnet tool-use API with autonomous tool selection and escalation logic
- Pipeline AI: Three-agent sequential orchestration with structured JSON handoffs
- Practical contrast: Same support ticket, two fundamentally different execution models
- Tool use: Agents query a structured knowledge base as a callable tool

## Tech Stack

- Python 3.10+
- Anthropic Claude Sonnet (tool-use API for v2)
- Streamlit
- Custom structured knowledge base (no vector DB required)

## Setup

1. Clone the repo
2. Create and activate a virtual environment
3. Run `pip install -r requirements.txt`
4. Set `ANTHROPIC_API_KEY` as an environment variable
5. Run `streamlit run app.py`

## Architecture – v1 Pipeline
