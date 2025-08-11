import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

def clean_pos_column(df):
    """Remove all numbers from the POS column of the input dataframe."""
    if "POS" in df.columns:
        df = df.copy()
        df["POS"] = df["POS"].str.replace(r"\d+", "", regex=True)
    return df

def get_sleeper_adp():
    url = "https://www.fantasypros.com/nfl/adp/overall.php"
    response = requests.get(url)
    if response.status_code != 200:
        return pd.DataFrame()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id": "data"})
    if not table:
        return pd.DataFrame()
    headers = [th.text.strip() for th in table.find("thead").find_all("th")]
    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cells = [td.text.strip() for td in tr.find_all("td")]
        if cells:
            rows.append(cells)
    df = pd.DataFrame(rows, columns=headers)
    # Only keep the Sleeper ADP column and relevant player info
    df = clean_pos_column(df)
    columns_to_keep = [col for col in ["Player Team (Bye)", "POS", "Team", "Sleeper"] if col in df.columns]
    return df[columns_to_keep] if columns_to_keep else pd.DataFrame()

def get_underdog_adp():
    url = "https://www.fantasypros.com/nfl/adp/best-ball-overall.php"
    response = requests.get(url)
    if response.status_code != 200:
        return pd.DataFrame()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id": "data"})
    if not table:
        return pd.DataFrame()
    headers = [th.text.strip() for th in table.find("thead").find_all("th")]
    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cells = [td.text.strip() for td in tr.find_all("td")]
        if cells:
            rows.append(cells)
    df = pd.DataFrame(rows, columns=headers)
    # Only keep the Underdog ADP column and relevant player info
    df = clean_pos_column(df)
    columns_to_keep = [col for col in ["Player Team (Bye)", "POS", "Underdog"] if col in df.columns]
    return df[columns_to_keep] if columns_to_keep else pd.DataFrame()

def join_adp_data():
    df_sleeper = get_sleeper_adp()
    df_underdog = get_underdog_adp()
    required_cols = ["Player Team (Bye)", "POS"]
    if not all(col in df_sleeper.columns for col in required_cols):
        st.error("Sleeper DataFrame is missing required columns.")
        return pd.DataFrame()
    if not all(col in df_underdog.columns for col in required_cols):
        st.error("Underdog DataFrame is missing required columns.")
        return pd.DataFrame()
    merged = pd.merge(
        df_sleeper,
        df_underdog,
        on=["Player Team (Bye)", "POS"],
        how="outer"
    )
    # Reorder columns
    columns_order = ["Player Team (Bye)", "POS", "Sleeper", "Underdog"]
    merged = merged[columns_order]
    return merged

def my_rankings_page():
    st.title("My Rankings")
    df = join_adp_data()
    if df.empty:
        st.error("No combined ADP data found. Check your internet connection or the page structure.")
        return
    df = df.reset_index(drop=True)
    df["My Ranking"] = df.index + 1
    st.write("You can drag and drop rows in the table below to change your rankings. Rankings will update automatically.")
    edited_df = st.experimental_data_editor(df, num_rows="dynamic")
    # Recalculate rankings based on new order
    edited_df["My Ranking"] = range(1, len(edited_df) + 1)
    st.dataframe(edited_df)

# Sidebar navigation
page = st.sidebar.selectbox("Select Page", ["ADP Comparison", "My Rankings"])
if page == "ADP Comparison":
    st.title("Sleeper & Underdog ADP Comparison")
    df = join_adp_data()
    if df.empty:
        st.error("No combined ADP data found. Check your internet connection or the page structure.")
    else:
        st.dataframe(df)
elif page == "My Rankings":
    my_rankings_page()
