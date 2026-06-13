"""
SaaS Support Agent - True Agentic Loop (v2)
---------------------------------------------
This module implements a genuinely agentic version of the support agent.

The key architectural difference from agents.py (the v1 sequential pipeline):

    v1 (agents.py):     Python code decides the order of operations.
                         classify -> research -> respond, always, every time.

    v2 (this module):   Claude decides the order of operations. Claude is
                         given a set of tools (search the knowledge base,
                         list categories, escalate, deliver a response) and
                         a goal (resolve the ticket). Claude reasons about
                         what to do next, calls a tool, observes the result,
                         and decides whether to act again, try a different
                         search, escalate, or conclude.

This is the "agent loop" pattern (Reason -> Act -> Observe), sometimes
called ReAct. The loop terminates only when Claude itself calls one of the
two terminal tools (deliver_customer_response or escalate_ticket), or when
a safety cap on steps is reached.
"""

import json
import anthropic
from knowledge_base import search_knowledge_base, get_all_categories


client = anthropic.Anthropic()

MODEL = "claude-sonnet-4-6"

MAX_STEPS = 6  # safety guardrail against infinite loops


# ===========================================================================
# TOOL DEFINITIONS
# ===========================================================================
# These are passed to the Claude API. Claude decides which tool to call,
# with what arguments, and when. Two of these tools are "terminal" -
# calling them ends the agent loop.
TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": (
            "Search the internal support knowledge base for troubleshooting "
            "guidance on a specific category. Returns matched issues with "
            "troubleshooting steps, resolution methods, and escalation "
            "triggers. Valid categories: authentication, integration, "
            "performance, billing, permissions. You may call this multiple "
            "times with different categories if the first search does not "
            "produce a good match."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "The support category to search, e.g. "
                                    "'authentication', 'integration', "
                                    "'performance', 'billing', 'permissions'",
                }
            },
            "required": ["category"],
        },
    },
    {
        "name": "list_kb_categories",
        "description": (
            "List every category available in the knowledge base. Use this "
            "if a search_knowledge_base call returned no match and you are "
            "unsure which category fits the ticket."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "escalate_ticket",
        "description": (
            "TERMINAL ACTION. Escalate this ticket to a human specialist "
            "team. Use this when the knowledge base does not contain a "
            "matching issue, when severity is critical and requires human "
            "judgment, or when the ticket is too ambiguous to resolve "
            "without more information from the customer. Calling this ends "
            "the workflow."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why this ticket needs human escalation",
                },
                "escalation_team": {
                    "type": "string",
                    "description": "Which team should receive this, e.g. "
                                    "'Tier 2 Support', 'Engineering', "
                                    "'Security', 'Billing'",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
            },
            "required": ["reason", "escalation_team", "severity"],
        },
    },
    {
        "name": "deliver_customer_response",
        "description": (
            "TERMINAL ACTION. Deliver the final, customer-facing support "
            "response. Use this when you have enough information from the "
            "knowledge base to resolve the ticket. Calling this ends the "
            "workflow."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "response_text": {
                    "type": "string",
                    "description": "The full customer-facing response. Warm "
                                    "but professional tone. Numbered "
                                    "troubleshooting steps. No markdown "
                                    "headers.",
                },
            },
            "required": ["category", "severity", "response_text"],
        },
    },
]


SYSTEM_PROMPT = """You are an autonomous SaaS technical support agent.

A customer has submitted a support ticket. Your goal is to resolve it.

You have access to tools:
- search_knowledge_base: look up troubleshooting guidance by category
- list_kb_categories: see all available categories if you are unsure which fits
- escalate_ticket: end the workflow by escalating to a human team
- deliver_customer_response: end the workflow by sending a resolution to the customer

Think step by step about what category this ticket falls into, search the
knowledge base, and evaluate whether the results actually match the
customer's specific problem. If the first search does not produce a good
match, try a different category or use list_kb_categories before giving up.

If the knowledge base gives you a clear matching issue, use
deliver_customer_response to resolve the ticket directly.

If the ticket is a security issue, the knowledge base has no good match, or
the situation is ambiguous enough that a human should review it, use
escalate_ticket instead. Do not guess at solutions that are not grounded in
the knowledge base.

Every workflow must end with exactly one call to either
deliver_customer_response or escalate_ticket."""


# ===========================================================================
# TOOL EXECUTION
# ===========================================================================
def _execute_tool(name: str, tool_input: dict) -> dict:
    """
    Executes a single tool call and returns the result that gets sent back
    to Claude as a tool_result. Also returns whether this tool call is
    terminal (ends the loop).
    """
    if name == "search_knowledge_base":
        result = search_knowledge_base(tool_input.get("category", ""))
        return result, None

    if name == "list_kb_categories":
        return {"categories": get_all_categories()}, None

    if name == "escalate_ticket":
        return {"status": "Ticket escalated successfully."}, {
            "outcome": "escalated",
            "data": tool_input,
        }

    if name == "deliver_customer_response":
        return {"status": "Response delivered to customer."}, {
            "outcome": "resolved",
            "data": tool_input,
        }

    return {"error": f"Unknown tool: {name}"}, None


# ===========================================================================
# THE AGENT LOOP
# ===========================================================================
def run_agent(ticket_text: str) -> dict:
    """
    Runs the full agentic loop for a single support ticket.

    Returns a dict containing:
      - trace: a step-by-step record of Claude's reasoning, tool calls, and
        tool results, for transparency and portfolio demonstration
      - outcome: "resolved", "escalated", or "max_steps_reached"
      - data: the arguments from the terminal tool call (the resolution or
        the escalation details)
    """
    messages = [
        {"role": "user", "content": f"New support ticket:\n\n{ticket_text}"}
    ]
    trace = []

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        text_parts = [b.text for b in response.content if b.type == "text"]
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        step_record = {
            "step": step,
            "reasoning": " ".join(text_parts).strip(),
            "tool_calls": [{"name": t.name, "input": t.input} for t in tool_uses],
        }

        # Claude responded with no tool call. Treat its text as the final
        # answer and end the loop (defensive fallback, should be rare given
        # the system prompt requires a terminal tool call).
        if not tool_uses:
            step_record["note"] = "No tool call. Treating text as final response."
            trace.append(step_record)
            return {
                "trace": trace,
                "outcome": "resolved",
                "data": {
                    "category": "unknown",
                    "severity": "medium",
                    "response_text": " ".join(text_parts).strip(),
                },
            }

        messages.append({"role": "assistant", "content": response.content})

        tool_results_content = []
        terminal = None

        for tool_use in tool_uses:
            result, terminal_info = _execute_tool(tool_use.name, tool_use.input)
            tool_results_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result),
                }
            )
            if terminal_info is not None:
                terminal = terminal_info

        step_record["tool_results"] = [
            json.loads(r["content"]) for r in tool_results_content
        ]
        trace.append(step_record)

        if terminal is not None:
            return {"trace": trace, "outcome": terminal["outcome"], "data": terminal["data"]}

        messages.append({"role": "user", "content": tool_results_content})

    # Safety cap reached without a terminal tool call
    return {
        "trace": trace,
        "outcome": "max_steps_reached",
        "data": {
            "reason": f"Agent did not reach a terminal action within {MAX_STEPS} steps.",
        },
    }
