"""
SaaS Support Agentic Workflow
------------------------------
This module implements a three-agent pipeline that:
1. CLASSIFIER AGENT  - Categorizes the incoming support ticket
2. RESEARCHER AGENT  - Searches the knowledge base for troubleshooting steps
3. RESPONSE AGENT    - Formats a structured support response

The agents use Claude (Sonnet) via the Anthropic API with tool use,
demonstrating agentic orchestration of AI to save human time.
"""

import json
import anthropic
from knowledge_base import search_knowledge_base, get_all_categories


# ---------------------------------------------------------------------------
# Initialize the Anthropic client
# The client reads ANTHROPIC_API_KEY from the environment automatically.
# ---------------------------------------------------------------------------
client = anthropic.Anthropic()

MODEL = "claude-sonnet-4-6"


# ===========================================================================
# AGENT 1 : TICKET CLASSIFIER
# ===========================================================================
def classify_ticket(ticket_text: str) -> dict:
    """
    Takes raw ticket text and returns a structured classification:
    - category (authentication, integration, performance, billing, permissions)
    - severity (low, medium, high, critical)
    - summary (one-line restatement of the problem)
    """

    system_prompt = """You are a SaaS technical support ticket classifier.
Your job is to read a support ticket and classify it into exactly one category
and assign a severity level.

CATEGORIES (pick exactly one):
- authentication : Login issues, password problems, SSO/SAML, 2FA/MFA
- integration    : API errors, webhook failures, third-party sync issues
- performance    : Slow loading, timeouts, export failures, reliability
- billing        : Charges, invoices, payment issues, plan discrepancies
- permissions    : Access denied, role problems, feature access issues

SEVERITY LEVELS:
- critical : Service is completely down or a security issue exists
- high     : A core workflow is blocked for the user
- medium   : Feature is degraded but workarounds exist
- low      : Minor inconvenience, cosmetic, or informational

Respond ONLY with valid JSON. No markdown, no backticks, no explanation.
Format:
{"category": "...", "severity": "...", "summary": "..."}
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Classify this support ticket:\n\n{ticket_text}"}
        ],
    )

    raw_text = response.content[0].text.strip()

    # Clean potential markdown fencing
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        classification = json.loads(raw_text)
    except json.JSONDecodeError:
        classification = {
            "category": "unknown",
            "severity": "medium",
            "summary": "Could not parse classification. Raw: " + raw_text,
        }

    return classification


# ===========================================================================
# AGENT 2 : KNOWLEDGE BASE RESEARCHER
# ===========================================================================
def research_issue(classification: dict) -> dict:
    """
    Uses the classification to search the knowledge base, then asks Claude
    to select the most relevant troubleshooting steps for this specific issue.

    This is the 'tool use' component: Claude decides which KB category to
    search and then reasons over the results.
    """

    category = classification.get("category", "unknown")
    summary = classification.get("summary", "")

    # Step 1: Search the knowledge base (this is our "tool")
    kb_results = search_knowledge_base(category)

    if "error" in kb_results:
        return {
            "matched_issue": None,
            "troubleshooting_steps": [],
            "resolution_methods": [],
            "escalation_trigger": "Category not found. Escalate to Tier 2.",
            "kb_category": category,
        }

    # Step 2: Ask Claude to match the specific issue and rank solutions
    system_prompt = """You are a SaaS support research agent. You have been
given knowledge base results for a support ticket category. Your job is to:

1. Identify which specific issue in the KB best matches the ticket summary.
2. Select the most relevant troubleshooting steps (in priority order).
3. Select the most relevant resolution methods.
4. Include the escalation trigger if applicable.

Respond ONLY with valid JSON. No markdown, no backticks.
Format:
{
    "matched_issue": "the specific issue name from KB",
    "troubleshooting_steps": ["step1", "step2", ...],
    "resolution_methods": ["method1", "method2", ...],
    "escalation_trigger": "when to escalate"
}
"""

    user_message = f"""
Ticket Summary: {summary}
Ticket Category: {category}
Ticket Severity: {classification.get("severity", "medium")}

Knowledge Base Results:
{json.dumps(kb_results, indent=2)}

Match the ticket to the most relevant issue and extract the troubleshooting
steps and resolution methods. Prioritize steps most likely to solve this
specific problem.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        research = json.loads(raw_text)
    except json.JSONDecodeError:
        research = {
            "matched_issue": summary,
            "troubleshooting_steps": ["Unable to parse research results. Manual review needed."],
            "resolution_methods": ["Escalate to Tier 2 support."],
            "escalation_trigger": "Automated research failed.",
        }

    research["kb_category"] = kb_results.get("category", category)
    return research


# ===========================================================================
# AGENT 3 : RESPONSE FORMATTER
# ===========================================================================
def format_response(classification: dict, research: dict) -> str:
    """
    Takes the classification and research results and produces a
    professional, structured support response that a human agent could
    send directly to the customer or use as an internal reference.
    """

    system_prompt = """You are a SaaS support response specialist. You take
classified ticket information and researched troubleshooting data and produce
a clear, professional support response.

Your response should include:
1. A brief acknowledgment of the issue
2. Numbered troubleshooting steps the customer can try
3. What the support team will do on their end (resolution methods)
4. When the issue would be escalated
5. A professional closing

Write in a warm but professional tone. Be specific and actionable.
Do not use markdown headers or bullet points. Use numbered lists for steps.
Keep it concise but thorough.
"""

    user_message = f"""
Create a support response using this information:

TICKET CLASSIFICATION:
- Category: {classification.get("category")}
- Severity: {classification.get("severity")}
- Summary: {classification.get("summary")}

RESEARCH RESULTS:
- Matched Issue: {research.get("matched_issue")}
- Troubleshooting Steps: {json.dumps(research.get("troubleshooting_steps", []))}
- Resolution Methods: {json.dumps(research.get("resolution_methods", []))}
- Escalation Trigger: {research.get("escalation_trigger")}
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


# ===========================================================================
# FULL PIPELINE - Orchestrates all three agents
# ===========================================================================
def process_ticket(ticket_text: str) -> dict:
    """
    Main entry point. Runs the full agentic workflow:
    Ticket Text -> Classifier -> Researcher -> Response Formatter

    Returns a dict with all intermediate results for transparency.
    """

    # Agent 1: Classify
    classification = classify_ticket(ticket_text)

    # Agent 2: Research
    research = research_issue(classification)

    # Agent 3: Format Response
    final_response = format_response(classification, research)

    return {
        "input_ticket": ticket_text,
        "classification": classification,
        "research": research,
        "response": final_response,
    }
