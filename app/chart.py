import numpy as np
import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from db import init_db, get_connection

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

    df['error_desc'] = df['error_desc'].fillna('Unknown Error')
    df.loc[df['error_desc'].str.strip() == '', 'error_desc'] = 'Unknown Error'

    return df

def show_error_table(df):
    if df.empty:
        st.warning("No failed units found for this batch.")
        return
    st.dataframe(df)

def show_error_bar_chart(df):
    if df.empty:
        st.warning("No failed units found for this batch.")
        return 

    fig, ax = plt.subplots() 
    ax.bar(df['error_desc'], df['count'], color='skyblue')
    ax.set_xticks(range(len(df['error_desc'])))
    ax.set_xticklabels(df['error_desc'], rotation=45, ha='right')
    ax.set_xlabel("Error")
    ax.set_ylabel("Number of Units")
    ax.set_title("S/N Count by Error")
    plt.tight_layout()

    st.pyplot(fig, width="content")

def show_error_pie_chart(df):
    if df.empty:
        st.warning("No failed units found for this batch.")
        return 

    top5 = df.head(5)
    fig, ax = plt.subplots()

    wedges, texts, autotexts = plt.pie(
        top5['count'], 
        labels=None,  
        autopct=lambda pct: func(pct, top5['count']),
        startangle=140,
        colors=plt.cm.Pastel1.colors
    )

    # add legend with error descriptions
    ax.legend(wedges, top5['error_desc'], title="Categorized Error", bbox_to_anchor=(1, 0.5), loc="center left")
    ax.set_title("Top 5 S/N Count by Error")
    st.pyplot(fig, width="content")
