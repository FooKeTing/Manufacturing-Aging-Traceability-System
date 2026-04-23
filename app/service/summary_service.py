import pandas as pd

def build_summary(df):

    df["fg_status"] = df["fg_status"].astype(str).str.strip().str.title()

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

        pivot.columns = [
            col if isinstance(col, str) else col
            for col in pivot.columns
        ]

        for col in ["Fresh","Rework","OBA"]:
            if col not in pivot.columns:
                pivot[col] = 0

        return pivot.rename(columns={
            "Fresh": f"{prefix}_New",
            "Rework": f"{prefix}_Rework",
            "OBA": f"{prefix}_OBA"
        })

    test_pivot = pivot_and_rename(df, "T")
    passed_pivot = pivot_and_rename(df[df["aging_result"]=="Passed"], "P")
    failed_pivot = pivot_and_rename(df[df["aging_result"]=="Failed"], "F")

    summary = test_pivot.merge(
        passed_pivot,
        on=["batch_id","date","time_start","time_end","pc","rack","order_id"],
        how="left"
    ).merge(
        failed_pivot,
        on=["batch_id","date","time_start","time_end","pc","rack","order_id"],
        how="left"
    ).fillna(0)

    summary["Time Start"] = summary["time_start"].dt.strftime("%H:%M")
    summary["Time End"] = summary["time_end"].dt.strftime("%H:%M")
    summary["order_id"] = summary["order_id"].astype(str).str[-4:]

    return summary

def get_scan_summary_data(conn, order_id=None):
    if order_id:
        df = pd.read_sql_query(
            "SELECT * FROM unit_records WHERE order_id = ?",
            conn,
            params=(order_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM unit_records", conn)

    if df.empty:
        return df, None

    df["time_start"] = pd.to_datetime(df["time_start"])
    df["time_end"] = pd.to_datetime(df["time_end"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%d/%m/%Y")
    df["aging_result"] = df["aging_result"].fillna("NULL")

    return df, build_summary(df)

def colour_status(val):
    return {
        "Fresh": "background-color: lightgreen",
        "Rework": "background-color: lightcoral",
        "OBA": "background-color: lightblue"
    }.get(val, "")

