from __future__ import annotations
import json
import os
from pathlib import Path
import streamlit as st
from worker import AutonomousInvoiceWorker, DEFAULT_DB, DEFAULT_INVOICE_DIR, FinanceStore

st.set_page_config(page_title="CentrAlign AI Task Worker", page_icon="🤖", layout="wide")
st.title("🤖 Autonomous AI Task Worker")
st.caption("A focused proof of concept: invoice discovery → extraction → simulated finance entry → read-back verification")
st.info("Sandbox only. This demo uses local sample invoices and a local SQLite database; it does not access real company systems.")

with st.sidebar:
    st.subheader("Demo environment")
    st.write(f"Invoice directory: `{DEFAULT_INVOICE_DIR.name}/`")
    st.write("Target app: local SQLite finance ledger")
    st.write("LLM credentials: not required")
    if st.button("Reset demo database", use_container_width=True):
        if DEFAULT_DB.exists():
            DEFAULT_DB.unlink()
        st.success("Database removed. It will be recreated on the next run.")
    st.divider()
    st.caption("Try: Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.")

task = st.text_area("What should the worker accomplish?", value="Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.", height=110)
if st.button("Run task", type="primary", use_container_width=True):
    worker = AutonomousInvoiceWorker()
    result = worker.run(task)
    st.session_state["last_result"] = result

result = st.session_state.get("last_result")
if result:
    st.divider()
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Outcome")
        if result["status"] == "completed":
            st.success(result["message"])
        elif result["status"] == "needs_input":
            st.warning(result["message"])
        else:
            st.error(result["message"])
        st.metric("Execution events", len(result["events"]))
    with right:
        st.subheader("Execution trace")
        for event in result["events"]:
            with st.expander(f"{event['kind'].upper()} · {event['message']}", expanded=event["kind"] in ("goal", "complete", "failure", "human_input")):
                if event.get("data") is not None:
                    st.json(event["data"])
    st.subheader("Saved finance records")
    st.dataframe(FinanceStore().list_invoices(), use_container_width=True, hide_index=True)
    st.download_button("Download execution trace (JSON)", data=json.dumps(result, indent=2), file_name="execution_trace.json", mime="application/json")
