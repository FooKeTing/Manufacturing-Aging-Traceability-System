import streamlit as st
import os
import time

from database import init_db, get_connection
from state import init_state
from setting import BASE_PATH_TRACE, TRACE_DB_NAME, RACK_LIST, ERROR_OPTIONS
from app.service.traceability_service import refresh_traceability_excel
from app_controller import scan_fg_sn, start_batch, end_batch, auto_process_check, cancel_batch, display_scan_summary
from app.service.troubleshooting_service import process_manual_failed_unit, save_manual_failure, get_troubleshooting_data, update_troubleshooting, get_all_troubleshooting
from chart import *

init_db()
init_state()

multiPage = st.sidebar.selectbox("Select Page", ["Scan FG SN", "Manual Input Error Failed Unit", "Troubleshooting Records", "Charts"])

conn = get_connection() 

if multiPage == "Scan FG SN":
    st.title("📦 Scan FG SN Batch Processing")
    st.divider()

    st.text_input("Enter Order ID (3 characters)", key = "order_id", placeholder = "Enter Order ID for this batch")

    if st.button("🔄 Refresh Traceability Database"):
        trace_file = os.path.join(BASE_PATH_TRACE, TRACE_DB_NAME)

        with st.spinner("Refreshing Traceability Excel..."):
            try:
                refresh_traceability_excel(trace_file)

                st.cache_data.clear()

                if "trace_refreshed" in st.session_state:
                    del st.session_state["trace_refreshed"]

                st.success("Traceability Excel refreshed successfully!")

            except Exception as e:
                st.error(f"Failed to refresh Excel: {e}")

    selected_rack = st.selectbox("Select Rack",RACK_LIST, key = "selected_rack")

    st.selectbox("Select Unit Type",["Fresh", "OBA"],key="fg_type")

    st.text_input("Scan Unit Serial Number", key = "fg_sn", max_chars = 6, on_change = scan_fg_sn)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("Start Batch (Record time start)", on_click = start_batch)
    with col2:
        st.button("End Batch (Record time end) & Create Folder", on_click = end_batch)

        if st.session_state.get("auto_process_running") and not st.session_state.get("processing_done"):
            auto_process_check()
    with col3:
        if not st.session_state.confirm_cancel:
            if st.button("Cancel Batch ⚠️"):
                st.session_state.confirm_cancel = True
        else:
            st.warning("Are you sure you want to cancel this batch?")

            col_yes, col_no = st.columns(2)

            with col_yes:
                st.button("✅ Yes, Cancel", on_click = cancel_batch)
            
            with col_no:
                if st.button("❌ No"):
                    st.session_state.confirm_cancel = False

    display_scan_summary(st.session_state.selected_rack)

elif multiPage == "Manual Input Error Failed Unit":
    st.title("Manual Input Error for Failed Unit")
    st.divider()

    if st.session_state.get("clear_manual_inputs"):
        st.session_state.manual_fg_sn = ""
        st.session_state.manual_error = ""
        st.session_state.manual_custom_error = ""
        st.session_state.clear_manual_inputs = False

    if st.session_state.get("manual_success_msg"):
        st.success(st.session_state.manual_success_msg)
        st.session_state.manual_success_msg = None

    fg_sn_input = st.text_input("Scan FG Serial Number", max_chars=6, placeholder="Scan or enter FG SN", key="manual_fg_sn")

    if fg_sn_input:

        result = process_manual_failed_unit(conn, fg_sn_input)

        if result["status"] == "not_found":
            st.error("FG SN not found in database.")
            st.stop()

        else:
            fg_sn = result["fg_sn"]

            st.info(f"FG SN: {fg_sn}")

            selected_error = st.selectbox("Select Failure Reason", ERROR_OPTIONS, key="manual_error")

            custom_error = ""
            if selected_error == "Others":
                custom_error = st.text_input("Please enter failure reason", key="manual_custom_error")

            final_error_reason = (custom_error if selected_error == "Others" and custom_error else selected_error)

            if st.button("💾 Save Error Reason"):

                save_manual_failure(conn, fg_sn_input, final_error_reason)

                st.session_state.manual_success_msg = f"Manual failure recorded for {fg_sn_input}"
                st.session_state.clear_manual_inputs = True
                
                st.rerun()

elif multiPage == "Troubleshooting Records":

    st.title("Troubleshooting report")

    df_failed = get_troubleshooting_data(conn)

    if df_failed.empty:
        st.info("No troubleshooting records found.")

    else:
        df_failed["display"] = df_failed["batch_id"].astype(str) + " - " + df_failed["fg_sn"]

        selected_display = st.selectbox("Select Unit SN to Edit (batch_num - fg_sn)", df_failed["display"])

        selected_row = df_failed[df_failed["display"] == selected_display].iloc[0]
        selected_id = selected_row["batch_id"]

        st.subheader("Error Description")
        st.write(selected_row["error"] or "No description available")

        st.divider()
        st.subheader("Edit troubleshooting details")

        action_finding = st.text_area("Finding / Action Taken", value=selected_row["action_finding"] or "")

        status = st.selectbox(
            "Troubleshooting Status",
            ["Open", "In Progress", "Closed"],
            index=["Open", "In Progress", "Closed"].index(
                selected_row["troubleshooting_status"]
                if selected_row["troubleshooting_status"] in ["Open", "In Progress", "Closed"]
                else "Open"
            )
        )

        root_cause = st.text_area("Root Cause", value=selected_row["root_cause"] or "")

        batch_id = int(selected_row["batch_id"])
        fg_sn = str(selected_row["fg_sn"])

        if st.button("💾 Update Troubleshooting Record"):
            update_troubleshooting(conn,
                batch_id,
                fg_sn,
                root_cause,
                status,
                action_finding
            )

            st.success("Record updated successfully!")

            time.sleep(2)
            st.rerun()

        st.divider()

        df_all = get_all_troubleshooting(conn)
        st.dataframe(df_all, width = "stretch")

elif multiPage == "Charts":
    st.title("📈 Batch Analysis Dashboard")
    st.divider()

    selected_order = select_order()
    if selected_order:
        with st.container():
            st.subheader("📊 Yield Loss Analysis for First Failed Units ")
            df_yield = get_yield_data(selected_order)
            tab1, tab2 = st.tabs(["📋 Table", "📊 Yield Loss Chart"], default="📊 Yield Loss Chart")
            
            with tab1:
                show_yield_table(df_yield.rename(columns={"batch_id": "Batch ID", "total": "Total Unit Scanned", "failed": "Total Failed Unit", "yield_loss": "Yield Loss (%)"}))
            with tab2:
                show_yield_loss_chart(df_yield)

        with st.container():
            st.subheader("📊 First Failed Units by Error Description")
            df = get_error_data(selected_order)
            tab1, tab2, tab3 = st.tabs(["📋 Table", "📊 Bar Chart", "🥧 Pie Chart"], default="📊 Bar Chart")
            
            with tab1:
                show_error_table(df.rename(columns={"error_desc": "Error Description", "count": "Number of Unit"}))
            with tab2:
                show_error_bar_chart(df)
            with tab3:
                show_error_pie_chart(df)

        with st.container():
            st.subheader("📊 Error by Root Cause")
            df = get_root_cause_data(selected_order)
            tab1, tab2, tab3 = st.tabs(["📋 Table", "📊 Bar Chart", "🥧 Pie Chart"], default="📊 Bar Chart")
            
            with tab1:
                show_root_cause_table(df.rename(columns={"root_cause": "Root Cause", "count": "Number of Error"}))
            with tab2:
                show_root_cause_bar_chart(df)
            with tab3:
                show_root_cause_pie_chart(df)