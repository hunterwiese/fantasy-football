import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

def clean_pos_column(df):
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
    df = clean_pos_column(df)
    columns_to_keep = [col for col in ["Player Team (Bye)", "POS", "Underdog"] if col in df.columns]
    return df[columns_to_keep] if columns_to_keep else pd.DataFrame()

def join_adp_data(platform):
    df_sleeper = get_sleeper_adp()
    df_underdog = get_underdog_adp()
    required_cols = ["Player Team (Bye)", "POS"]
    if not all(col in df_sleeper.columns for col in required_cols):
        return pd.DataFrame()
    if not all(col in df_underdog.columns for col in required_cols):
        return pd.DataFrame()
    merged = pd.merge(
        df_sleeper,
        df_underdog,
        on=["Player Team (Bye)", "POS"],
        how="outer"
    )
    # Choose ADP column based on platform
    if platform == "sleeper":
        merged["ADP"] = merged["Sleeper"]
    else:
        merged["ADP"] = merged["Underdog"]
    columns_order = ["Player Team (Bye)", "POS", "ADP"]
    merged = merged[columns_order]
    return merged

def load_rankings(platform):
    filename = "my_rankings.csv"
    adp_df = join_adp_data(platform).reset_index(drop=True)
    if os.path.exists(filename):
        try:
            # Load only order columns
            order_df = pd.read_csv(filename)
            # Merge with current ADP data
            merged = order_df.merge(adp_df[["Player Team (Bye)", "POS", "ADP"]], on=["Player Team (Bye)", "POS"], how="left")
            merged["My Ranking"] = range(1, len(merged) + 1)
            return merged
        except Exception:
            pass
    # If no saved order, use ADP order
    adp_df["My Ranking"] = adp_df.index + 1
    return adp_df
def add_pos_rank(df):
    pos_ranks = []
    for i, row in df.iterrows():
        pos = row["POS"]
        my_rank = row["My Ranking"]
        y = (df[(df["POS"] == pos) & (df["My Ranking"] < my_rank)]).shape[0] + 1
        pos_ranks.append(f"{pos}{y}")
    df["POS Rank"] = pos_ranks
    return df

def add_diff(df):
    df["ADP_num"] = df["ADP"].apply(safe_float)
    df["Diff"] = df["My Ranking"] - df["ADP_num"]
    return df

def color_for_diff(diff, maxDiff=15):
    color = "#fff"
    if diff is not None:
        try:
            diff = float(diff)
            norm = max(-maxDiff, min(maxDiff, diff))
            if norm < 0:
                pct = abs(norm) / maxDiff
                r = round(255 - 155 * pct)
                g = 255
                b = round(255 - 155 * pct)
                color = f"rgb({r},{g},{b})"
            elif norm > 0:
                pct = norm / maxDiff
                r = 255
                g = round(255 - 155 * pct)
                b = round(255 - 155 * pct)
                color = f"rgb({r},{g},{b})"
        except:
            color = "#fff"
    return color

def make_table_html(df, columns, table_id=None, color_diff=False):
    table_html = "<table"
    if table_id:
        table_html += f' id="{table_id}"'
    table_html += "><thead><tr>"
    for col in columns:
        table_html += f"<th>{col}</th>"
    table_html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        table_html += "<tr>"
        for col in columns:
            if color_diff and col == "Diff":
                color = color_for_diff(row.get(col, None))
                table_html += f"<td style='background:{color};'>{row.get(col, '')}</td>"
            else:
                table_html += f"<td>{row.get(col, '')}</td>"
        table_html += "</tr>"
    table_html += "</tbody></table>"
    return table_html

def safe_float(val):
    try:
        return float(val)
    except:
        return None
