import logging
import glob
import os
import pandas as pd

from app.service.batch_service import get_latest_batch_id, get_pc_count, get_batch_time_range

logger = logging.getLogger(__name__)

def check_pass_files(conn, result_folder, date_start, date_end):
    batch_id = get_latest_batch_id(conn)
    pc_count = get_pc_count(conn, batch_id)

    all_files = glob.glob(os.path.join(result_folder, "*.xlsx"))

    filesA = []
    filesB = []

    for f in all_files:
        fname = os.path.basename(f).lower()

        if "result" not in fname:
            continue

        parts = fname.split("_")
        if len(parts) < 2:
            continue

        file_date = parts[0]

        if file_date not in (date_start, date_end):
            continue

        if "_a_" in fname:
            filesA.append(f)
        elif "_b_" in fname:
            filesB.append(f)

    if not filesA:
        return False, "Waiting Aging Result A...", [], []

    if len(filesA) < pc_count:
        return False, f"Insufficient files for Aging Result A... {pc_count} needed.", [], []

    if not filesB:
        return False, "Waiting Aging Result B...", [], []

    if len(filesB) < pc_count:
        return False, f"Insufficient files for Aging Result B... {pc_count} needed.", [], []

    return True, "Aging Result A and B are ready.", filesA, filesB

def prepare_aging_data(conn, result_folder, date_start, date_end):
    passstatus, message, filesA, filesB = check_pass_files(conn, result_folder, date_start, date_end)

    if not passstatus:
        return None, None, message

    try:
        agingA_df = pd.concat(
            [pd.read_excel(f)[["IP", "Main board SN"]] for f in filesA],
            ignore_index=True
        )

        agingB_df = pd.concat(
            [pd.read_excel(f)[["IP", "Main board SN"]] for f in filesB],
            ignore_index=True
        )

    except KeyError:
        return None, None, "Missing required columns: IP or Main board SN"

    except Exception as e:
        return None, None, f"Error reading Excel files: {str(e)}"

    if agingA_df.empty or agingB_df.empty:
        return None, None, "Aging files are empty"

    aging_df = pd.concat([agingA_df, agingB_df], ignore_index=True)

    aging_df = aging_df.dropna(subset=["IP", "Main board SN"])

    ip_col = aging_df["IP"].astype(str).str.strip()
    cb_col = aging_df["Main board SN"].astype(str).str.strip()

    ip_passed = dict(zip(cb_col, ip_col))
    passed_cb_set = set(cb_col)

    return ip_passed, passed_cb_set, None

def fetch_pending_units(conn, batch_id):
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT fg_sn, cb_sn 
            FROM unit_records 
            WHERE batch_id = ?
            AND aging_result IS NULL
        """, (batch_id,))

        return cursor.fetchall()

    except Exception as e:
        return []

def classify_result(cb_sn, passed_cb_set):
    if not cb_sn or cb_sn.strip() == "":
        return False, "Do not have CB record" 

    cb_sn = cb_sn.strip()

    if cb_sn in passed_cb_set:
        return True, "Passed"

    return False, "Failed"

def update_unit_record(conn, fg_sn, batch_id, result):
    cursor = conn.cursor()

    if not fg_sn or not batch_id:
        return

    cursor.execute("""
        UPDATE unit_records
        SET aging_result = ?
        WHERE fg_sn = ?
        AND batch_id = ?
    """, (result, fg_sn, batch_id))

    conn.commit()

def process_passed_results(conn, order_id, batch_id, result_folder):
    batch_start, batch_end, date_start, date_end = get_batch_time_range(conn, batch_id)

    if not batch_start or not batch_end:
        return False, False, "Batch time range not found."

    ip_passed, passed_cb_set, error = prepare_aging_data(conn, result_folder, date_start, date_end)

    if error:
        return False, False, error

    rows = fetch_pending_units(conn, batch_id)
    cursor = conn.cursor()

    pass_count = 0
    fail_count = 0

    for fg_sn, cb_sn in rows:

        is_pass, result = classify_result(cb_sn, passed_cb_set)

        if is_pass:
            pass_count += 1
        else:
            fail_count += 1

        update_unit_record(conn, fg_sn, batch_id, result)

        if cb_sn and cb_sn in ip_passed:
            ip = ip_passed[cb_sn]

            try:
                last_octet = int(ip.split(".")[-1])

                if 221 <= last_octet <= 226:
                    cursor.execute("""
                        UPDATE unit_records
                        SET fg_status = 'OBA'
                        WHERE fg_sn = ?
                        AND batch_id = ?
                        AND fg_status = 'Rework'
                    """, (fg_sn, batch_id))

            except ValueError:
                logger.warning(f"Invalid IP format: {ip}")

    conn.commit()

    return True, pass_count, fail_count

def get_fail_count(conn, batch_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM unit_records
        WHERE batch_id = ?
        AND aging_result = 'Failed'
    """, (batch_id,))
    fail_count = cursor.fetchone()[0]

    return fail_count

