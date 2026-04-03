import sqlite3
import streamlit as st
from datetime import datetime
import os
import pandas as pd
import glob
import zipfile
import re
import xlwings as xw
import time
from config import MAX_PER_RACK, RACK_PC, RACK_LIST, BASE_PATH_TRACE, SHARED_PATH, TRACE_DB_NAME, ERROR_CODE_DESC, ERROR_OPTIONS 
from db import init_db, get_connection

init_db()

if "unsent_sn" not in st.session_state:
    st.session_state.unsent_sn = []

if "order_id" not in st.session_state:
    st.session_state.order_id = ""

if "selected_rack" not in st.session_state:
    st.session_state.selected_rack = "R1"

if "confirm_cancel" not in st.session_state:
    st.session_state.confirm_cancel = False

if "manual_success_msg" not in st.session_state:
    st.session_state.manual_success_msg = None

if "manual_fg_sn" not in st.session_state:
    st.session_state.manual_fg_sn = ""

if "manual_error" not in st.session_state:
    st.session_state.manual_error = ""

if "manual_custom_error" not in st.session_state:
    st.session_state.manual_custom_error = ""

if "clear_manual_inputs" not in st.session_state:
    st.session_state.clear_manual_inputs = False

if "auto_process_running" not in st.session_state:
    st.session_state.auto_process_running = False

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

def process_passed_results(order_id, batch_id, result_folder):
    batch_start, batch_end, date_start, date_end = get_batch_time_range(batch_id)

    if not batch_start or not batch_end:
        st.error("Batch time range not found.")
        return

    pass_count = 0
    fail_count = 0

    conn = get_connection()
    cursor = conn.cursor()

    passstatus, message, filesA, filesB = check_pass_files(result_folder, date_start, date_end)
    if not passstatus:
        return pass_count, fail_count, {}, message

    st.success("✅ Aging files detected!")
    agingA_df = pd.concat(
        [pd.read_excel(f)[["IP","Main board SN"]] for f in filesA],
        ignore_index=True
    )
    agingB_df = pd.concat(
        [pd.read_excel(f)[["IP","Main board SN"]] for f in filesB],
        ignore_index=True
    )

    if agingA_df.shape[1] < 2:
        st.error("Aging file A missing CB column")
        return
    if agingB_df.shape[1] < 2:
        st.error("Aging file B missing CB column")
        return

    aging_df = pd.concat([agingA_df, agingB_df], ignore_index=True)

    ip_col = aging_df.iloc[:,0].astype(str).str.strip()
    cb_col = aging_df.iloc[:,1].astype(str).str.strip()

    ip_passed = dict(zip(cb_col, ip_col))

    passed_cb_set = set(cb_col)

    cursor.execute("""
        SELECT fg_sn, cb_sn FROM unit_records 
        WHERE batch_id = ?
        AND aging_result IS NULL
    """, (batch_id,))
    rows = cursor.fetchall()

    for fg_sn, cb_sn in rows:

        if cb_sn and cb_sn in ip_passed:
            ip_value = ip_passed[cb_sn]

            try:
                last_octet = int(ip_value.split(".")[-1])

                if 221 <= last_octet <= 226:
                    cursor.execute("""
                        UPDATE unit_records
                        SET fg_status = 'OBA'
                        WHERE fg_sn = ?
                        AND batch_id = ?
                        AND fg_status = 'Rework'
                    """, (fg_sn, batch_id))
            except:
                pass

        if not cb_sn:
            result = "Do not have CB record"
            fail_count +=1
        elif cb_sn in passed_cb_set:
            result = "Passed"
            pass_count +=1
        else:
            result = "Failed"
            fail_count +=1

        cursor.execute("""
            UPDATE unit_records
            SET aging_result = ?
            WHERE fg_sn = ?
            AND batch_id = ?
        """, (result, fg_sn, batch_id))

    conn.commit()
    st.success("✅ Aging results processed!")

def process_failed_result_details(order_id, batch_id, result_folder):
    batch_start, batch_end, date_start, date_end = get_batch_time_range(batch_id)

    if not batch_start or not batch_end:
        st.error("Batch time range not found.")
        return

    fail_count = get_fail_count(batch_id)

    conn = get_connection()
    cursor = conn.cursor()
    if fail_count > 0:
        cursor.execute("""
            SELECT cb_sn FROM unit_records
            WHERE batch_id = ?
            AND aging_result = 'Failed'
            AND cb_sn IS NOT NULL
        """, (batch_id,))
        failed_rows = cursor.fetchall()

        failed_hb_list = {}
        for (cb_sn,) in failed_rows:

            cb_sn = cb_sn.strip()
            pattern = os.path.join(result_folder, f"*{cb_sn}*.zip")
            zip_files = sorted(glob.glob(pattern), reverse=True)

            if not zip_files:
                st.warning(f"❌ ZIP not found for CB_SN: {cb_sn}")
                continue

            zip_path = zip_files[0]

            if not os.path.exists(zip_path):
                continue

            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for file_name in zip_ref.namelist():

                        if "history.log" in file_name:

                            with zip_ref.open(file_name) as log_file:
                                content = log_file.read().decode(errors="ignore")

                                error_code_match = re.search(r"Record error:\s*(\d{2})", content)
                                hb_sn1_match = re.search(r"Hash board 0:\s*(\S+)", content)
                                hb_sn2_match = re.search(r"Hash board 1:\s*(\S+)", content)
                                hb_sn3_match = re.search(r"Hash board 2:\s*(\S+)", content)
                                ip_address_match = re.search(r"Local IP addr:\s*(\d{2}\.\d{3}\.\d{2}\.\d{1,3})",content)
                            
                                error_code = error_code_match.group(1) if error_code_match else None
                                hb_sn1 = hb_sn1_match.group(1) if hb_sn1_match else None
                                hb_sn2 = hb_sn2_match.group(1) if hb_sn2_match else None
                                hb_sn3 = hb_sn3_match.group(1) if hb_sn3_match else None
                                ip_address = ip_address_match.group(1) if ip_address_match else None

                                failed_hb_list[cb_sn] = {
                                    "error_code": error_code,
                                    "hb_sn1": hb_sn1,
                                    "hb_sn2": hb_sn2,
                                    "hb_sn3": hb_sn3,
                                    "ip_address": ip_address
                                }

                                if error_code:
                                    error_desc = ERROR_CODE_DESC.get(str(error_code), f"Unknown Error ({error_code})")
                                    cursor.execute("""
                                        UPDATE unit_records
                                        SET error_code = ?,
                                            error_desc = ?
                                        WHERE cb_sn = ?
                                        AND batch_id = ?
                                    """, (error_code, error_desc, cb_sn, batch_id))

            except Exception as e:
                print(f"Error processing {cb_sn}: {e}")

        conn.commit()

    failstatus, message, filesErrExcel = check_fail_excel(result_folder, date_start, date_end)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cb_sn FROM unit_records
        WHERE batch_id = ?
        AND aging_result = 'Failed'
        AND error_code IS NULL
    """, (batch_id,))
    failed_code_null = cursor.fetchall()

    if fail_count > 0 and failstatus:
        st.success("✅ Aging error files detected!")

        err_excel_df = pd.concat(
            [pd.read_excel(f)[["IP","Status","Aging Error Code","Upload Data","Repower Test Result","Device Error Code","Main board SN","Board SN"]] for f in filesErrExcel],
            ignore_index=True
        )

        if err_excel_df.shape[1] < 8:
            st.error("Aging Error missing error record.")
            return

        ip_addr_excel_col = err_excel_df.columns[0]
        error_status_excel_col = err_excel_df.columns[1]
        error_aging_excel_col = err_excel_df.columns[2]
        error_upload_excel_col = err_excel_df.columns[3]
        error_repower_excel_col = err_excel_df.columns[4]
        error_device_excel_col = err_excel_df.columns[5]
        cb_sn_excel_col = err_excel_df.columns[6]
        hb_sn_excel_col = err_excel_df.columns[7]
    
        err_excel_df[cb_sn_excel_col] = err_excel_df[cb_sn_excel_col].fillna("").astype(str).str.strip()

        excel_lookup = err_excel_df.set_index(cb_sn_excel_col)

        trace_cb_dict, trace_psu_dict, trace_bin_dict = load_traceability_dict()

        failed_excel_list = {}
        for (cb_sn,) in failed_code_null:
        
            cb_sn_str = str(cb_sn).strip()

            if cb_sn_str not in excel_lookup.index:
                print("CB not found in excel:", cb_sn_str)
                continue

            row = excel_lookup.loc[cb_sn_str]

            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]

            ip_addr_excel_value = row[ip_addr_excel_col]
            hb_sn_excel_value = row[hb_sn_excel_col]

            hb_sn_excel_list = str(hb_sn_excel_value).split("|") if pd.notna(hb_sn_excel_value) else []

            hb_sn1_excel = hb_sn_excel_list[0] if len(hb_sn_excel_list) > 0 else None
            hb_sn2_excel = hb_sn_excel_list[1] if len(hb_sn_excel_list) > 1 else None
            hb_sn3_excel = hb_sn_excel_list[2] if len(hb_sn_excel_list) > 2 else None

            hb_bin_excel = get_hb_bin(
                [hb_sn1_excel, hb_sn2_excel, hb_sn3_excel],
                trace_bin_dict
            )

            error_status_excel = row[error_status_excel_col]
            error_aging_excel = row[error_aging_excel_col]
            error_upload_excel = row[error_upload_excel_col]
            error_repower_excel = row[error_repower_excel_col]
            error_device_excel = row[error_device_excel_col]

            error_value = None
            if pd.notna(error_status_excel) and error_status_excel != "Success":
                error_value = error_status_excel
            elif pd.notna(error_aging_excel) and error_aging_excel != "-":
                error_value = error_aging_excel
            elif pd.notna(error_upload_excel) and error_upload_excel != "-":
                error_value = error_upload_excel
            elif pd.notna(error_repower_excel) and error_repower_excel != "Repower test success" and error_repower_excel != "-":
                error_value = error_repower_excel
            elif pd.notna(error_device_excel) and error_device_excel != "-":
                error_value = error_device_excel

            if error_value:
                cursor.execute("""
                    UPDATE unit_records
                    SET error_desc = ?
                    WHERE cb_sn = ?
                    AND batch_id = ?
                """, (
                    error_value,
                    cb_sn,
                    batch_id
                ))

            failed_excel_list[cb_sn] = {
                "error_desc": error_value,
                "hb_sn1": hb_sn1_excel,
                "hb_sn2": hb_sn2_excel,
                "hb_sn3": hb_sn3_excel,
                "ip_address": ip_addr_excel_value,
                "hb_bin":hb_bin_excel
            }

        conn.commit()

    cursor.execute("""
        SELECT batch_id, date, fg_sn, cb_sn, error_desc
        FROM unit_records
        WHERE batch_id = ?
        AND aging_result = 'Failed'
    """,(batch_id,))
    failed_units = cursor.fetchall()

    trace_cb_dict, trace_psu_dict, trace_bin_dict = load_traceability_dict()

    for row in failed_units:
        batch_id, date, fg_sn, cb_sn, error = row
        
        hb_sn1 = hb_sn2 = hb_sn3 = ip_address = hb_bin = None

        if cb_sn in failed_hb_list:

            detail_ZIP = failed_hb_list.get(cb_sn,{})

            hb_sn1 = detail_ZIP.get("hb_sn1")
            hb_sn2 = detail_ZIP.get("hb_sn2")
            hb_sn3 = detail_ZIP.get("hb_sn3")
            ip_address = detail_ZIP.get("ip_address")
            hb_bin = get_hb_bin(
                [hb_sn1, hb_sn2, hb_sn3],
                trace_bin_dict
            )

        elif cb_sn in failed_excel_list:

            detail_excel = failed_excel_list.get(cb_sn,{})

            hb_sn1 = detail_excel.get("hb_sn1")
            hb_sn2 = detail_excel.get("hb_sn2")
            hb_sn3 = detail_excel.get("hb_sn3")
            ip_address = detail_excel.get("ip_address")
            hb_bin = detail_excel.get("hb_bin")

        reject_num = None
        action_finding = None
        root_cause = None
        troubleshooting_status = "Open"

        psu_sn = trace_psu_dict.get(fg_sn)

        cursor.execute("""
            SELECT COUNT(*)FROM troubleshooting_records
            WHERE fg_sn =?
        """,(fg_sn,))
        previous_fail_count = cursor.fetchone()[0]
        reject_num = previous_fail_count + 1

        cursor.execute("""
            INSERT INTO troubleshooting_records
            (batch_id, date, error, reject_num, hb_bin, fg_sn, hb_sn1, hb_sn2, hb_sn3, psu_sn, cb_sn, ip_addr, action_finding, root_cause, troubleshooting_status)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id, date, error, reject_num, hb_bin, fg_sn, hb_sn1, hb_sn2, hb_sn3, psu_sn, cb_sn, ip_address, action_finding, root_cause, troubleshooting_status
        ))

    conn.commit()

def auto_process_check():
    batch_id = get_latest_batch_id()
    batch_start, batch_end, date_start, date_end = get_batch_time_range(batch_id)

    if not st.session_state.get("auto_process_running"):
        return

    result_folder = st.session_state.get("current_batch_folder")
    order_id = st.session_state.order_id
    batch_id = get_latest_batch_id()

    if not result_folder:
        return

    passstatus, pass_msg, files, filesB = check_pass_files(result_folder, date_start, date_end)
    failstatus, fail_msg, filesErrExcel = check_fail_excel(result_folder, date_start, date_end)
    
    if passstatus:
        process_passed_results(order_id, batch_id, result_folder)
        if failstatus:
            st.success("✅ Processing completed!")
            process_failed_result_details(order_id, batch_id, result_folder)
            st.session_state.auto_process_running = False
        else:
            st.warning(f"⏳ {fail_msg}")
            st.info(f"Please put the result files into: {result_folder}")
            time.sleep(3)
            st.rerun()
    else:
        st.warning(f"⏳ {pass_msg}")
        st.info(f"Please put the result files into: {result_folder}")
        time.sleep(3)
        st.rerun()

def display_scan_summary(selected_rack):

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

def scan_fg_sn():
    fg_sn = st.session_state.fg_sn.strip()
    order_id = st.session_state.order_id.strip()
    rack = st.session_state.selected_rack
    pc = RACK_PC[rack]

    conn = get_connection()
    cursor = conn.cursor()

    if not warn_no_order_id(order_id):
        return

    if len(order_id) != 3:
        st.error("Order ID must be exactly 3 characters! Please reenter correct order ID.")
        return

    if not fg_sn:
        return

    if len(fg_sn) !=6:
        st.error("FG SN must be 6 characters! Please rescan the FG SN.")
        st.session_state.fg_sn = ""
        return

    current_count = len([
        x for x in st.session_state.unsent_sn 
        if x["rack"] == selected_rack
    ])
    
    if current_count >= MAX_PER_RACK:
        next_rack = get_next_rack(rack)

        if next_rack:
            st.warning(f"{rack} is Full. Auto switching to {next_rack}")
            st.session_state.selected_rack = next_rack
            rack = next_rack
            pc = RACK_PC[rack]
        else:
            st.error("All racks are full. Stop scanning in FG SN!")
            st.session_state.fg_sn = ""
            return

    in_session = any(x["fg_sn"] == fg_sn for x in st.session_state.unsent_sn)
    if in_session:
        st.warning(f"SN{fg_sn} is already scanned in this batch! Please check and rescan the unit!")
        st.session_state.fg_sn = ""
        return

    cursor.execute("SELECT 1 FROM unit_records WHERE fg_sn = ? AND order_id = ?",(fg_sn,order_id))
    in_db = cursor.fetchone() is not None
    conn.close()

    selected_type = st.session_state.get("fg_type", "Fresh")

    if selected_type == "OBA":
        fg_status = "OBA"
    elif in_db:
        fg_status = "Rework"
    else:
        fg_status = "Fresh"

    st.session_state.unsent_sn.append({
        "order_id": order_id,
        "rack":rack,
        "fg_sn":fg_sn,
        "fg_status": fg_status,
        "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pc":pc
        })

    st.session_state.fg_sn =""

def start_batch():
    conn = get_connection()
    cursor = conn.cursor()

    if not st.session_state.unsent_sn:
        st.error("No SNs scanned yet. Please scan FG SN!")
        return

    order_id = st.session_state.order_id.strip()
    if not warn_no_order_id(order_id):
        return

    last_batch = get_latest_batch_id()

    batch_id = last_batch + 1

    time_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_batch = datetime.now().strftime("%Y-%m-%d")

    for sn in st.session_state.unsent_sn:
        cursor.execute("""
            INSERT INTO unit_records
            (batch_id, date, time_start, pc, rack, order_id, fg_sn, fg_status, timestamp)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,(
            batch_id,
            date_batch,
            time_start,
            sn["pc"],
            sn["rack"],
            sn["order_id"],
            sn["fg_sn"],
            sn["fg_status"],
            sn["timestamp"],
            ))

    conn.commit()
    st.success(f"Batch {batch_id} started on {date_batch} at {time_start} with {len(st.session_state.unsent_sn)} SNs.")
    st.session_state.unsent_sn = []

    trace_cb_dict, trace_psu_dict, trace_bin_dict = load_traceability_dict()

    cursor.execute("""
        SELECT fg_sn FROM unit_records
        WHERE batch_id = ? 
        AND cb_sn IS NULL
    """, (batch_id,))
    rows = cursor.fetchall()

    linked_count = 0
    for (fg_sn,) in rows:
        if fg_sn in trace_cb_dict:
            cb_sn = trace_cb_dict[fg_sn]

            cursor.execute("""
                UPDATE unit_records
                SET cb_sn = ?
                WHERE fg_sn = ?
                AND batch_id = ?
            """, (cb_sn, fg_sn, batch_id))

            linked_count +=1
    conn.commit()
    conn.close()

def end_batch():
    conn = get_connection()
    cursor = conn.cursor()

    batch_id = get_latest_batch_id()
    if not batch_id:
        st.error("No batch exists for this Order ID.")
        return

    time_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE unit_records
        SET time_end = ?
        WHERE batch_id = ?
        AND time_end IS NULL
    """, (time_end, batch_id))
    conn.commit()
    conn.close()

    order_id = st.session_state.order_id.strip()

    result_folder = create_folder(order_id, time_end)

    if not result_folder:
        st.error("Failed to create result folder.")
        return

    st.session_state["current_batch_folder"] = result_folder

    st.session_state.auto_process_running = True

    st.success("📁 Folder created")
    st.info("🤖 Auto-processing started. Waiting for files...")

def cancel_batch():

    st.session_state.unsent_sn = []

    st.session_state.order_id = ""
    st.session_state.fg_sn = ""
    st.session_state.selected_rack = "R1"
    st.session_state.confirm_cancel = False

    st.warning("Batch cancelled. All temporary scanned SN cleared.")

    st.rerun()

multiPage = st.sidebar.selectbox(
    "Select Page",
    ["Scan FG SN","Manual Input Error Failed Unit"]
)
conn = get_connection()
cursor = conn.cursor()

if multiPage == "Scan FG SN":
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
        st.button("Start Batch (Record time start)", on_click=start_batch)

    with col2:
        st.button("End Batch (Record time end) & Create Folder", on_click=end_batch)

    with col3:
        if not st.session_state.confirm_cancel:
            if st.button("Cancel Batch ⚠️"):
                st.session_state.confirm_cancel = True

        else:
            st.warning("Are you sure you want to cancel this batch?")

            col_yes, col_no = st.columns(2)

            with col_yes:
                st.button("✅ Yes, Cancel", on_click=cancel_batch)

            with col_no:
                if st.button("❌ No"):
                    st.session_state.confirm_cancel = False

    display_scan_summary(st.session_state.selected_rack)
    auto_process_check()

elif multiPage == "Manual Input Error Failed Unit":
    st.title("Manual Input Error for Failed Unit")

    if st.session_state.manual_success_msg:
        st.success(st.session_state.manual_success_msg)
        st.session_state.manual_success_msg = None

    if st.session_state.clear_manual_inputs:
        st.session_state.manual_fg_sn = ""
        st.session_state.manual_error = ""
        st.session_state.manual_custom_error = ""
        st.session_state.clear_manual_inputs = False

    fg_sn_input = st.text_input(
        "Scan FG Serial Number",
        max_chars=6,
        placeholder="Scan or enter FG SN",
        key="manual_fg_sn"
    )

    if fg_sn_input:

        cursor.execute("""
            SELECT fg_sn FROM unit_records
            WHERE fg_sn = ?
            AND aging_result is NULL
            ORDER BY batch_id DESC
            LIMIT 1
        """, (fg_sn_input,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            st.error("FG SN not found in database.")
        else:
            fg_sn = result[0]
            aging_result = "Failed"
            
            st.info(f"FG SN: {fg_sn}")

            selected_error = st.selectbox(
                "Select Failure Reason",
                ERROR_OPTIONS,
                key="manual_error"
            )

            custom_error = None
            if selected_error == "Others":
                custom_error = st.text_input(
                    "Please enter failure reason",
                    placeholder="Enter custom failure reason",
                    key="manual_custom_error"
                )
                final_error_reason = custom_error if custom_error else "Failure under investigate"
            else:
                final_error_reason = selected_error


            if st.button("💾 Save Error Reason", key="save_error"):

                if not selected_error:
                    st.error("Please select a failure reason.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE unit_records
                        SET aging_result = ?,
                            error_desc = ?
                        WHERE fg_sn = ?
                        AND batch_id = (
                            SELECT MAX(batch_id) FROM unit_records WHERE fg_sn = ?
                        )
                    """, (aging_result, final_error_reason, fg_sn_input, fg_sn_input))

                    conn.commit()
                    conn.close()

                    st.session_state.manual_success_msg = f"Manual failure recorded for {fg_sn_input}"

                    st.session_state.clear_manual_inputs = True
                    st.rerun()