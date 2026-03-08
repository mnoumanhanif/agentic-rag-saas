"""Streamlit UI for the Agentic RAG system."""

import os

import requests
import streamlit as st

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Agentic RAG System", page_icon="🤖", layout="wide")

st.title("🤖 Agentic RAG System")
st.markdown(
    "Upload PDFs and ask questions with intelligent retrieval, "
    "reasoning, and self-reflection."
)

# Sidebar
with st.sidebar:
    st.header("📁 Document Upload")
    uploaded_files = st.file_uploader(
        "Choose PDF files", type="pdf", accept_multiple_files=True
    )

    if st.button("Process Documents", type="primary"):
        if uploaded_files:
            with st.spinner("Processing documents..."):
                files = [
                    ("files", (file.name, file, "application/pdf"))
                    for file in uploaded_files
                ]
                try:
                    response = requests.post(
                        f"{API_URL}/upload", files=files, timeout=120
                    )
                    if response.status_code == 200:
                        st.success(f"✅ {response.json()['message']}")
                    else:
                        st.error(f"❌ Error: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to backend. Is it running?")
                except requests.exceptions.Timeout:
                    st.error("Request timed out. Try with fewer documents.")
        else:
            st.warning("Please upload at least one PDF file.")

    st.divider()

    # System Health
    st.header("🔍 System Status")
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.status_code == 200:
            data = health.json()
            st.metric("Status", data["status"].capitalize())
            st.metric("Version", data["version"])
            col1, col2 = st.columns(2)
            with col1:
                if data["llm_available"]:
                    st.success("LLM ✓")
                else:
                    st.error("LLM ✗")
            with col2:
                if data["vector_store_loaded"]:
                    st.success("Docs ✓")
                else:
                    st.warning("No docs")
        else:
            st.error("Backend unavailable")
    except Exception:
        st.info("Backend not connected")

    st.divider()

    # Settings
    st.header("⚙️ Settings")
    show_sources = st.checkbox("Show sources", value=True)
    show_steps = st.checkbox("Show pipeline steps", value=False)
    show_reflection = st.checkbox("Show reflection", value=False)

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources") and show_sources:
            with st.expander("📚 Sources"):
                for i, src in enumerate(message["sources"], 1):
                    st.markdown(
                        f"**Source {i}**: {src.get('metadata', {}).get('source', 'Unknown')}"
                    )
                    st.text(src.get("content", "")[:300])
        if message.get("steps") and show_steps:
            with st.expander("🔄 Pipeline Steps"):
                for step in message["steps"]:
                    st.markdown(f"- {step}")
        if message.get("reflection") and show_reflection:
            with st.expander("🪞 Reflection"):
                refl = message["reflection"]
                st.metric("Quality Score", f"{refl.get('score', 0):.2f}")
                if refl.get("feedback"):
                    st.markdown(f"**Feedback**: {refl['feedback']}")

if prompt := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            chat_history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            response = requests.post(
                f"{API_URL}/query",
                json={"query": prompt, "chat_history": chat_history},
                timeout=120,
            )
            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                message_placeholder.markdown(answer)
                msg_data = {
                    "role": "assistant",
                    "content": answer,
                    "sources": data.get("sources", []),
                    "steps": data.get("steps", []),
                    "reflection": data.get("reflection"),
                }
                st.session_state.messages.append(msg_data)

                if data.get("sources") and show_sources:
                    with st.expander("📚 Sources"):
                        for i, src in enumerate(data["sources"], 1):
                            st.markdown(
                                f"**Source {i}**: "
                                f"{src.get('metadata', {}).get('source', 'Unknown')}"
                            )
                            st.text(src.get("content", "")[:300])
                if data.get("steps") and show_steps:
                    with st.expander("🔄 Pipeline Steps"):
                        for step in data["steps"]:
                            st.markdown(f"- {step}")
                if data.get("reflection") and show_reflection:
                    with st.expander("🪞 Reflection"):
                        refl = data["reflection"]
                        st.metric("Quality Score", f"{refl.get('score', 0):.2f}")
                        if refl.get("feedback"):
                            st.markdown(f"**Feedback**: {refl['feedback']}")
            else:
                error_msg = f"Error: {response.text}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to backend. Is it running?"
            message_placeholder.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )
        except requests.exceptions.Timeout:
            error_msg = "Request timed out. Please try again."
            message_placeholder.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )
