import glob
import os
import pandas as pd

from app.service.traceability_service import get_hb_bin, load_traceability_dict
from app.service.common_service import get_failed_cb_sn_no_error

def check_fail_excel(result_folder, date_start, date_end):
    all_files = glob.glob(os.path.join(result_folder, "*.xlsx"))
    files_err_excel = []

    for f in all_files:
        fname = os.path.basename(f).lower()

        if "error" not in fname:
            continue

        parts = fname.replace(".xlsx", "").split("_")

        if len(parts) < 2:
            continue

        file_date = parts[0]

        if file_date in (date_start, date_end):
            files_err_excel.append(f)

    if not files_err_excel:
        return False, "Waiting Aging Error...", []

    return True, "Aging Error files are ready.", files_err_excel

def load_excel_dataframe(filesErrExcel):
    return pd.concat(
        [pd.read_excel(f) for f in filesErrExcel],
        ignore_index=True
    )

def build_excel_lookup(df):
    df = df.copy()

    df["Main board SN"] = df["Main board SN"].fillna("").astype(str).str.strip()

    return df.set_index("Main board SN")

def pick_error(row):
    if pd.notna(row["Status"]) and row["Status"] != "Success":
        return row["Status"]

    if pd.notna(row["Aging Error Code"]) and row["Aging Error Code"] != "-":
        return row["Aging Error Code"]

    if pd.notna(row["Upload Data"]) and row["Upload Data"] != "-":
        return row["Upload Data"]

    if pd.notna(row["Repower Test Result"]) and row["Repower Test Result"] not in ["Repower test success", "-"]:
        return row["Repower Test Result"]

    if pd.notna(row["Device Error Code"]) and row["Device Error Code"] != "-":
        return row["Device Error Code"]

    return None

def parse_excel_row(row, trace_bin_dict):
    hb_list = str(row["Board SN"]).split("|") if pd.notna(row["Board SN"]) else []

    hb_sn1 = hb_list[0] if len(hb_list) > 0 else None
    hb_sn2 = hb_list[1] if len(hb_list) > 1 else None
    hb_sn3 = hb_list[2] if len(hb_list) > 2 else None

    hb_bin = get_hb_bin([hb_sn1, hb_sn2, hb_sn3], trace_bin_dict)
    error_value = pick_error(row)

    return {
        "error_desc": error_value,
        "hb_sn1": hb_sn1,
        "hb_sn2": hb_sn2,
        "hb_sn3": hb_sn3,
        "ip_address": row.get("IP"),
        "hb_bin": hb_bin
    }

def update_excel_error(cursor, cb_sn, batch_id, error_value):
    cursor.execute("""
        UPDATE unit_records
        SET error_desc = ?
        WHERE cb_sn = ?
        AND batch_id = ?
    """, (error_value, cb_sn, batch_id))

def process_excel_matches(cb_sn_list, excel_lookup, trace_bin_dict, cursor, batch_id):
    failed_excel_list = {}

    for cb_sn in cb_sn_list:
        cb_sn = str(cb_sn).strip()

        if cb_sn not in excel_lookup.index:
            continue

        row = excel_lookup.loc[cb_sn]

        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]

        parsed = parse_excel_row(row, trace_bin_dict)

        if parsed["error_desc"]:
            update_excel_error(cursor, cb_sn, batch_id, parsed["error_desc"])

        failed_excel_list[cb_sn] = parsed

    return failed_excel_list

def process_excel_failures(conn, batch_id, fail_count, failstatus, filesErrExcel):
    if fail_count <= 0 or not failstatus:
        return {}

    failed_code_null = get_failed_cb_sn_no_error(conn, batch_id)

    df = load_excel_dataframe(filesErrExcel)

    excel_lookup = build_excel_lookup(df)

    trace_cb_dict, trace_psu_dict, trace_bin_dict = load_traceability_dict()

    cursor = conn.cursor()

    return process_excel_matches(
        failed_code_null,
        excel_lookup,
        trace_bin_dict,
        cursor,
        batch_id
    )


