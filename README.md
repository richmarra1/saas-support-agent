# SaaS Support Agent - Agentic AI Workflow

An agentic workflow that orchestrates multiple Claude AI agents to automatically classify, research, and resolve SaaS technical support tickets. Built to demonstrate practical AI orchestration that saves human time in real support operations.

## What This Project Demonstrates

- **Agentic AI Orchestration**: Three specialized AI agents working in a pipeline, each with a distinct role
- **Tool Use**: Agents query a structured knowledge base as a "tool" to ground responses in real data
- **Practical Business Value**: Turns a 15-20 minute manual triage process into a 10-second automated pipeline

## Architecture

```
                    SUPPORT TICKET (raw text)
                            |
                            v
                +-----------------------+
                |   AGENT 1: CLASSIFIER |
                |   (Claude Sonnet)     |
                |-----------------------|
                | - Reads ticket text   |
                | - Assigns category    |
                | - Sets severity level |
                | - Summarizes issue    |
                +-----------+-----------+
                            |
                   classification dict
                            |
                            v
                +-----------------------+
                |  AGENT 2: RESEARCHER  |
                |  (Claude Sonnet)      |
                |-----------------------|
                | - Searches KB (tool)  |
                | - Matches best issue  |
                | - Ranks solutions     |
                | - Flags escalation    |
                +-----------+-----------+
                            |
                    research results dict
                            |
                            v
                +-----------------------+
                |  AGENT 3: RESPONDER   |
                |  (Claude Sonnet)      |
                |-----------------------|
                | - Formats response    |
                | - Adds customer steps |
                | - Includes internal   |
                |   resolution actions  |
                +-----------+-----------+
                            |
                            v
                STRUCTURED SUPPORT RESPONSE
```

## Supported Issue Categories

| Category | Examples |
|----------|----------|
| Authentication & Login | Password resets, SSO/SAML failures, 2FA issues |
| Integration & API | 401 errors, webhook failures, sync problems |
| Performance & Reliability | Slow pages, timeouts, export failures |
| Billing & Account | Unexpected charges, invoice discrepancies |
| Permissions & Access Control | Role misconfigurations, feature access denied |

## Tech Stack

- **Python 3.10+**
- **Anthropic Claude API** (Sonnet) - AI reasoning engine
- **Streamlit** - Web interface
- **Custom Knowledge Base** - Structured troubleshooting data (no vector DB needed)

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/saas-support-agent.git
cd saas-support-agent
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate          # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your Anthropic API key

Get a key from [console.anthropic.com](https://console.anthropic.com/)

```bash
export ANTHROPIC_API_KEY="your-key-here"       # Mac/Linux
# set ANTHROPIC_API_KEY=your-key-here           # Windows CMD
# $env:ANTHROPIC_API_KEY="your-key-here"        # PowerShell
```

### 5. Run the app

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Project Structure

```
saas-support-agent/
|-- app.py              # Streamlit web interface
|-- agents.py           # Three-agent pipeline (classifier, researcher, responder)
|-- knowledge_base.py   # Structured troubleshooting data + search functions
|-- requirements.txt    # Python dependencies
|-- README.md           # This file
```

## How It Works (Technical Detail)

**Agent 1 - Classifier**: Receives raw ticket text. Uses a system prompt that constrains Claude to output JSON with exactly three fields: category, severity, and summary. No tools needed here, just structured output.

**Agent 2 - Researcher**: Takes the classification and calls `search_knowledge_base()` as a tool. This function maps the category to structured troubleshooting data. Claude then reasons over the KB results to select and prioritize the most relevant steps for this specific ticket.

**Agent 3 - Response Formatter**: Receives both the classification and research results. Produces a professional support response that a human agent could send to the customer or use as an internal reference. Includes customer-facing steps, internal resolution actions, and escalation criteria.

**Key Design Decision**: The knowledge base is a Python dictionary, not a vector database. For a support workflow with well-defined categories, exact-match lookup is faster, cheaper, and more reliable than semantic search. Vector DBs add complexity without adding value when your categories are known and finite.

## Example Output

**Input Ticket**: "Our API integration returns 401 errors since yesterday. The key hasn't changed."

**Classification**: Category: Integration | Severity: High | Summary: API returning 401 Unauthorized after no configuration changes

**Response**: A structured troubleshooting guide with prioritized steps specific to 401 auth failures, resolution methods the support team should take, and escalation criteria.

## Future Enhancements

- Add a vector database (ChromaDB/Pinecone) for semantic search across a larger KB
- Implement conversation memory so the agent can handle follow-up questions
- Add Slack/email integration to pull tickets directly from support channels
- Build an evaluation harness to measure agent accuracy across ticket types
- Add a feedback loop where human agents rate responses to improve prompts

## License

MIT
