import numpy as np
import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from database import init_db, get_connection

def func(pct, allvalues):
    absolute = int(pct / 100.*np.sum(allvalues))
    return "{:.1f}%\n({:d})".format(pct, absolute)

def select_order():
    conn = get_connection()
    order_query = "SELECT DISTINCT order_id FROM unit_records ORDER BY order_id DESC"
    order_ids = [row[0] for row in conn.execute(order_query).fetchall()]
    conn.close()
    
    if not order_ids:
        st.warning("No orders found in the database.")
        return None
    return st.selectbox("Select Order ID", order_ids)

def get_yield_data(order_id):
    conn = get_connection()

    query_yield = """
        SELECT 
            batch_id,
            COUNT(*) as total,
            SUM(CASE WHEN aging_result = 'Failed' THEN 1 ELSE 0 END) as failed
        FROM unit_records
        WHERE order_id = ?
        AND fg_status = "Fresh"
        GROUP BY batch_id
        ORDER BY batch_id
    """

    df_yield = pd.read_sql_query(query_yield, conn, params=(order_id,))
    conn.close()

    df_yield["yield_loss"] = (df_yield["failed"] / df_yield["total"]) * 100

    return df_yield

def show_yield_table(df_yield):
    if df_yield.empty:
        st.warning("No data available for yield loss chart.")
        return
    st.dataframe(df_yield)

def show_yield_loss_chart(df_yield):
    fig, ax = plt.subplots()

    ax.plot(df_yield["batch_id"], df_yield["yield_loss"], marker='o')

    for i in range(len(df_yield)):
        ax.text(
            df_yield["batch_id"][i],
            df_yield["yield_loss"][i],
            f"{df_yield['yield_loss'][i]:.1f}%",
            ha='center',
            va='bottom'
        )
    
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    
    ax.set_title("Yield Loss (%) by Batch")
    ax.set_xlabel("Batch Number")
    ax.set_ylabel("Yield Loss (%)")

    st.pyplot(fig)

def get_error_data(order_id):
    conn = get_connection()
    
    query = """
        SELECT 
            COALESCE(error_desc, 'Unknown Error') AS error_desc,
            COUNT(*) as count
        FROM unit_records
        WHERE aging_result = 'Failed'
        AND order_id = ?
        AND fg_status = "Fresh"
        GROUP BY error_desc
        ORDER BY count DESC
    """

    df = pd.read_sql_query(query, conn, params=(order_id,))
    conn.close()

    return df

def show_error_table(df):
    if df.empty:
        st.warning("No failed units found for this order.")
        return
    st.dataframe(df)

def show_error_bar_chart(df):
    fig, ax = plt.subplots() 
    ax.bar(df['error_desc'], df['count'], color='skyblue')
    ax.set_xticks(range(len(df['error_desc'])))
    ax.set_xticklabels(df['error_desc'], rotation=45, ha='right')
    ax.set_xlabel("Error")
    ax.set_ylabel("Number of Units")
    ax.set_title("S/N Count by Error")
    plt.tight_layout()

    st.pyplot(fig, width = "stretch")

def show_error_pie_chart(df):
    top5 = df.head(5)
    fig, ax = plt.subplots()

    wedges, texts, autotexts = plt.pie(
        top5['count'], 
        labels=None,  
        autopct=lambda pct: func(pct, top5['count']),
        startangle=140,
        colors=plt.cm.Pastel1.colors
    )

    ax.legend(wedges, top5['error_desc'], title="Categorized Error", bbox_to_anchor=(1, 0.5), loc="center left")
    ax.set_title("Top 5 S/N Count by Error")

    st.pyplot(fig, width="content")

def get_root_cause_data(order_id):
    conn = get_connection()

    query = """
        SELECT 
            COALESCE(root_cause, 'Under Investigation') AS root_cause,
            COUNT(*) as count
        FROM troubleshooting_records
        WHERE order_id = ?
        AND troubleshooting_status IN ('Open', 'In Progress', 'Closed')
        AND reject_num = 1
        GROUP BY root_cause
        ORDER BY count DESC
    """

    df = pd.read_sql_query(query, conn, params=(order_id,))
    conn.close()

    return df

def show_root_cause_table(df):
    if df.empty:
        st.warning(f"No root cause data found this order.")
        return
    st.dataframe(df)

def show_root_cause_bar_chart(df):
    fig, ax = plt.subplots() 
    ax.bar(df['root_cause'], df['count'], color='skyblue')
    ax.set_xticks(range(len(df['root_cause'])))
    ax.set_xticklabels(df['root_cause'], rotation=45, ha='right')
    ax.set_xlabel("Root Cause")
    ax.set_ylabel("Number of Errors")
    ax.set_title("Error Count by Root Cause")
    plt.tight_layout()

    st.pyplot(fig, width = "stretch")

def show_root_cause_pie_chart(df):
    top5 = df.head(5)
    fig, ax = plt.subplots()

    wedges, texts, autotexts = plt.pie(
        top5['count'], 
        labels=None,  
        autopct=lambda pct: func(pct, top5['count']),
        startangle=140,
        colors=plt.cm.Pastel1.colors
    )

    ax.legend(wedges, top5['root_cause'], title="Root Cause", bbox_to_anchor=(1, 0.5), loc="center left")
    ax.set_title("Top 5 Root Causes")

    st.pyplot(fig, width="content")