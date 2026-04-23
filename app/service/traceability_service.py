import logging
import xlwings as xw
import time
import pandas as pd
import os

from app.setting import BASE_PATH_TRACE, TRACE_DB_NAME

logger = logging.getLogger(__name__)

def refresh_traceability_excel(trace_file: str, timeout: int = 60) -> bool:
    app = None
    wb = None

    try:
        app = xw.App(visible=False)
        app.screen_updating = False
        app.display_alerts = False

        wb = app.books.open(trace_file)

        wb.api.RefreshAll()

        start_time = time.time()

        while wb.api.Application.CalculationState != 0:
            if time.time() - start_time > timeout:
                raise TimeoutError("Excel calculation took too long")
            time.sleep(1)

        wb.save()

        logger.info("Traceability Excel refreshed successfully.")
        return True

    except Exception as e:
        logger.exception(f"Traceability refresh failed: {e}")
        return False

    finally:
        try:
            if wb:
                wb.close()
        except Exception:
            pass

        try:
            if app:
                app.quit()
        except Exception:
            pass

def load_traceability(trace_file):
    try:
        trace_df = pd.read_excel(
            trace_file,
            sheet_name="FG Linking",
            usecols=[0, 1, 2],
            dtype=str,
            engine="openpyxl"
        )

        trace_bin_df = pd.read_excel(
            trace_file,
            sheet_name="HB SMT",
            usecols=[0, 5],
            dtype=str,
            engine="openpyxl"
        )

        return trace_df, trace_bin_df

    except FileNotFoundError:
        raise FileNotFoundError(f"Traceability file not found: {trace_file}")

    except ValueError as e:
        raise ValueError(f"Excel structure error in traceability file: {e}")

    except Exception as e:
        raise RuntimeError(f"Unexpected error loading traceability: {e}")

def validate_traceability(trace_df, trace_bin_df):
    if trace_df.shape[1] < 3:
        raise ValueError(
            "Traceability file missing fg sn / cb sn / type columns"
        )

    if trace_bin_df.shape[1] < 2:
        raise ValueError(
            "Traceability file missing hb sn / hb bin columns"
        )

def build_trace_dicts(trace_df, trace_bin_df):
    trace_df = trace_df.copy()
    trace_bin_df = trace_bin_df.copy()

    trace_df.columns = trace_df.columns.str.strip()
    trace_bin_df.columns = ["BIN", "SN"]

    fg_col, pcba_col, type_col = trace_df.columns[:3]
    trace_bin_df["SN"] = trace_bin_df["SN"].astype(str).str.strip().str.upper()
    trace_bin_df["BIN"] = trace_bin_df["BIN"].astype(str).str.strip()

    trace_cb = trace_df[trace_df[type_col] == "CBLM"]
    trace_psu = trace_df[trace_df[type_col] == "PS"]

    trace_cb_dict = dict(zip(
        trace_cb[fg_col].astype(str),
        trace_cb[pcba_col].astype(str)
    ))

    trace_psu_dict = dict(zip(
        trace_psu[fg_col].astype(str),
        trace_psu[pcba_col].astype(str)
    ))

    trace_bin_dict = dict(zip(trace_bin_df["SN"], trace_bin_df["BIN"]))

    return trace_cb_dict, trace_psu_dict, trace_bin_dict

def load_traceability_dict():
    trace_file = os.path.join(BASE_PATH_TRACE, TRACE_DB_NAME)

    refresh_traceability_excel(trace_file)  

    trace_df, trace_bin_df = load_traceability(trace_file)

    validate_traceability(trace_df, trace_bin_df)

    return build_trace_dicts(trace_df, trace_bin_df)

def get_hb_bin(hb_sn_list, trace_bin_dict):
    bins = []

    for sn in hb_sn_list:
        if not sn:
            continue

        sn_key = str(sn).strip()

        bin_value = trace_bin_dict.get(sn_key)
        if bin_value is not None:
            bins.append(bin_value)

    if not bins:
        return None

    unique_bins = set(bins)

    if len(unique_bins) == 1:
        return bins[0]

    return "MIXED"

