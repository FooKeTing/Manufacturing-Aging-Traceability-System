import logging
import pandas as pd

from app.service.traceability_service import get_hb_bin, load_traceability_dict
from app.service.batch_service import get_batch_time_range
from app.service.aging_service import get_fail_count
from app.service.failure_zip_service import process_zip_failures
from app.service.failure_excel_service import check_fail_excel, process_excel_failures

logger = logging.getLogger(__name__)

def load_reject_map(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fg_sn, COUNT(*)
        FROM troubleshooting_records
        GROUP BY fg_sn
    """)

    return {r[0]: r[1] for r in cursor.fetchall()}

def load_order_map(conn, batch_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fg_sn, order_id
        FROM unit_records
        WHERE batch_id = ?
    """, (batch_id,))

    return {r[0]: r[1] for r in cursor.fetchall()}

def load_failed_units(conn, batch_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT batch_id, date, fg_sn, cb_sn, error_desc
        FROM unit_records
        WHERE batch_id = ?
        AND aging_result = 'Failed'
    """, (batch_id,))

    return cursor.fetchall()

def build_troubleshooting_inserts(failed_units,failed_hb_list, failed_excel_list, order_map, reject_map, trace_psu_dict,  trace_bin_dict):
    inserts = []

    for row in failed_units:
        batch_id, date, fg_sn, cb_sn, error = row

        hb_sn1 = hb_sn2 = hb_sn3 = ip_address = hb_bin = None

        # --- ZIP source ---
        if cb_sn in failed_hb_list:
            d = failed_hb_list[cb_sn]
            hb_sn1 = d.get("hb_sn1")
            hb_sn2 = d.get("hb_sn2")
            hb_sn3 = d.get("hb_sn3")
            ip_address = d.get("ip_address")

            hb_bin = get_hb_bin([hb_sn1, hb_sn2, hb_sn3], trace_bin_dict)
            
        # --- Excel source ---
        elif cb_sn in failed_excel_list:
            d = failed_excel_list[cb_sn]
            hb_sn1 = d.get("hb_sn1")
            hb_sn2 = d.get("hb_sn2")
            hb_sn3 = d.get("hb_sn3")
            ip_address = d.get("ip_address")
            hb_bin = d.get("hb_bin")

        order_id_value = order_map.get(fg_sn)
        psu_sn = trace_psu_dict.get(fg_sn)

        reject_num = reject_map.get(fg_sn, 0) + 1

        inserts.append((
            batch_id,
            order_id_value,
            date,
            error,
            reject_num,
            hb_bin,
            fg_sn,
            hb_sn1,
            hb_sn2,
            hb_sn3,
            psu_sn,
            cb_sn,
            ip_address,
            None,   # action_finding
            None,   # root_cause
            "Open"  # status
        ))

    return inserts

def insert_troubleshooting(cursor, inserts):
    if not inserts:
        return 0

    cursor.executemany("""
        INSERT INTO troubleshooting_records
        (batch_id, order_id, date, error, reject_num, hb_bin,
         fg_sn, hb_sn1, hb_sn2, hb_sn3, psu_sn,
         cb_sn, ip_addr, action_finding, root_cause, troubleshooting_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, inserts)

    return len(inserts)

def process_failed_result_details(conn, order_id, batch_id, result_folder):
    batch_start, batch_end, date_start, date_end = get_batch_time_range(conn, batch_id)

    if not batch_start or not batch_end:
        return False, "Batch time range not found."

    fail_count = get_fail_count(conn, batch_id)
    
    trace_cb_dict, trace_psu_dict, trace_bin_dict = load_traceability_dict()

    cursor = conn.cursor()

    try:
        reject_map = load_reject_map(conn)
        order_map = load_order_map(conn, batch_id)

        failed_hb_list = process_zip_failures(conn, batch_id, result_folder, fail_count)

        failstatus, message, filesErrExcel = check_fail_excel(
            result_folder, date_start, date_end
        )

        failed_excel_list = process_excel_failures(conn, batch_id, fail_count, failstatus, filesErrExcel)

        conn.commit()

        failed_units = load_failed_units(conn, batch_id)

        inserts = build_troubleshooting_inserts(
            failed_units,
            failed_hb_list,
            failed_excel_list,
            order_map,
            reject_map, 
            trace_psu_dict,
            trace_bin_dict
        )

        if inserts:
            insert_troubleshooting(cursor, inserts)
            conn.commit()

        return True, "Success"

    except Exception as e:
        conn.rollback()
        logger.exception("process_failed_result_details failed")
        return False, str(e)

def process_manual_failed_unit(conn, fg_sn_input):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fg_sn,batch_id FROM unit_records
        WHERE fg_sn = ?
        ORDER BY batch_id DESC
        LIMIT 1
    """, (fg_sn_input,))

    result = cursor.fetchone()

    if not result:
        return {"status": "not_found"}

    return {
        "status": "found",
        "fg_sn": result[0],
        "batch_id": result[1]
    }

def save_manual_failure(conn, fg_sn_input, final_error_reason):
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE unit_records
        SET aging_result = ?,
            error_desc = ?
        WHERE fg_sn = ?
        AND batch_id = (
            SELECT MAX(batch_id) FROM unit_records WHERE fg_sn = ?
        )
    """, ("Failed", final_error_reason, fg_sn_input, fg_sn_input))

    conn.commit()

def get_troubleshooting_data(conn):

    df = pd.read_sql_query("""
        SELECT * 
        FROM troubleshooting_records 
        WHERE troubleshooting_status = "Open" 
           OR troubleshooting_status = "In Progress"
        ORDER BY batch_id DESC
    """, conn)

    return df

def update_troubleshooting(conn, batch_id, fg_sn, root_cause, status, action_finding):
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE troubleshooting_records
        SET root_cause = ?,
            troubleshooting_status = ?,
            action_finding = ?
        WHERE batch_id = ? AND fg_sn = ?
    """, (root_cause, status, action_finding, batch_id, fg_sn))

    conn.commit()

def get_all_troubleshooting(conn):
    return pd.read_sql_query("SELECT * FROM troubleshooting_records", conn)