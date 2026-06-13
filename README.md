# SaaS Support Agent: Pipeline vs. Agentic Loop

This project implements the same task, resolving SaaS technical support
tickets, using two different architectures, side by side in one app. The
goal is to demonstrate the difference between an LLM pipeline (sometimes
loosely called "agentic" in industry marketing) and a genuinely agentic
system under the accepted technical definition: an autonomous Reason-Act-
Observe loop in which the model itself decides what action to take next.

## What This Project Demonstrates

- **v1, Sequential Pipeline**: Three Claude calls in a fixed order (Classify,
  Research, Respond), hardcoded in Python. Same input always produces the
  same sequence of operations. This is a compound AI workflow, not an agent.
- **v2, Agentic Loop**: Claude is given a goal and a set of tools (search the
  knowledge base, list categories, escalate to a human, or deliver a
  response). Claude decides which tool to call, observes the result, and
  decides what to do next, including retrying with a different search or
  escalating, until it calls one of two terminal tools. The sequence of
  operations is not fixed in advance and can vary ticket to ticket.
- **Tool Use**: Both versions ground their output in a structured knowledge
  base rather than relying on the model's unverified recall.
- **Practical Business Value**: Turns a 15 to 20 minute manual triage process
  into an automated resolution or a clean escalation with context attached.

## Architecture: v1, Sequential Pipeline

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

The order above never changes. Step 2 always runs after step 1, regardless
of what step 1 found. The code, not the model, is making the routing
decisions.

## Architecture: v2, Agentic Loop

```
                    SUPPORT TICKET (raw text)
                            |
                            v
              +-------------------------------+
              |   CLAUDE (reasons about the   |<------------------+
              |   ticket and decides on an    |                    |
              |   action)                     |                    |
              +---------------+---------------+                    |
                              |                                      |
                  picks ONE tool to call:                            |
                  - search_knowledge_base(category)                  |
                  - list_kb_categories()                             |
                  - escalate_ticket(reason, team, severity)          |
                  - deliver_customer_response(category,              |
                        severity, response_text)                     |
                              |                                       |
                              v                                       |
              +-------------------------------+                      |
              |   TOOL EXECUTES, RESULT IS    |                       |
              |   RETURNED TO CLAUDE          |----------------------+
              +---------------+---------------+
                              |
            if escalate_ticket or deliver_customer_response
                  was called, the loop ends here
                              |
                              v
                  RESOLUTION or ESCALATION
```

Unlike v1, the path through this diagram is not fixed. For a ticket where
the first knowledge base search does not match well, Claude can loop back,
search a different category, and only then decide to resolve or escalate.
The number of steps and the order of tool calls can differ from one ticket
to the next, because Claude is making that decision in real time based on
what it observes.

## Definitions Used in This Project

**Agentic AI**: A system in which the model itself, not the surrounding
code, decides what action to take next based on the outcome of its previous
action, in a Reason-Act-Observe loop (sometimes called ReAct). The defining
test: can you predict the exact sequence of operations before running it?
If yes, it is a pipeline. If the model can deviate based on what it
discovers mid-task, it is agentic.

**LLM pipeline / compound AI workflow**: Multiple LLM calls chained in a
fixed, predetermined order. Often called "agentic" informally, but does not
meet the technical definition above because the model has no control over
sequencing.


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
