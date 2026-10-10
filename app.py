"""Run with uv run streamlit run app.py."""
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

from ai_agent.agent import run_single_step


def main():
    load_dotenv(Path(__file__).with_name(".env"), override=False)
    st.title("Financial Research Agent — Lesson 1")
    st.caption("Evidence, tools, and agent decisions: one tool-call step.")
    st.write("Price: what happened. News: what is reported. SEC: filing metadata, not full contents.")
    with st.form("research"):
        question = st.text_input("Financial research question", placeholder="How did NVDA close over the last 5 trading sessions?")
        submitted = st.form_submit_button("Research once")
    if submitted:
        with st.spinner("Selecting a tool and retrieving evidence…"):
            result = run_single_step(question)
        if result["error"]:
            st.warning(result["error"])
        if result["trace"]:
            st.subheader("Execution trace")
            st.json(result["trace"])
        if result["observation"] is not None:
            st.subheader("Structured observation")
            st.json(result["observation"])
        if result["answer"]:
            st.subheader("Evidence-based answer")
            st.write(result["answer"])


if __name__ == "__main__":
    main()
