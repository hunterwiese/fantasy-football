from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import pandas as pd
import os
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)
app.secret_key = 'fantasy-draft-secret-key'

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

def safe_float(val):
    try:
        return float(val)
    except:
        return None

@app.route('/', methods=['GET', 'POST'])
def home():
  platform = request.form.get('platform', 'sleeper')
  df = load_rankings(platform)
  df["ADP_num"] = df["ADP"].apply(safe_float)
  df["Diff"] = df["My Ranking"] - df["ADP_num"]
  # Add POS Rank column
  pos_ranks = []
  for i, row in df.iterrows():
    pos = row["POS"]
    my_rank = row["My Ranking"]
    y = (df[(df["POS"] == pos) & (df["My Ranking"] < my_rank)]).shape[0] + 1
    pos_ranks.append(f"{pos}{y}")
  df["POS Rank"] = pos_ranks

  table_html = "<table id='rankings-table'><thead><tr><th>My Ranking</th><th>Player Team (Bye)</th><th>POS</th><th>POS Rank</th><th>ADP</th><th>Diff</th></tr></thead><tbody>"
  for i, row in df.iterrows():
    diff = row["Diff"]
    color = "#fff"
    if diff is not None:
      try:
        diff = float(diff)
        maxDiff = 15
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
        else:
          color = "#fff"
      except:
        color = "#fff"
    table_html += f"<tr><td>{row['My Ranking']}</td><td>{row['Player Team (Bye)']}</td><td>{row['POS']}</td><td>{row['POS Rank']}</td><td>{row['ADP']}</td><td style='background:{color};'>{diff if diff is not None else ''}</td></tr>"
  table_html += "</tbody></table>"
  sortable_js = """
<link href='https://fonts.googleapis.com/css?family=Inter:400,600&display=swap' rel='stylesheet'>
<style>
  body {
    font-family: 'Inter', Arial, sans-serif;
    background: #f6f8fa;
    margin: 0;
    padding: 0;
  }
  .container {
    max-width: 900px;
    margin: 40px auto;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    padding: 32px 24px 24px 24px;
  }
  h1 {
    font-size: 2.2rem;
    font-weight: 600;
    margin-bottom: 18px;
    color: #222;
    letter-spacing: -1px;
  }
  form {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
  }
  label {
    font-weight: 600;
    color: #444;
    font-size: 1.05rem;
  }
  select {
    font-size: 1rem;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #d0d7de;
    background: #f6f8fa;
    color: #222;
    font-family: inherit;
    transition: border 0.2s;
  }
  select:focus {
    border-color: #0074d9;
    outline: none;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    font-size: 1rem;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }
  thead {
    background: #f0f4f8;
  }
  th, td {
    padding: 12px 10px;
    text-align: left;
  }
  th {
    font-weight: 600;
    color: #333;
    border-bottom: 2px solid #eaecef;
  }
  tr {
    transition: background 0.15s;
  }
  tbody tr:hover {
    background: #f6f8fa;
  }
  td {
    border-bottom: 1px solid #eaecef;
    color: #222;
  }
  td:last-child {
    font-weight: 600;
    text-align: center;
    border-left: 1px solid #eaecef;
  }
  @media (max-width: 700px) {
    .container {
      padding: 12px 4px;
    }
    table, thead, tbody, th, td, tr {
      font-size: 0.95rem;
    }
    th, td {
      padding: 8px 4px;
    }
  }
</style>
<script src='https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js'></script>
<script>
  const tbody = document.querySelector('#rankings-table tbody');
  function getTableData() {
    let data = [];
    Array.from(tbody.children).forEach(function(row, i) {
      data.push({
        "My Ranking": i + 1,
        "Player Team (Bye)": row.children[1].textContent,
        "POS": row.children[2].textContent,
        "ADP": row.children[3].textContent
      });
    });
    return data;
  }
  function saveRankings() {
    const platform = document.getElementById('platform').value;
    const rankings = getTableData();
    fetch('/save_rankings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform: platform, rankings: rankings })
    });
  }
  function updateDiffs() {
    // First, update My Ranking and Diff/Color
    Array.from(tbody.children).forEach(function(row, i) {
      row.children[0].textContent = i + 1;
      let adp = parseFloat(row.children[4].textContent); // ADP is now col 4
      let diff = null;
      if (!isNaN(adp)) {
        diff = (i + 1) - adp;
      }
      let color = '#fff';
      if (diff !== null) {
        let maxDiff = 10;
        let norm = Math.max(-maxDiff, Math.min(maxDiff, diff));
        if (norm < 0) {
          let pct = Math.abs(norm) / maxDiff;
          let r = Math.round(255 - 155 * pct);
          let g = 255;
          let b = Math.round(255 - 155 * pct);
          color = `rgb(${r},${g},${b})`;
        } else if (norm > 0) {
          let pct = norm / maxDiff;
          let r = 255;
          let g = Math.round(255 - 155 * pct);
          let b = Math.round(255 - 155 * pct);
          color = `rgb(${r},${g},${b})`;
        }
      }
      row.children[5].textContent = diff !== null ? diff : '';
      row.children[5].style.background = color;
    });
    // Now, update POS Rank for each row
    let rows = Array.from(tbody.children);
    rows.forEach(function(row, i) {
      let pos = row.children[2].textContent;
      // Count number of rows with same POS and lower My Ranking (index)
      let y = 1;
      for (let j = 0; j < rows.length; j++) {
        if (j === i) continue;
        if (rows[j].children[2].textContent === pos && j < i) {
          y++;
        }
      }
      row.children[3].textContent = pos + y;
    });
  }
  new Sortable(tbody, {
    animation: 150,
    onEnd: function () {
      updateDiffs();
      saveRankings();
    }
  });
  updateDiffs();
</script>
"""
  return f"""
<div class="container">
  <h1>Fantasy Football Custom Rankings</h1>
  <form method='post'>
    <label for='platform'>ADP Platform:</label>
    <select name='platform' id='platform' onchange='this.form.submit()'>
      <option value='sleeper' {'selected' if platform == 'sleeper' else ''}>Sleeper</option>
      <option value='underdog' {'selected' if platform == 'underdog' else ''}>Underdog</option>
    </select>
  </form>
  <form action="/draft" method="get" style="margin-bottom:24px;">
    <button type="submit" style="background:#0074d9;color:#fff;padding:10px 18px;border:none;border-radius:8px;font-size:1.1rem;cursor:pointer;">Start Draft</button>
  </form>
  {table_html}
</div>
{sortable_js}
"""
@app.route('/draft', methods=['GET', 'POST'])
def draft():
  platform = request.args.get('platform', 'sleeper')
  df = load_rankings(platform)
  # Calculate POS Rank for all players
  pos_ranks = []
  for i, row in df.iterrows():
      pos = row["POS"]
      my_rank = row["My Ranking"]
      y = (df[(df["POS"] == pos) & (df["My Ranking"] < my_rank)]).shape[0] + 1
      pos_ranks.append(f"{pos}{y}")
  df["POS Rank"] = pos_ranks
  df["ADP_num"] = df["ADP"].apply(safe_float)
  df["Diff"] = df["My Ranking"] - df["ADP_num"]
  # Show all players, no drafted logic
  # Professional CSS styles
  draft_css = """
<link href='https://fonts.googleapis.com/css?family=Inter:400,600&display=swap' rel='stylesheet'>
<style>
  body {
    font-family: 'Inter', Arial, sans-serif;
    background: #f6f8fa;
    margin: 0;
    padding: 0;
  }
  .container {
    max-width: 1100px;
    margin: 40px auto;
    background: #fff;
    border-radius: 18px;
    box-shadow: 0 6px 32px rgba(0,0,0,0.10);
    padding: 40px 32px 32px 32px;
  }
  h1 {
    font-size: 2.4rem;
    font-weight: 700;
    margin-bottom: 28px;
    color: #222;
    letter-spacing: -1px;
    text-align: left;
  }
  .draft-flex {
    display: flex;
    gap: 40px;
    align-items: flex-start;
    justify-content: space-between;
    overflow-x: auto;
    min-width: 0;
  }
  .draft-board, .drafted-list {
    background: #f9fafb;
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    padding: 24px 18px 18px 18px;
    flex: 1 1 0;
    min-width: 320px;
    max-width: 480px;
  }
  .draft-board {
    margin-right: 0;
  }
  .drafted-list {
    margin-left: 0;
  }
  h2 {
    font-size: 1.35rem;
    font-weight: 600;
    margin-bottom: 18px;
    color: #0074d9;
    letter-spacing: -0.5px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    font-size: 1rem;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 6px rgba(0,0,0,0.03);
  }
  thead {
    background: #f0f4f8;
  }
  th, td {
    padding: 10px 8px;
    text-align: left;
  }
  th {
    font-weight: 600;
    color: #333;
    border-bottom: 2px solid #eaecef;
    background: #f0f4f8;
  }
  tr {
    transition: background 0.15s;
  }
  tbody tr:hover {
    background: #f6f8fa;
  }
  td {
    border-bottom: 1px solid #eaecef;
    color: #222;
  }
  td:last-child {
    font-weight: 600;
    text-align: center;
    border-left: 1px solid #eaecef;
  }
  @media (max-width: 900px) {
    .container {
      padding: 16px 4px;
    }
    .draft-flex {
      flex-direction: row;
      gap: 24px;
      overflow-x: auto;
    }
    .draft-board, .drafted-list {
      min-width: 320px;
      max-width: 480px;
      padding: 14px 4px 8px 4px;
    }
    table, thead, tbody, th, td, tr {
      font-size: 0.97rem;
    }
    th, td {
      padding: 7px 2px;
    }
  }
  @media (max-width: 700px) {
    .draft-flex {
      flex-direction: row;
      gap: 16px;
      overflow-x: auto;
    }
    .draft-board, .drafted-list {
      min-width: 280px;
      max-width: 400px;
    }
  }
</style>
"""

  board_html = "<div class='draft-board'><h2>Draft Board</h2>"
  board_html += "<table><thead><tr>"
  for col in ["My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff"]:
    board_html += f"<th>{col}</th>"
  board_html += "</tr></thead><tbody>"
  for _, row in df.iterrows():
    board_html += f"<tr>"
    for col in ["My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff"]:
      board_html += f"<td>{row[col]}</td>"
    board_html += "</tr>"
  board_html += "</tbody></table></div>"

  drafted_html = "<div class='drafted-list'><h2>Players Drafted</h2>"
  drafted_html += "<table><thead><tr>"
  for col in ["My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff"]:
    drafted_html += f"<th>{col}</th>"
  drafted_html += "</tr></thead><tbody>"
  # Empty for now
  drafted_html += "</tbody></table></div>"

  return f"""
{draft_css}
<div class='container'>
  <h1>Fantasy Football Draft Board</h1>
  <div class='draft-flex'>
    {board_html}
    {drafted_html}
  </div>
</div>
"""

@app.route('/save_rankings', methods=['POST'])
def save_rankings():
  data = request.get_json()
  rankings = data.get('rankings', [])
  filename = "my_rankings.csv"
  # Only save order columns
  df = pd.DataFrame(rankings)[["Player Team (Bye)", "POS"]]
  df.to_csv(filename, index=False)
  return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True)
