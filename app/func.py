import streamlit as st
from datetime import datetime
import glob
import os
import xlwings as xw
import time
import pandas as pd
from config import MAX_PER_RACK, RACK_PC, RACK_LIST, BASE_PATH_TRACE, SHARED_PATH, TRACE_DB_NAME, ERROR_CODE_DESC, ERROR_OPTIONS 
from db import init_db, get_connection

init_db()

def warn_no_order_id(order_id):
    if not order_id:
        st.error("Order ID is empty. Please enter Order ID!")
        return False
    return True

def get_next_rack(selected_rack):
    if selected_rack in RACK_LIST:
        idx = RACK_LIST.index(selected_rack)
        if idx + 1 < len(RACK_LIST):
            return RACK_LIST[idx+1]
    return None

def get_latest_batch_id():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(batch_id) FROM unit_records")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] is not None else 0

def get_batch_time_range(batch_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time_start, time_end
        FROM unit_records
        WHERE batch_id = ?
        LIMIT 1
    """, (batch_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0] or not row[1]:
        return None, None, None, None

    batch_start = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    batch_end = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
    date_start = batch_start.strftime("%y%m%d")
    date_end = batch_end.strftime("%y%m%d")
    return batch_start, batch_end, date_start, date_end

def check_pass_files(result_folder, date_start, date_end):
    all_files = glob.glob(os.path.join(result_folder, "*.xlsx"))

    filesA = []
    filesB = []

    for f in all_files:
        fname = os.path.basename(f).lower()

        if "result" not in fname.lower():
            continue

        parts = fname.split("_")

        if len(parts) < 2:
            continue

        file_date = parts[0]

        if file_date == date_start or file_date == date_end:
            if "_a_" in fname.lower():
                filesA.append(f)
            elif "_b_" in fname.lower():
                filesB.append(f)

    if not filesA:
        return False, "Waiting Aging Result A...", [], []
    if not filesB:
        return False, "Waiting Aging Result B...", [], []
    return True, "Aging Result A and B are ready.", filesA, filesB

def check_fail_excel(result_folder, date_start, date_end):
    all_files = glob.glob(os.path.join(result_folder, "*.xlsx"))
    filesErrExcel = []

    for f in all_files:
        fname = os.path.basename(f).lower()

        if "error" not in fname.lower():
            continue

        parts = fname.replace(".xlsx" , "").split("_")

        if len(parts) < 3:
            continue

        file_date = parts[0]

        if file_date == date_start or file_date == date_end:
            filesErrExcel.append(f)

    if not filesErrExcel:
        return False, "Waiting Aging Error...", []
    return True, "Aging Error are ready.", filesErrExcel

def refresh_traceability_excel(trace_file):
        try:
            app = xw.App(visible=False)
            app.screen_updating = False
            app.display_alerts = False
            wb = app.books.open(trace_file)
            wb.api.RefreshAll()

            timeout = 60
            start_time = time.time()
            while wb.api.Application.CalculationState != 0:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Excel calculation took too long")
                time.sleep(1)

            wb.save()
            wb.close()
            app.quit()
            print("Traceability Excel refreshed.")

        except Exception as e:
            print(f"Traceability refresh failed: {e}")

@st.cache_data(ttl=3600)
def load_traceability(trace_file):
    trace_df = pd.read_excel(
        trace_file,
        sheet_name="FG Linking",
        usecols=[0,1,2],
        dtype=str,
        engine="openpyxl"
    )

    trace_bin_df = pd.read_excel(
        trace_file,
        sheet_name="HB SMT",
        usecols=[0,5],
        dtype=str,
        engine="openpyxl"
    )
    return trace_df, trace_bin_df

@st.cache_data(ttl=3600)
def load_traceability_dict():
    trace_file = os.path.join(BASE_PATH_TRACE,TRACE_DB_NAME)

    if "trace_refreshed" not in st.session_state:
        refresh_traceability_excel(trace_file)
        st.session_state.trace_refreshed = True

    trace_df, trace_bin_df = load_traceability(trace_file)

    if trace_df.shape[1] < 3:
        st.error("Traceability file does not have the data(fg sn, cb sn/psu sn & sn type).")
        return
    if trace_bin_df.shape[1] < 2:
        st.error("Traceability file does not have the data(hb sn & hb bin).")
        return

    fg_col = trace_df.columns[0]
    pcba_col = trace_df.columns[1]
    type_col = trace_df.columns[2]
    bin_col = trace_bin_df.columns[0]
    hb_col = trace_bin_df.columns[1]

    trace_cb = trace_df[trace_df[type_col] == "CBLM"]
    trace_psu = trace_df[trace_df[type_col] == "PS"]

    trace_df.columns = trace_df.columns.str.strip()
    trace_bin_df.columns = trace_bin_df.columns.str.strip()
    trace_bin_df[hb_col] = trace_bin_df[hb_col].astype(str).str.strip()
    trace_bin_df[bin_col] = trace_bin_df[bin_col].astype(str).str.strip()

    trace_cb_dict = dict(zip(
        trace_cb[fg_col].astype(str),
        trace_cb[pcba_col].astype(str)
    ))
    trace_psu_dict = dict(zip(
        trace_psu[fg_col].astype(str),
        trace_psu[pcba_col].astype(str)
    ))

    trace_bin_dict = dict(zip(
        trace_bin_df[hb_col],
        trace_bin_df[bin_col]
    ))

    return trace_cb_dict,trace_psu_dict ,trace_bin_dict

def get_fail_count(batch_id):
    conn = get_connection() 
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM unit_records
            WHERE batch_id = ?
            AND aging_result = 'Failed'
        """, (batch_id,))
        fail_count = cursor.fetchone()[0]
    finally:
        conn.close() 
    return fail_count

def get_hb_bin(hb_sn_list, trace_bin_dict):
    bins = [
        trace_bin_dict.get(str(sn).strip())
        for sn in hb_sn_list
        if sn
    ]

    bins = [b for b in bins if b is not None]

    if len(bins) == 0:
        return None
    elif len(set(bins)) == 1:
        return bins[0]
    else:
        return "MIXED"

def create_folder(order_id, time_end_str):
    try:
        time_end_dt = datetime.strptime(time_end_str, "%Y-%m-%d %H:%M:%S")
        folder_name = time_end_dt.strftime("%y%m%d_%H%M")

        full_path = os.path.join(SHARED_PATH, order_id, folder_name)

        os.makedirs(full_path, exist_ok=True)

        return full_path

    except Exception as e:
        print("Error creating folder:", e)
        return None

def display_scan_summary(selected_rack):
    conn = get_connection()
    cursor = conn.cursor()

    current_count = len([
        x for x in st.session_state.unsent_sn 
        if x["rack"] == selected_rack
    ])
    
    progress_ratio = current_count / MAX_PER_RACK
    st.progress(progress_ratio)

    st.markdown(f"**Rack {selected_rack} Load:** {current_count} / {MAX_PER_RACK} units")

    if st.session_state.unsent_sn:
        st.subheader("Preview: SNs scanned before batch start")
        preview_sn_df = pd.DataFrame(st.session_state.unsent_sn)
        st.dataframe(preview_sn_df[["fg_sn","rack","fg_status","pc","timestamp"]])
    
    order_id = st.session_state.order_id.strip()
    if order_id:
        df = pd.read_sql_query("""
            SELECT * FROM unit_records 
            WHERE order_id = ?""", 
            conn, params=(order_id,))
    else:
        df = pd.read_sql_query("SELECT * FROM unit_records", conn)

    if df.empty:
        return
    df["time_start"] = pd.to_datetime(df["time_start"])
    df["time_end"] = pd.to_datetime(df["time_end"])
    df["date"] = pd.to_datetime(df["date"], errors='coerce').dt.strftime("%d/%m/%Y")
    df["aging_result"] = df["aging_result"].fillna("NULL")

    def pivot_and_rename(data, prefix):
        grouped = data.groupby([
            "batch_id","date","time_start","time_end","pc","rack","order_id","fg_status"
        ]).size().reset_index(name="qty")
        pivot = grouped.pivot_table(
            index=["batch_id","date","time_start","time_end","pc","rack","order_id"],
            columns="fg_status",
            values="qty",
            fill_value=0
        ).reset_index()
        for col in ["Fresh","Rework","OBA"]:
            if col not in pivot.columns:
                pivot[col] = 0
        return pivot.rename(columns={"Fresh":f"{prefix}_New","Rework":f"{prefix}_Rework","OBA":f"{prefix}_OBA"})

    test_pivot = pivot_and_rename(df, "T")
    passed_pivot = pivot_and_rename(df[df["aging_result"]=="Passed"], "P")
    failed_pivot = pivot_and_rename(df[df["aging_result"]=="Failed"], "F")

    summary = test_pivot.merge(passed_pivot, on=["batch_id","date","time_start","time_end","pc","rack","order_id"], how="left") \
                        .merge(failed_pivot, on=["batch_id","date","time_start","time_end","pc","rack","order_id"], how="left") \
                        .fillna(0)

    summary["Time Start"] = summary["time_start"].dt.strftime("%H:%M")
    summary["Time End"] = summary["time_end"].dt.strftime("%H:%M")
    summary["order_id"] = summary["order_id"].str[-4:]

    summary_dis = summary[
        ["batch_id","date","Time Start","Time End","pc","rack","order_id",
         "T_New","T_Rework","T_OBA",
         "P_New","P_Rework","P_OBA",
         "F_New","F_Rework","F_OBA"]
    ]

    summary_dis.columns = pd.MultiIndex.from_tuples([
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

    def color_status(val):
        if val == "Fresh":
            return "background-color: lightgreen"
        elif val == "Rework":
            return "background-color: lightcoral"
        elif val == "OBA":
            return "background-color: lightblue"
        return ""

    st.subheader("Rack Summary Table")
    st.dataframe(summary_dis, width="stretch")

    st.subheader("All Scan Records")
    st.dataframe(df.style.map(color_status, subset=["fg_status"]))

def cancel_batch():
    st.session_state.unsent_sn = []

    st.session_state.order_id = ""
    st.session_state.fg_sn = ""
    st.session_state.selected_rack = "R1"
    st.session_state.confirm_cancel = False

    st.warning("Batch cancelled. All temporary scanned SN cleared.")

    st.rerun()