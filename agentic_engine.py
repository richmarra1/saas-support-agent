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

Both terminal tools require Claude to file a structured "case report"
(category, severity, summary, matched KB issue, steps, confidence...) so the
UI can show the same level of detail as v1 - while Claude still controls
the workflow.
"""
import json
import os
import time

import anthropic
import streamlit as st
from knowledge_base import search_knowledge_base, get_all_categories


def _get_api_key():
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        key = os.getenv("ANTHROPIC_API_KEY", "")
    return key.strip().strip('"').strip("'")


client = anthropic.Anthropic(api_key=_get_api_key())

MODEL = "claude-sonnet-4-6"

MAX_STEPS = 6  # safety guardrail against infinite loops

TERMINAL_TOOLS = {"deliver_customer_response", "escalate_ticket"}


# ===========================================================================
# SHARED "CASE REPORT" FIELDS
# ===========================================================================
# Both terminal tools require these fields. This is what lets the UI show
# category, severity, summary, matched issue, etc. for the agentic version.
SEVERITY_ENUM = ["low", "medium", "high", "critical"]

CASE_REPORT_PROPERTIES = {
    "category": {
        "type": "string",
        "enum": ["authentication", "integration", "performance",
                 "billing", "permissions", "other"],
        "description": "The support category you determined for this ticket.",
    },
    "severity": {
        "type": "string",
        "enum": SEVERITY_ENUM,
        "description": (
            "critical = service down or security issue; high = core workflow "
            "blocked; medium = degraded but workaround exists; low = minor."
        ),
    },
    "summary": {
        "type": "string",
        "description": "One-sentence restatement of the customer's problem.",
    },
    "matched_issue": {
        "type": "string",
        "description": (
            "The exact 'issue' name from the knowledge base that best matches "
            "this ticket, or 'No match' if none fits."
        ),
    },
    "troubleshooting_steps": {
        "type": "array",
        "items": {"type": "string"},
        "description": (
            "The most relevant troubleshooting steps from the knowledge base, "
            "in priority order. Empty list if there was no match."
        ),
    },
    "resolution_methods": {
        "type": "array",
        "items": {"type": "string"},
        "description": (
            "The most relevant resolution methods from the knowledge base. "
            "Empty list if there was no match."
        ),
    },
    "escalation_trigger": {
        "type": "string",
        "description": "The KB escalation trigger for the matched issue, if any.",
    },
    "confidence": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "How confident you are that the KB match fits this ticket.",
    },
}

CASE_REPORT_REQUIRED = [
    "category", "severity", "summary", "matched_issue",
    "troubleshooting_steps", "resolution_methods", "confidence",
]


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
            "the workflow. You must also fill in the full case report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **CASE_REPORT_PROPERTIES,
                "reason": {
                    "type": "string",
                    "description": "Why this ticket needs human escalation.",
                },
                "escalation_team": {
                    "type": "string",
                    "description": "Which team should receive this, e.g. "
                                    "'Tier 2 Support', 'Engineering', "
                                    "'Security', 'Billing', 'Finance'.",
                },
                "customer_message": {
                    "type": "string",
                    "description": (
                        "A short, warm holding reply to the customer: "
                        "acknowledge the issue, say it has been escalated to "
                        "a specialist team, and list any safe steps they can "
                        "try meanwhile. No markdown headers."
                    ),
                },
            },
            "required": CASE_REPORT_REQUIRED
            + ["reason", "escalation_team", "customer_message"],
        },
    },
    {
        "name": "deliver_customer_response",
        "description": (
            "TERMINAL ACTION. Deliver the final, customer-facing support "
            "response. Use this when you have enough information from the "
            "knowledge base to resolve the ticket. Calling this ends the "
            "workflow. You must also fill in the full case report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **CASE_REPORT_PROPERTIES,
                "response_text": {
                    "type": "string",
                    "description": "The full customer-facing response. Warm "
                                    "but professional tone. Numbered "
                                    "troubleshooting steps. No markdown "
                                    "headers.",
                },
            },
            "required": CASE_REPORT_REQUIRED + ["response_text"],
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

Before each tool call, briefly explain your reasoning in one or two
sentences (what you think the problem is and why you are choosing this tool).

Think about what category this ticket falls into, search the knowledge base,
and evaluate whether the results actually match the customer's specific
problem. If the first search does not produce a good match, try a different
category or use list_kb_categories before giving up.

If the knowledge base gives you a clear matching issue, use
deliver_customer_response to resolve the ticket directly.

If the ticket is a security issue, the knowledge base has no good match, or
the situation is ambiguous enough that a human should review it, use
escalate_ticket instead. Do not guess at solutions that are not grounded in
the knowledge base.

Whichever terminal tool you call, fill in the full case report: category,
severity, one-sentence summary, the exact matched KB issue name, the
relevant troubleshooting steps and resolution methods copied from the
knowledge base, the escalation trigger, and your confidence.

Every workflow must end with exactly one call to either
deliver_customer_response or escalate_ticket."""


# ===========================================================================
# TOOL EXECUTION
# ===========================================================================
def _execute_tool(name: str, tool_input: dict):
    """
    Executes a single tool call and returns (result, terminal_info).
    result is sent back to Claude as a tool_result. terminal_info is not
    None when the tool ends the loop.
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


def _summarize_result(name: str, result: dict) -> str:
    """Short, human-readable description of a tool result for the UI trace."""
    if name == "search_knowledge_base":
        if "error" in result:
            return f"No match: {result['error']}"
        issues = [i.get("issue", "") for i in result.get("common_issues", [])]
        return (
            f"Found '{result.get('category', '')}' with {len(issues)} issue(s): "
            + "; ".join(issues)
        )
    if name == "list_kb_categories":
        return "Categories: " + ", ".join(result.get("categories", []))
    return result.get("status") or result.get("error") or ""


# ===========================================================================
# THE AGENT LOOP
# ===========================================================================
def run_agent(ticket_text: str) -> dict:
    """
    Runs the full agentic loop for a single support ticket.

    Returns a dict containing:
      - trace: step-by-step record of Claude's reasoning, tool calls, and
        tool results (for transparency and portfolio demonstration)
      - outcome: "resolved", "escalated", or "max_steps_reached"
      - data: the case report from the terminal tool call
      - stats: api_calls, steps, tools_used, categories_searched, elapsed_s
    """
    start = time.time()
    messages = [
        {"role": "user", "content": f"New support ticket:\n\n{ticket_text}"}
    ]
    trace = []
    api_calls = 0
    tools_used = []
    categories_searched = []

    def _stats():
        return {
            "api_calls": api_calls,
            "steps": len(trace),
            "tools_used": tools_used,
            "categories_searched": categories_searched,
            "elapsed_s": round(time.time() - start, 2),
        }

    for step in range(1, MAX_STEPS + 1):
        step_start = time.time()
        response = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        api_calls += 1

        text_parts = [b.text for b in response.content if b.type == "text"]
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        step_record = {
            "step": step,
            "reasoning": " ".join(text_parts).strip(),
            "tool_calls": [],
        }

        # Claude responded with no tool call. Treat its text as the final
        # answer and end the loop (defensive fallback, should be rare given
        # the system prompt requires a terminal tool call).
        if not tool_uses:
            step_record["note"] = "No tool call. Treating text as final response."
            step_record["duration_s"] = round(time.time() - step_start, 2)
            trace.append(step_record)
            return {
                "trace": trace,
                "outcome": "resolved",
                "data": {
                    "category": "other",
                    "severity": "medium",
                    "summary": "Agent answered without filing a case report.",
                    "matched_issue": "N/A",
                    "troubleshooting_steps": [],
                    "resolution_methods": [],
                    "confidence": "low",
                    "response_text": " ".join(text_parts).strip(),
                },
                "stats": _stats(),
            }

        messages.append({"role": "assistant", "content": response.content})

        tool_results_content = []
        terminal = None

        for tool_use in tool_uses:
            result, terminal_info = _execute_tool(tool_use.name, tool_use.input)
            tools_used.append(tool_use.name)
            if tool_use.name == "search_knowledge_base":
                categories_searched.append(tool_use.input.get("category", ""))

            # Keep the trace readable: don't repeat the whole case report
            # for terminal tools (it's shown separately in the UI).
            shown_input = (
                {"see": "case report"} if tool_use.name in TERMINAL_TOOLS
                else tool_use.input
            )
            step_record["tool_calls"].append({
                "name": tool_use.name,
                "input": shown_input,
                "result_summary": _summarize_result(tool_use.name, result),
                "terminal": tool_use.name in TERMINAL_TOOLS,
            })

            tool_results_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result),
                }
            )
            if terminal_info is not None:
                terminal = terminal_info

        step_record["duration_s"] = round(time.time() - step_start, 2)
        trace.append(step_record)

        if terminal is not None:
            return {
                "trace": trace,
                "outcome": terminal["outcome"],
                "data": terminal["data"],
                "stats": _stats(),
            }

        messages.append({"role": "user", "content": tool_results_content})

    # Safety cap reached without a terminal tool call
    return {
        "trace": trace,
        "outcome": "max_steps_reached",
        "data": {
            "reason": f"Agent did not reach a terminal action within {MAX_STEPS} steps.",
        },
        "stats": _stats(),
    }
