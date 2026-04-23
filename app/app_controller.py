import streamlit as st
import time
import pandas as pd

from database import get_connection
from app.service.batch_service import scan_fg_sn_logic, start_batch_logic, get_latest_batch_id, end_batch_logic, create_folder
from app.service.aging_service import get_batch_time_range, check_pass_files, process_passed_results
from app.service.failure_excel_service import check_fail_excel
from app.service.troubleshooting_service import process_failed_result_details
from app.service.summary_service import get_scan_summary_data, colour_status
from setting import MAX_PER_RACK


def scan_fg_sn():
    conn = get_connection() 

    result = scan_fg_sn_logic(
        conn = conn,
        fg_sn = st.session_state.fg_sn,
        order_id = st.session_state.order_id,
        rack = st.session_state.selected_rack,
        fg_type = st.session_state.get("fg_type", "Fresh"),
        unsent_sn = st.session_state.unsent_sn
    )

    conn.close()

    if result["status"] == "error":
        st.warning(result["message"])
        st.session_state.fg_sn = ""
        return

    if result["status"] == "ok":
        st.session_state.unsent_sn.append(result["data"])
        st.session_state.selected_rack = result["data"]["rack"]
        st.session_state.fg_sn = ""

def start_batch():
    conn = get_connection()

    try:
        order_id = st.session_state.get("order_id")
        unsent_sn = st.session_state.get("unsent_sn", [])

        if not order_id:
            st.warning("Order ID is required")
            return

        status, result = start_batch_logic(conn, order_id, unsent_sn)

        if not status:
            st.warning(result)
            return

        st.session_state.unsent_sn = []
        st.session_state.batch_id = result

        st.success(f"Batch {result} started successfully")

    finally:
        conn.close()

def set_batch_context(conn, batch_id, order_id, result_folder):
    batch_start, batch_end, date_start, date_end = get_batch_time_range(conn, batch_id)

    st.session_state.batch_context = {
        "batch_id": batch_id,
        "order_id": order_id,
        "result_folder": result_folder,
        "date_start": date_start,
        "date_end": date_end
    }

def auto_process_check():
    if not st.session_state.get("auto_process_running"):
        return

    ctx = st.session_state.get("batch_context")
    if not ctx:
        return

    batch_id = ctx["batch_id"]
    order_id = ctx["order_id"]
    result_folder = ctx["result_folder"]
    date_start = ctx["date_start"]
    date_end = ctx["date_end"]

    with st.status("🔄 Monitoring result folder...", expanded=True) as status:

        while st.session_state.get("auto_process_running"):

            conn = get_connection()

            passstatus, pass_msg, files, filesB = check_pass_files(conn, result_folder, date_start, date_end)
            failstatus, fail_msg, filesErrExcel = check_fail_excel(result_folder, date_start, date_end)
    
            if passstatus:
                if not st.session_state.pass_msg_shown:
                    st.info("✅ Pass files detected. Processing...")
                    st.session_state.pass_msg_shown = True
               
                process_passed_results(conn, order_id, batch_id, result_folder)

                if failstatus:
                    st.info(f"✅ All files ready. Analyzing result...")

                    process_failed_result_details(conn, order_id, batch_id, result_folder)

                    status.update(label="🎉 Processing completed!", state="complete")
                    st.session_state.auto_process_running = False
                    st.session_state.pass_msg_shown = False
                    break
                else:
                    status.update(label=f"⏳ {fail_msg} Please put the result files into: {result_folder}", state="running")
                
            else:
                status.update(label=f"⏳ {pass_msg} Please put the result files into: {result_folder}", state="running")

            time.sleep(3)

def end_batch():
    conn = get_connection()

    try:
        batch_id = get_latest_batch_id(conn)

        status, result = end_batch_logic(conn, batch_id)
        if not status:
            st.warning(result)
            return

        time_end = result
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()

    order_id = st.session_state.order_id.strip()

    status, result = create_folder(order_id, time_end)
    if not status:
        st.warning(result)
        return

    result_folder = result

    conn = get_connection()
    set_batch_context(conn, batch_id, order_id, result_folder)
    conn.close()

    st.session_state.auto_process_running = True
    st.session_state.pass_msg_shown = False
    st.session_state.processing_done = False  

    st.success("Batch ended and auto-processing started")

    auto_process_check()

def cancel_batch():
    st.session_state.unsent_sn = []

    st.session_state.order_id = ""
    st.session_state.fg_sn = ""
    st.session_state.selected_rack = "R1"
    st.session_state.confirm_cancel = False

    st.session_state.processing_done = False
    st.session_state.auto_process_running = False

    st.warning("Batch cancelled. All temporary scanned SN cleared.")

    st.rerun()

def display_scan_summary(selected_rack):
    conn = get_connection()

    try:
        current_count = len([
            x for x in st.session_state.unsent_sn
            if x.get("rack") == selected_rack
        ])

        st.progress(min(current_count / MAX_PER_RACK, 1.0))
        st.markdown(f"**Rack {selected_rack} Load:** {current_count} / {MAX_PER_RACK}")

        if st.session_state.unsent_sn:
            st.subheader("Preview SNs")
            preview_df = pd.DataFrame(st.session_state.unsent_sn)
            st.dataframe(preview_df)

        order_id = st.session_state.get("order_id", "").strip()

        df, summary = get_scan_summary_data(conn, order_id)

        if df.empty:
            return

        # ---------- SUMMARY ----------
        st.subheader("Rack Summary Table")

        summary_display = summary[[
            "batch_id","date","Time Start","Time End",
            "pc","rack","order_id",
            "T_New","T_Rework","T_OBA",
            "P_New","P_Rework","P_OBA",
            "F_New","F_Rework","F_OBA"
        ]]

        summary_display.columns = pd.MultiIndex.from_tuples([
            ("", "Batch"),
            ("", "Date"),
            ("", "Time Start"),
            ("", "Time End"),
            ("", "PC"),
            ("", "Rack"),
            ("", "Order ID"),

            ("Test Quantity", "New"),
            ("Test Quantity", "Rework/Retest"),
            ("Test Quantity", "OBA"),

            ("Passed", "New"),
            ("Passed", "Rework/Retest"),
            ("Passed", "OBA"),

            ("Failed", "New"),
            ("Failed", "Rework/Retest"),
            ("Failed", "OBA"),
        ])

        st.dataframe(summary_display, width = "stretch")

        # ---------- DETAIL TABLE ----------
        st.subheader("All Scan Records")

        st.dataframe(df.style.map(colour_status, subset=["fg_status"]))

    finally:
        conn.close()