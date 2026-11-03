"""Streamlit UI: streamlit run src/mathagent/ui_app.py"""

from __future__ import annotations

import streamlit as st

from mathagent.agent import MathAgent
from mathagent.config import get_settings
from mathagent.data.loader import load_local_samples


st.set_page_config(page_title="MathAgent", page_icon="∑", layout="wide")
st.title("MathAgent")
st.caption("Tool-integrated math reasoning · ToRA / MathChat / SymPy")

settings = get_settings()
with st.sidebar:
    st.header("Settings")
    st.write(f"Model: `{settings.model}`")
    st.write(f"Base URL: `{settings.base_url}`")
    st.write(f"Max turns: `{settings.max_turns}`")
    samples = load_local_samples()
    labels = [f"{s['id']}: {s['problem'][:60]}…" for s in samples]
    pick = st.selectbox("Sample problems", ["(custom)"] + labels)

problem = ""
if pick != "(custom)":
    idx = labels.index(pick)
    problem = samples[idx]["problem"]
    st.info(f"Expected answer: `{samples[idx].get('answer', '')}`")

problem = st.text_area("Problem", value=problem, height=160)

if st.button("Solve", type="primary") and problem.strip():
    log = st.empty()
    lines: list[str] = []

    def on_event(msg: str) -> None:
        lines.append(msg)
        log.code("\n\n".join(lines[-12:]))

    try:
        agent = MathAgent(on_event=on_event)
        result = agent.solve(problem.strip())
        st.success(f"Answer: {result.answer}")
        with st.expander("Full response"):
            st.markdown(result.final_message)
        with st.expander("Tool trace"):
            for e in result.tool_events:
                st.write(f"**{e.name}** `{e.arguments}`")
                st.code(e.result)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
