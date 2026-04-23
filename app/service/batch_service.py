from datetime import datetime
import os

from app.setting import RACK_LIST, MAX_PER_RACK, RACK_PC, SHARED_PATH
from app.service.traceability_service import load_traceability_dict

def validate_order_id(order_id):
    if not order_id:
        return False, "Order ID is empty. Please enter Order ID!"

    if len(order_id) != 3:
        return False, "Order ID must be exactly 3 characters! Please reenter correct order ID."

    return True, None

def validate_fg_sn(fg_sn):
    if not fg_sn:
        return False, "FG SN is empty. Please enter/scan FG SN!"

    if len(fg_sn) != 6:
        return False, "FG SN must be exactly 6 characters! Please rescan correct FG SN."

    return True, None

def get_next_rack(selected_rack):
    if selected_rack in RACK_LIST:
        idx = RACK_LIST.index(selected_rack)
        if idx + 1 < len(RACK_LIST):
            return RACK_LIST[idx+1]
    return None

def scan_fg_sn_logic(conn, fg_sn, order_id, rack, fg_type, unsent_sn):
    fg_sn = fg_sn.strip()
    order_id = order_id.strip()

    status, msg = validate_order_id(order_id)
    if status == False:
        return {"status": "error", "message": msg}

    status, msg = validate_fg_sn(fg_sn)
    if status == False:
        return {"status": "error", "message": msg}

    current_count = len([x for x in unsent_sn if x["rack"] == rack])

    if current_count >= MAX_PER_RACK:
        next_rack = get_next_rack(rack)
        if not next_rack:
            return {"status": "error", "message": "All racks are full. Stop scanning in FG SN!"}
        rack = next_rack

    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM unit_records WHERE fg_sn = ? AND order_id = ?",
        (fg_sn, order_id)
    )
    in_db = cursor.fetchone() is not None

    if fg_type == "OBA":
        fg_status = "OBA"
    elif in_db:
        fg_status = "Rework"
    else:
        fg_status = "Fresh"

    return {
        "status": "ok",
        "data": {
            "order_id": order_id,
            "rack": rack,
            "fg_sn": fg_sn,
            "fg_status": fg_status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pc": RACK_PC[rack]
        }
    }

def get_latest_batch_id(conn):
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(batch_id) FROM unit_records")
    result = cursor.fetchone()[0]

    return result if result else 0

def start_batch_logic(conn, order_id, unsent_sn):
    cursor = conn.cursor()

    try:
        if not unsent_sn:
            return False, "No SNs scanned"

        status, msg = validate_order_id(order_id)
        if not status:
            return False, msg

        batch_id = get_latest_batch_id(conn) + 1

        now = datetime.now()
        time_start = now.strftime("%Y-%m-%d %H:%M:%S")
        date_batch = now.strftime("%Y-%m-%d")

        for sn in unsent_sn:
            cursor.execute("""
                INSERT INTO unit_records
                (batch_id, date, time_start, pc, rack, order_id, fg_sn, fg_status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                date_batch,
                time_start,
                sn["pc"],
                sn["rack"],
                order_id,
                sn["fg_sn"],
                sn["fg_status"],
                sn["timestamp"],
            ))

        conn.commit()

        trace_cb_dict, _, _ = load_traceability_dict()

        cursor.execute("""
            SELECT fg_sn FROM unit_records
            WHERE batch_id = ? AND cb_sn IS NULL
        """, (batch_id,))

        for (fg_sn,) in cursor.fetchall():
            cb_sn = trace_cb_dict.get(fg_sn)

            if cb_sn:
                cursor.execute("""
                    UPDATE unit_records
                    SET cb_sn = ?
                    WHERE fg_sn = ? AND batch_id = ?
                """, (cb_sn, fg_sn, batch_id))

        conn.commit()

        return True, batch_id

    except Exception as e:
        conn.rollback()
        return False, str(e)

def end_batch_logic(conn, batch_id):
    cursor = conn.cursor()

    if not batch_id:
        return False, "No batch exists."

    time_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE unit_records
        SET time_end = ?
        WHERE batch_id = ?
        AND time_end IS NULL
    """, (time_end, batch_id))

    return True, time_end

def create_folder(order_id, time_end_str):
    try:
        time_end_dt = datetime.strptime(time_end_str, "%Y-%m-%d %H:%M:%S")
        folder_name = time_end_dt.strftime("%y%m%d_%H%M")

        full_path = os.path.join(SHARED_PATH, order_id, folder_name)

        os.makedirs(full_path, exist_ok=True)

        return True, full_path

    except Exception as e:
        return False, f"Error creating folder:{e}"

def get_batch_time_range(conn, batch_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT time_start, time_end
        FROM unit_records
        WHERE batch_id = ?
        LIMIT 1
    """, (batch_id,))

    row = cursor.fetchone()

    if not row or not row[0] or not row[1]:
        return None, None, None, None

    batch_start = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    batch_end = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")

    date_start = batch_start.strftime("%y%m%d")
    date_end = batch_end.strftime("%y%m%d")

    return batch_start, batch_end, date_start, date_end

def get_pc_count(conn, batch_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(DISTINCT pc)
        FROM unit_records
        WHERE batch_id = ?
    """, (batch_id,))

    result = cursor.fetchone()[0]

    return result if result else 0
