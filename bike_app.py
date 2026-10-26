import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

import bike_tools
from bike_agent import PRICING_URL, run_bike_agent

st.set_page_config(page_title="Bay Wheels plan advisor", layout="wide")
st.title("Bay Wheels: monthly membership or pay per use")

uploaded = st.file_uploader("Trip CSV", type="csv")
url = st.text_input("Pricing page URL", PRICING_URL)
if st.button("Run", type="primary", disabled=uploaded is None):
    path = Path(tempfile.gettempdir()) / "uploaded.csv"
    path.write_bytes(uploaded.getvalue())
    with st.spinner("Agent is working..."):
        st.session_state["run"] = run_bike_agent(path, url, label=uploaded.name)

run = st.session_state.get("run")
if run:
    parsed = run["parsed"]
    strip = st.columns(4)
    strip[0].metric("Steps", f"{run['steps']} ({run['tool_calls']} tool calls)")
    strip[1].metric("Total time", f"{run['seconds']} s")
    strip[2].metric("Stop reason", run["stop_reason"])
    strip[3].metric("Trips", run["rows"])

    timeline_col, result_col = st.columns([2, 3])
    with timeline_col:
        st.subheader("Timeline")
        number = 0
        for item in run["timeline"]:
            if item["kind"] == "call":
                number += 1
                st.markdown(f"**{number}. {item['tool']}**")
                st.code(json.dumps(item["args"]), language="json")
            else:
                st.caption(f"observation from {item['tool']}")
                st.code(item["content"][:600], language="json")

    with result_col:
        st.subheader("Results")
        st.markdown(f"### Decision: {parsed['decision'] or 'none'}")
        st.table(pd.DataFrame([
            {"plan": "Pay per ride/minute", "total ($)": parsed["pay_per_use_total"]},
            {"plan": "Monthly membership + residual charges", "total ($)": parsed["membership_total"]},
        ]))
        st.markdown(f"**Break-even vs actual:** {parsed['break_even']}")
        st.markdown(f"**Justification:** {parsed['justification']}")
        weekly = [i["args"]["sql"] for i in run["timeline"] if i["kind"] == "call" and i["tool"] == "csv_sql"
                  and "%W" in i["args"].get("sql", "")]
        if weekly:
            limit, bike_tools.MAX_ROWS = bike_tools.MAX_ROWS, 1000
            table = bike_tools.csv_sql(weekly[-1])
            bike_tools.MAX_ROWS = limit
            if table["success"]:
                st.markdown(f"**By week** ({table['data']['row_count']} weeks, agent query re-run for the full table)")
                st.dataframe(pd.DataFrame(table["data"]["rows"]), height=210, hide_index=True)
        st.markdown(f"**Assumptions and caveats:** {parsed['assumptions']}")
        if run["snapshot"]:
            snap = run["snapshot"]
            st.markdown("**Citations**")
            st.markdown(f"- Pricing page: {snap['url']} (served from {snap['final_url']})\n"
                        f"- Captured: {snap['accessed']}\n- SHA-256 of page text: `{snap['sha256']}`")
        with st.expander("Raw final answer"):
            st.text(run["final"])
