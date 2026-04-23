def get_failed_cb_sn_no_error(conn, batch_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cb_sn FROM unit_records
        WHERE batch_id = ?
        AND aging_result = 'Failed'
        AND error_code IS NULL
    """, (batch_id,))

    return [r[0] for r in cursor.fetchall()]

