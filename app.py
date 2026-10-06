"""
SaaS Support Agent - Streamlit Web App
----------------------------------------
Toggle between:
  v1 - Sequential Pipeline (Classifier -> Researcher -> Responder)
  v2 - True Agentic Loop (Claude reasons, selects tools, iterates via Reason-Act-Observe)
"""

import html
import time

import streamlit as st
from agents import classify_ticket, research_issue, format_response
from agentic_engine import run_agent

st.set_page_config(
    page_title="SaaS Support Agent",
    page_icon="🔧",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
.stApp { font-family: 'DM Sans', sans-serif; }
.main-header { font-size: 2.2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem; }
.sub-header { font-size: 1.05rem; color: #6c6c8a; margin-bottom: 2rem; }
.agent-card { background: #f8f9fc; border: 1px solid #e2e4f0; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; }
.agent-title { font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; }
.agent-1 { color: #5046e5; border-left: 4px solid #5046e5; }
.agent-2 { color: #0891b2; border-left: 4px solid #0891b2; }
.agent-3 { color: #059669; border-left: 4px solid #059669; }
.agentic { color: #7c3aed; border-left: 4px solid #7c3aed; }
.severity-critical { color: #dc2626; font-weight: 700; }
.severity-high { color: #ea580c; font-weight: 700; }
.severity-medium { color: #ca8a04; font-weight: 700; }
.severity-low { color: #16a34a; font-weight: 700; }
.metric-box { background: white; border: 1px solid #e2e4f0; border-radius: 8px; padding: 1rem; text-align: center; }
.metric-value { font-size: 1.5rem; font-weight: 700; color: #1a1a2e; }
.metric-label { font-size: 0.8rem; color: #6c6c8a; text-transform: uppercase; letter-spacing: 0.05em; }
.step-card { background: white; border: 1px solid #e2e4f0; border-left: 4px solid #7c3aed; border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem; }
.step-head { font-size: 0.8rem; font-weight: 700; color: #7c3aed; text-transform: uppercase; letter-spacing: 0.06em; }
.step-reason { color: #1a1a2e; margin: 0.35rem 0; }
.step-tool { font-family: monospace; font-size: 0.85rem; color: #0891b2; }
.step-result { font-size: 0.85rem; color: #6c6c8a; }
.step-terminal { border-left-color: #059669; }
.stButton > button { background: #5046e5; color: white; border: none; border-radius: 8px; padding: 0.6rem 2rem; font-weight: 600; font-size: 1rem; }
.stButton > button:hover { background: #3d35c4; color: white; }
</style>
""", unsafe_allow_html=True)


def metric_box(label: str, value: str, extra_class: str = "") -> None:
    st.markdown(
        f'<div class="metric-box"><div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value {extra_class}">{html.escape(str(value))}</div></div>',
        unsafe_allow_html=True,
    )


st.markdown('<div class="main-header">SaaS Support Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Compare a sequential LLM pipeline (v1) vs. a true agentic loop (v2) where Claude autonomously selects its own tools via Reason-Act-Observe.</div>', unsafe_allow_html=True)

mode = st.radio("Select Architecture:", ["v1 - Sequential Pipeline", "v2 - True Agentic Loop"], horizontal=True)

if mode == "v1 - Sequential Pipeline":
    st.info("**v1 Pipeline:** Three agents run in a fixed order. Classifier → Researcher → Responder. Each agent has a defined role and hands off structured output.")
else:
    st.info("**v2 Agentic Loop:** Claude receives the ticket and decides which tools to call, in what order, and when it has enough information to respond or escalate. No hardcoded sequence. Reason-Act-Observe in practice.")

with st.sidebar:
    st.markdown("### How It Works")
    if mode == "v1 - Sequential Pipeline":
        st.markdown("**v1 Sequential Pipeline**\n\n**Agent 1: Classifier** - Reads the ticket, determines category and severity.\n\n**Agent 2: Researcher** - Searches the knowledge base for relevant steps.\n\n**Agent 3: Responder** - Produces a professional support response.")
    else:
        st.markdown("**v2 True Agentic Loop**\n\nClaude receives the raw ticket and autonomously decides:\n\n1. Which tool to call first\n2. What to do with the result\n3. Whether to search again, escalate, or respond\n\nWhen it finishes, Claude files a structured case report (category, severity, matched issue, steps) so you get the same detail as v1, plus the full reasoning trace.")
    st.divider()
    st.markdown("### Sample Tickets")
    if st.button("Load: Login Issue", use_container_width=True):
        st.session_state["sample"] = "Hi, I've been trying to log into my account for the past hour but it keeps saying my password is wrong. I've tried resetting it three times and the reset email never arrives. My team is blocked because I'm the admin. This is urgent!"
    if st.button("Load: API Error", use_container_width=True):
        st.session_state["sample"] = "Our integration with Salesforce stopped syncing contacts yesterday around 3pm EST. We're getting 401 Unauthorized errors on every API call. Nothing changed on our end. Please investigate ASAP."
    if st.button("Load: Slow Performance", use_container_width=True):
        st.session_state["sample"] = "The dashboard has been extremely slow for our entire team since Monday. Pages take 30+ seconds to load and sometimes time out completely."
    if st.button("Load: Billing Question", use_container_width=True):
        st.session_state["sample"] = "We were charged $2,400 this month but our plan should be $1,200. The invoice shows some API overage charge we never agreed to."
    if st.button("Load: Permission Denied", use_container_width=True):
        st.session_state["sample"] = "I was promoted to team lead but still can't access the Analytics dashboard. I get a 'You do not have permission' error. Other team leads can see it fine."

default_text = st.session_state.get("sample", "")
ticket_input = st.text_area("Paste a support ticket below:", value=default_text, height=150, placeholder="Example: Our team cannot log in after the SSO migration...")

col_btn, col_space = st.columns([1, 3])
with col_btn:
    run_button = st.button("Analyze Ticket", type="primary", use_container_width=True)

if run_button and ticket_input.strip():
    st.session_state.pop("sample", None)
    st.divider()
    total_start = time.time()

    # =======================================================================
    # v1 - SEQUENTIAL PIPELINE
    # =======================================================================
    if mode == "v1 - Sequential Pipeline":
        with st.container():
            st.markdown('<div class="agent-card agent-1"><div class="agent-title">Agent 1: Ticket Classifier</div></div>', unsafe_allow_html=True)
            with st.spinner("Classifying ticket..."):
                t1 = time.time()
                classification = classify_ticket(ticket_input)
                t1_elapsed = time.time() - t1
            col1, col2, col3 = st.columns(3)
            with col1:
                metric_box("Category", classification.get("category", "N/A").title())
            with col2:
                severity = classification.get("severity", "medium")
                metric_box("Severity", severity.upper(), f"severity-{severity}")
            with col3:
                metric_box("Classified In", f"{t1_elapsed:.1f}s")
            st.markdown(f"**Summary:** {classification.get('summary', 'N/A')}")

        with st.container():
            st.markdown('<div class="agent-card agent-2"><div class="agent-title">Agent 2: Knowledge Base Researcher</div></div>', unsafe_allow_html=True)
            with st.spinner("Searching knowledge base..."):
                t2 = time.time()
                research = research_issue(classification)
                t2_elapsed = time.time() - t2
            col_match, col_time = st.columns([3, 1])
            with col_match:
                st.markdown(f"**Matched Issue:** {research.get('matched_issue', 'N/A')}")
            with col_time:
                metric_box("Researched In", f"{t2_elapsed:.1f}s")
            with st.expander("View Troubleshooting Steps"):
                for i, step in enumerate(research.get("troubleshooting_steps", []), 1):
                    st.markdown(f"{i}. {step}")
            with st.expander("View Resolution Methods"):
                for i, method in enumerate(research.get("resolution_methods", []), 1):
                    st.markdown(f"{i}. {method}")
            if research.get("escalation_trigger"):
                st.info(f"**Escalation Trigger:** {research['escalation_trigger']}")

        with st.container():
            st.markdown('<div class="agent-card agent-3"><div class="agent-title">Agent 3: Response Formatter</div></div>', unsafe_allow_html=True)
            with st.spinner("Generating response..."):
                t3 = time.time()
                final_response = format_response(classification, research)
                t3_elapsed = time.time() - t3
            st.markdown(final_response)

        total_elapsed = time.time() - total_start
        st.divider()
        st.markdown("### Pipeline Summary")
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Total Time", f"{total_elapsed:.1f}s")
        with m2: st.metric("Agents Used", "3")
        with m3: st.metric("API Calls", "3")
        with m4: st.metric("Architecture", "Sequential")
        with st.expander("View Raw JSON Output"):
            st.json({"input_ticket": ticket_input, "classification": classification, "research": research, "response": final_response})

    # =======================================================================
    # v2 - TRUE AGENTIC LOOP
    # =======================================================================
    else:
        with st.spinner("Claude is reasoning, selecting tools, and iterating..."):
            agentic_result = run_agent(ticket_input)

        outcome = agentic_result.get("outcome", "unknown")
        data = agentic_result.get("data", {}) or {}
        stats = agentic_result.get("stats", {}) or {}
        trace = agentic_result.get("trace", []) or []

        # --- Outcome banner -------------------------------------------------
        if outcome == "resolved":
            st.success("**Outcome: Resolved by the agent.** Claude found a matching knowledge base issue and delivered a response.")
        elif outcome == "escalated":
            team = data.get("escalation_team", "a specialist team")
            st.warning(f"**Outcome: Escalated to {team}.** Claude decided this ticket needs human review.")
        else:
            st.error(f"**Outcome: {outcome}.** {data.get('reason', '')}")

        # --- Case report (same detail as v1) -------------------------------
        st.markdown('<div class="agent-card agentic"><div class="agent-title">Agent Case Report</div></div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_box("Category", str(data.get("category", "N/A")).title())
        with c2:
            sev = str(data.get("severity", "medium")).lower()
            metric_box("Severity", sev.upper(), f"severity-{sev}")
        with c3:
            metric_box("Confidence", str(data.get("confidence", "N/A")).title())
        with c4:
            metric_box("Resolved In", f"{stats.get('elapsed_s', 0):.1f}s")
        if data.get("summary"):
            st.markdown(f"**Summary:** {data['summary']}")

        # --- Agent reasoning trace (the "agentic" part) --------------------
        st.markdown('<div class="agent-card agentic"><div class="agent-title">Reasoning Trace: Reason → Act → Observe</div></div>', unsafe_allow_html=True)
        for step in trace:
            is_terminal = any(tc.get("terminal") for tc in step.get("tool_calls", []))
            parts = [
                f'<div class="step-card{" step-terminal" if is_terminal else ""}">',
                f'<div class="step-head">Step {step.get("step")} · {step.get("duration_s", 0):.1f}s</div>',
            ]
            if step.get("reasoning"):
                parts.append(f'<div class="step-reason">💭 {html.escape(step["reasoning"])}</div>')
            for tc in step.get("tool_calls", []):
                args = "" if tc.get("terminal") else ", ".join(
                    f"{k}={v!r}" for k, v in (tc.get("input") or {}).items()
                )
                parts.append(f'<div class="step-tool">⚙️ {html.escape(tc.get("name", ""))}({html.escape(args)})</div>')
                if tc.get("result_summary"):
                    parts.append(f'<div class="step-result">👁️ {html.escape(tc["result_summary"])}</div>')
            if step.get("note"):
                parts.append(f'<div class="step-result">{html.escape(step["note"])}</div>')
            parts.append("</div>")
            st.markdown("".join(parts), unsafe_allow_html=True)

        # --- Knowledge base findings ---------------------------------------
        st.markdown('<div class="agent-card agent-2"><div class="agent-title">Knowledge Base Findings</div></div>', unsafe_allow_html=True)
        searched = stats.get("categories_searched", [])
        col_match, col_searched = st.columns([3, 1])
        with col_match:
            st.markdown(f"**Matched Issue:** {data.get('matched_issue', 'N/A')}")
        with col_searched:
            metric_box("Categories Searched", str(len(searched)))
        if searched:
            st.caption("Searched: " + " → ".join(searched))
        steps_list = data.get("troubleshooting_steps") or []
        methods_list = data.get("resolution_methods") or []
        with st.expander(f"View Troubleshooting Steps ({len(steps_list)})"):
            for i, s in enumerate(steps_list, 1):
                st.markdown(f"{i}. {s}")
        with st.expander(f"View Resolution Methods ({len(methods_list)})"):
            for i, m in enumerate(methods_list, 1):
                st.markdown(f"{i}. {m}")
        if data.get("escalation_trigger"):
            st.info(f"**Escalation Trigger:** {data['escalation_trigger']}")

        # --- Escalation details --------------------------------------------
        if outcome == "escalated":
            st.markdown('<div class="agent-card agent-1"><div class="agent-title">Escalation Details</div></div>', unsafe_allow_html=True)
            st.markdown(f"**Team:** {data.get('escalation_team', 'N/A')}")
            st.markdown(f"**Reason:** {data.get('reason', 'N/A')}")

        # --- Final customer message ----------------------------------------
        st.markdown('<div class="agent-card agent-3"><div class="agent-title">Customer Response</div></div>', unsafe_allow_html=True)
        customer_text = data.get("response_text") or data.get("customer_message") or "No response generated."
        st.markdown(customer_text)

        # --- Summary metrics -----------------------------------------------
        total_elapsed = time.time() - total_start
        st.divider()
        st.markdown("### Agentic Loop Summary")
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Total Time", f"{total_elapsed:.1f}s")
        with m2: st.metric("Reasoning Steps", str(stats.get("steps", len(trace))))
        with m3: st.metric("API Calls", str(stats.get("api_calls", len(trace))))
        with m4: st.metric("Tool Calls", str(len(stats.get("tools_used", []))))
        with st.expander("View Raw JSON Output"):
            st.json(agentic_result)

elif run_button and not ticket_input.strip():
    st.warning("Please enter a support ticket to analyze.")
