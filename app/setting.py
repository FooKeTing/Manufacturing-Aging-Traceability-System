# ---------------------------------
# Configuration - modify if needed
# ---------------------------------
from pathlib import Path

# maximum number of units allowed in one rack
MAX_PER_RACK = 25

# map rack ID to pc number
RACK_PC = {
    "R1":1,
    "R2":1,
    "R3":2,
    "R4":3,
    "R5":3,
    "R6":4,
}
RACK_LIST = list(RACK_PC.keys())

# set parent folder that store traceability database
BASE_DIR = Path(__file__).resolve().parent.parent
BASE_PATH_TRACE = BASE_DIR / "DB"

# set parent folder that store result (sub-folder that result saved into it will be created by app)
SHARED_PATH = BASE_DIR / "sample_data"

# set specify folder path for database
DB_PATH = BASE_DIR / "DB" 

# file name that store traceability data
TRACE_DB_NAME = "Tracking Database.xlsx"

# database name that store data
DB_NAME = "AgingAutomation.db"

# dictionary mapping miner error codes to descriptions 
ERROR_CODE_DESC = {
    "1":"Main board not found SN(1)",
    "2": "Main board not found MAC(2)",
    "3":"Fan detect error(3)",
    "4":"PCB temperature sensor detect fail(4)",
    "5":"PCB temperature too high(5)",
    "6":"Board communication error(6)",
    "7":"Bin number mismatch(7)",
    "8":"Board detect error(8)",
    "9":"Board reset detect error(9)",
    "10":"Board not insert(10)",
    "11":"Board communication test error(11)",
    "12":"Board initialize fail(12)",
    "13":"Board frequency configure fail(13)",
    "14":"Board low hashrate(14)",
    "15":"Board communication error(15)",
    "16":"PSU detect fail(16)",
    "17":"PSU communication failure(17)",
    "18":"PSU voltage no output(18)",
    "19":"PSU overload(19)",
    "20":"PSU error detected(20)",
    "21":"PSU powerdown fail(21)",
    "22":"PSU set voltage fail(22)",
    }

# create option to allow selection 
ERROR_OPTIONS = [
    "",
    "Current MAC address repeat",
    "CB unknown",
    "Duplicate main control board SN",
    "Keep on rebooting",
    "Missed upgrade",
    "Repower test fail",
    "Unit cannot detect",
    "Unit connection failed ",
    "Unit burnt",
    "Unit no power",
    "Wrong order ID",
    "Others"
    ]