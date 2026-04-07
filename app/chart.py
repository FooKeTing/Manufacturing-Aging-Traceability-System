import numpy as np
import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from db import init_db, get_connection

def func(pct, allvalues):
    absolute = int(pct / 100.*np.sum(allvalues))
    return "{:.1f}%\n({:d})".format(pct, absolute)

def show_error_bar():
    st.title("📊 First Failed Units by Error Description")

    conn = get_connection()
    order_query = "SELECT DISTINCT order_id FROM unit_records ORDER BY order_id DESC"
    order_ids = [row[0] for row in conn.execute(order_query).fetchall()]

    if not order_ids:
        st.warning("No orders found in the database.")
        return

    selected_order = st.selectbox("Select Order ID", order_ids)

    query = """
        SELECT error_desc, COUNT(*) as count
        FROM unit_records
        WHERE aging_result = 'Failed'
        AND order_id = ?
        AND fg_status = "Fresh"
        GROUP BY error_desc
        ORDER BY count DESC
    """
    df = pd.read_sql_query(query, conn, params=(selected_order,))
    df['error_desc'] = df['error_desc'].replace({'': 'Unknown Error', 'nan': 'Unknown Error'})
    conn.close()

    if df.empty:
        st.warning("No failed units found for this batch.")
    else:
        st.subheader(f"Order ID: {selected_order}")

        st.dataframe(df)

        # bar chart
        plt.figure(figsize=(10,5))
        plt.bar(df['error_desc'], df['count'], color='salmon')
        plt.xticks(rotation=45, ha='right')
        plt.xlabel("Error")
        plt.ylabel("Number of Units")
        plt.title("S/N Count by Error")
        plt.tight_layout()
        st.pyplot(plt)

        # top 5 pie chart
        top5 = df.head(5)
        plt.figure(figsize=(6,6))
        wedges, texts, autotexts = plt.pie(
            top5['count'], 
            labels=None,  
            autopct=lambda pct: func(pct, top5['count']),
            startangle=140,
            colors=plt.cm.Pastel1.colors
        )

        # Add legend with error descriptions
        plt.legend(wedges, top5['error_desc'], title="Categorized Error", bbox_to_anchor=(1, 0.5), loc="center left")
        plt.title("Top 5 S/N Count by Error")
        st.pyplot(plt)
