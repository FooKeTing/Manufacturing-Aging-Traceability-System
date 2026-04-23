import os
import glob
import re
import zipfile

from app.setting import ERROR_CODE_DESC

def get_failed_cb_sn(conn, batch_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cb_sn FROM unit_records
        WHERE batch_id = ?
        AND aging_result = 'Failed'
        AND cb_sn IS NOT NULL
    """, (batch_id,))

    return [r[0].strip() for r in cursor.fetchall()]

def find_latest_zip(cb_sn, result_folder):
    pattern = os.path.join(result_folder, f"*{cb_sn}*.zip")
    zip_files = sorted(glob.glob(pattern), reverse=True)

    if not zip_files:
        return None

    return zip_files[0] if os.path.exists(zip_files[0]) else None

def parse_history_log(content):
    error_code_match = re.search(r"Record error:\s*(\d{1,2})", content)
    error_code = error_code_match.group(1) if error_code_match else None

    error_desc = ERROR_CODE_DESC.get(error_code) if error_code else None

    hb_sn1 = re.search(r"Hash board 0:\s*(\S+)", content)
    hb_sn2 = re.search(r"Hash board 1:\s*(\S+)", content)
    hb_sn3 = re.search(r"Hash board 2:\s*(\S+)", content)

    ip_match = re.search(r"Local IP addr:\s*(\d{2}\.\d{3}\.\d{1}\.\d{1,3})", content)

    return {
        "error_code": error_code,
        "error_desc": error_desc,

        "hb_sn1": hb_sn1.group(1) if hb_sn1 else None,
        "hb_sn2": hb_sn2.group(1) if hb_sn2 else None,
        "hb_sn3": hb_sn3.group(1) if hb_sn3 else None,

        "ip_address": ip_match.group(1) if ip_match else None,
    }

def process_single_zip(conn, cb_sn, result_folder, batch_id):
    cursor = conn.cursor()

    zip_path = find_latest_zip(cb_sn, result_folder)

    if not zip_path:
        return None

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_name in zip_ref.namelist():

                if "history.log" not in file_name:
                    continue

                with zip_ref.open(file_name) as log_file:
                    content = log_file.read().decode(errors="ignore")

                    parsed = parse_history_log(content)

                    cursor.execute("""
                        UPDATE unit_records
                        SET error_code = ?,
                            error_desc = ?
                        WHERE cb_sn = ?
                        AND batch_id = ?
                    """, (parsed["error_code"], parsed["error_desc"], cb_sn, batch_id))

                    return parsed

    except Exception as e:
        print(f"ZIP error {cb_sn}: {e}")

    return None

def process_zip_failures(conn, batch_id, result_folder, fail_count):
    cursor = conn.cursor()
    failed_hb_list = {}

    if fail_count <= 0:
        return failed_hb_list

    failed_rows = get_failed_cb_sn(conn, batch_id)

    for cb_sn in failed_rows:
        result = process_single_zip(conn, cb_sn, result_folder, batch_id)

        if result:
            failed_hb_list[cb_sn] = result

    return failed_hb_list

