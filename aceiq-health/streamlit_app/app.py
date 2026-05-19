"""AceIQ Health — Streamlit demo UI."""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import streamlit as st

API_URL = "http://localhost:8000"

SAMPLE_QUESTIONS = [
    "What is the renal dosing for metformin?",
    "What are the contraindications for metformin?",
    "Can atorvastatin be used during pregnancy?",
    "What are the major drug interactions of atorvastatin?",
    "What is the half-life of amoxicillin?",
    "What are common adverse reactions to amoxicillin?",
    "What is the boxed warning for metformin?",
]

DISCLAIMER = (
    "⚠️  **Educational reference only; not clinical advice.** "
    "Verify against primary sources before patient care."
)


# ── Helpers ───────────────────────────────────────────────────────────────────


@st.cache_data(ttl=30)
def fetch_health() -> dict:
    try:
        resp = httpx.get(f"{API_URL}/health", timeout=5)
        return resp.json()
    except Exception:
        return {"status": "unreachable", "document_count": "?", "chunk_count": "?"}


def query_api(question: str) -> dict:
    resp = httpx.post(f"{API_URL}/api/v1/query", json={"question": question}, timeout=60)
    resp.raise_for_status()
    return resp.json()


# ── Layout ────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AceIQ Health",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─ Sidebar ─
with st.sidebar:
    st.title("💊 AceIQ Health")
    st.caption("Drug reference assistant for medical students & junior doctors")

    st.divider()

    health = fetch_health()
    status_icon = "🟢" if health.get("status") == "ok" else "🔴"
    st.subheader(f"{status_icon} System")
    st.metric("Documents", health.get("document_count", "?"))
    st.metric("Chunks", health.get("chunk_count", "?"))
    st.caption(f"Env: {health.get('app_env', '?')}")
    has_ant = health.get("has_anthropic", False)
    has_oai = health.get("has_openai", False)
    st.caption(f"Anthropic: {'✅' if has_ant else '❌'}  OpenAI: {'✅' if has_oai else '❌'}")

    st.divider()

    st.subheader("📋 Sample questions")
    for i, sample in enumerate(SAMPLE_QUESTIONS):
        if st.button(sample, key=f"sample_{i}", use_container_width=True):
            st.session_state["prefill"] = sample

    st.divider()
    st.warning(DISCLAIMER, icon="⚕️")

# ─ Main pane ─
st.title("AceIQ Health")
st.caption("AI-native drug reference — grounded, cited answers in seconds")

if "prefill" in st.session_state:
    default_question = st.session_state.pop("prefill")
else:
    default_question = ""

question = st.text_input(
    "Ask a drug label question:",
    value=default_question,
    placeholder="e.g. What are the contraindications for metformin?",
)

if st.button("Search", type="primary", disabled=not question.strip()):
    with st.spinner("Retrieving and generating answer…"):
        t0 = time.perf_counter()
        try:
            data = query_api(question.strip())
        except Exception as exc:
            st.error(f"API error: {exc}")
            st.stop()

    if data.get("refused"):
        st.warning(data["answer"], icon="🚫")
    else:
        st.success(data["answer"])

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Latency", f"{data.get('latency_ms', 0)} ms")
        col2.metric("Model", data.get("model_used", "—"))
        col3.metric("Provider", data.get("provider_used", "—"))
        v_score = data.get("verifier_score")
        col4.metric("Verifier score", f"{v_score:.2f}" if v_score is not None else "N/A")

        # Citations
        citations = data.get("citations", [])
        if citations:
            st.subheader("📚 Sources")
            for i, cit in enumerate(citations, 1):
                with st.expander(
                    f"{i}. {cit.get('drug_name', '?')} — {cit.get('section', '?')}",
                    expanded=(i == 1),
                ):
                    st.caption(f"Source: {cit.get('source')} / {cit.get('external_id')}")
                    st.write(cit.get("excerpt", ""))
        else:
            st.info("No citations returned.")

    st.divider()
    st.caption(DISCLAIMER)
