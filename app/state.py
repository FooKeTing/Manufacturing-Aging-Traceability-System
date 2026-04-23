import streamlit as st

def init_state():
    defaults = {
        # =========================
        # MAIN SCAN PAGE
        # =========================
        "selected_rack": "R1",
        "fg_type": "Fresh",
        "fg_sn": "",
        "unsent_sn": [],

        # =========================
        # BATCH PROCESS CONTROL
        # =========================
        "auto_process_running": False,
        "processing_done": False,
        "pass_msg_shown": False,
        "batch_context": None,
        "batch_id": None,

        # =========================
        # TRACEABILITY
        # =========================
        "trace_refreshed": False,

        # =========================
        # CANCEL FLOW
        # =========================
        "confirm_cancel": False,

        # =========================
        # MANUAL ERROR INPUT PAGE
        # =========================
        "manual_fg_sn": "",
        "manual_error": "",
        "manual_custom_error": "",
        "clear_manual_inputs": False,
        "manual_success_msg": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


