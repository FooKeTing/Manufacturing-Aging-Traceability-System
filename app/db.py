# -----------------------------
# DATABASE SETUP
# -----------------------------
import sqlite3
import os 
from config import DB_PATH, DB_NAME

# ensure folder exists
os.makedirs(DB_PATH, exist_ok=True)

# full path to database
DB_PATH = os.path.join(DB_PATH, DB_NAME)

# connect to aging database
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;") 
    return conn

# create table to store scanned unit records if it does not exist
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # create table to store scanned unit records if it does not exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS unit_records(
        batch_id INTEGER NOT NULL,
        date TEXT,
        time_start TEXT,
        time_end TEXT,
        pc INTEGER NOT NULL,
        rack TEXT NOT NULL,
        order_id TEXT NOT NULL,
        fg_sn TEXT NOT NULL,
        cb_sn TEXT,
        fg_status TEXT NOT NULL,
        aging_result TEXT,
        error_code TEXT,
        error_desc TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    # create troubleshooting table to store failed unit investigation records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS troubleshooting_records(
        batch_id INTEGER,
        date TEXT,
        error TEXT,
        reject_num INTEGER,
        hb_bin TEXT,
        fg_sn TEXT,
        hb_sn1 TEXT,
        hb_sn2 TEXT,
        hb_sn3 TEXT,
        psu_sn TEXT,
        cb_sn TEXT,
        ip_addr TEXT,
        action_finding TEXT,
        root_cause TEXT,
        troubleshooting_status TEXT
    )
    """)
    # commit changes
    conn.commit()
    conn.close()