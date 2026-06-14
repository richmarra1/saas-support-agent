"""
SaaS Support Agent - Streamlit Web App
----------------------------------------
Toggle between:
  v1 - Sequential Pipeline (Classifier -> Researcher -> Responder)
  v2 - True Agentic Loop (Claude reasons, selects tools, iterates via Reason-Act-Observe)
"""

import streamlit as st
import time
import json
from agents import classify_ticket, research_issue, format_response
from agentic_engine import run_agentic_loop

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SaaS Support Agent",
    page_icon="🔧",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
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
.stButton > button { background: #5046e5; color: white; border: none; border-radius: 8px; padding: 0.6rem 2rem; font-weight: 600; font-size: 1rem; }
.stButton > button:hover { background: #3d35c4; color: white; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="main-header">SaaS Support Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Compare a sequential LLM pipeline (v1) vs. a true agentic loop (v2) '
    'where Claude autonomously selects its own tools via Reason-Act-Observe.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Architecture Toggle
# ---------------------------------------------------------------------------
mode = st.radio(
    "Select Architecture:",
    ["v1 - Sequential Pipeline", "v2 - True Agentic Loop"],
    horizontal=True,
)

if mode == "v1 - Sequential Pipeline":
    st.info("**v1 Pipeline:** Three agents run in a fixed order. Classifier → Researcher → Responder. Each agent has a defined role and hands off structured output.")
else:
    st.info("**v2 Agentic Loop:** Claude receives the ticket and decides which tools to call, in what order, and when it has enough information to respond. No hardcoded sequence. Reason-Act-Observe in practice.")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### How It Works")
    if mode == "v1 - Sequential Pipeline":
        st.markdown(
            "**v1 Sequential Pipeline**\n\n"
            "**Agent 1: Classifier** - Reads the ticket, determines category and severity.\n\n"
            "**Agent 2: Researcher** - Searches the knowledge base for relevant steps.\n\n"
            "**Agent 3: Responder** - Produces a professional support response."
        )
    else:
        st.markdown(
            "**v2 True Agentic Loop**\n\n"
            "Claude receives the raw ticket and autonomously decides:\n\n"
            "1. Which tool to call first\n"
            "2. What to do with the result\n"
            "3. Whether to call another tool or respond\n\n"
            "No hardcoded sequence. The model reasons, acts, observes, and iterates."
        )

    st.divider()
    st.markdown("### Sample Tickets")
    if st.button("Load: Login Issue", use_container_width=True):
        st.session_state["sample"] = (
            "Hi, I've been trying to log into my account for the past hour but "
            "it keeps saying my password is wrong. I've tried resetting it three "
            "times and the reset email never arrives. My team is blocked because "
            "I'm the admin and they need me to approve their access requests. "
            "This is urgent, please help!"
        )
    if st.button("Load: API Error", use_container_width=True):
        st.session_state["sample"] = (
            "Our integration with Salesforce stopped syncing contacts yesterday "
            "around 3pm EST. We're getting 401 Unauthorized errors on every API "
            "call. Nothing changed on our end. The API key is the same one we've "
            "used for 6 months. We have a board meeting tomorrow and need our "
            "pipeline data updated. Please investigate ASAP."
        )
    if st.button("Load: Slow Performance", use_container_width=True):
        st.session_state["sample"] = (
            "The dashboard has been extremely slow for our entire team since "
            "Monday morning. Pages take 30+ seconds to load and sometimes time "
            "out completely. We've tested on Chrome, Firefox, and Edge across "
            "multiple offices. Our internet is fine for every other app."
        )
    if st.button("Load: Billing Question", use_container_width=True):
        st.session_state["sample"] = (
            "We were charged $2,400 this month but our plan should be $1,200. "
            "We only have 15 users on the Professional tier. The invoice shows "
            "some 'API overage' charge that we never agreed to."
        )
    if st.button("Load: Permission Denied", use_container_width=True):
        st.session_state["sample"] = (
            "I was recently promoted to team lead and my manager says she "
            "updated my role, but I still can't access the Analytics dashboard "
            "or export reports. I get a 'You do not have permission' error."
        )

# ---------------------------------------------------------------------------
# Main Input
# ---------------------------------------------------------------------------
default_text = st.session_state.get("sample", "")
ticket_input = st.text_area(
    "Paste a support ticket below:",
    value=default_text,
    height=150,
    placeholder="Example: Our team cannot log in after the SSO migration...",
)

col_btn, col_space = st.columns([1, 3])
with col_btn:
    run_button = st.button("Analyze Ticket", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
if run_button and ticket_input.strip():
    st.session_state.pop("sample", None)
    st.divider()
    total_start = time.time()

    if mode == "v1 - Sequential Pipeline":

        # AGENT 1
        with st.container():
            st.markdown('<div class="agent-card agent-1"><div class="agent-title">Agent 1: Ticket Classifier</div></div>', unsafe_allow_html=True)
            with st.spinner("Classifying ticket..."):
                t1 = time.time()
                classification = classify_ticket(ticket_input)
                t1_elapsed = time.time() - t1
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="metric-box"><div class="metric-label">Category</div><div class="metric-value">{classification.get("category", "N/A").title()}</div></div>', unsafe_allow_html=True)
            with col2:
                severity = classification.get("severity", "medium")
                st.markdown(f'<div class="metric-box"><div class="metric-label">Severity</div><div class="metric-value severity-{severity}">{severity.upper()}</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-box"><div class="metric-label">Classified In</div><div class="metric-value">{t1_elapsed:.1f}s</div></div>', unsafe_allow_html=True)
            st.markdown(f"**Summary:** {classification.get('summary', 'N/A')}")

        # AGENT 2
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
                st.markdown(f'<div class="metric-box"><div class="metric-label">Researched In</div><div class="metric-value">{t2_elapsed:.1f}s</div></div>', unsafe_allow_html=True)
            with st.expander("View Troubleshooting Steps"):
                for i, step in enumerate(research.get("troubleshooting_steps", []), 1):
                    st.markdown(f"{i}. {step}")
            with st.expander("View Resolution Methods"):
                for i, method in enumerate(research.get("resolution_methods", []), 1):
                    st.markdown(f"{i}. {method}")
            if research.get("escalation_trigger"):
                st.info(f"**Escalation Trigger:** {research['escalation_trigger']}")

        # AGENT 3
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

    else:
        # V2 AGENTIC LOOP
        with st.container():
            st.markdown('<div class="agent-card agentic"><div class="agent-title">v2 Agentic Loop: Claude Reasoning Autonomously</div></div>', unsafe_allow_html=True)
            with st.spinner("Claude is reasoning, selecting tools, and iterating..."):
                t_start = time.time()
                agentic_result = run_agentic_loop(ticket_input)
                t_elapsed = time.time() - t_start

            st.markdown(f"**Total Time:** {t_elapsed:.1f}s")
            st.markdown(f"**Tool Calls Made:** {agentic_result.get('tool_calls_made', 'N/A')}")
            st.markdown(f"**Iterations:** {agentic_result.get('iterations', 'N/A')}")

            st.divider()
            st.markdown("### Final Response")
            st.markdown(agentic_result.get("response", "No response generated."))

            with st.expander("View Agentic Reasoning Trace"):
                for i, step in enumerate(agentic_result.get("reasoning_trace", []), 1):
                    st.markdown(f"**Step {i}:** {step}")

            with st.expander("View Raw JSON Output"):
                st.json(agentic_result)

elif run_button and not ticket_input.strip():
    st.warning("Please enter a support ticket to analyze.")