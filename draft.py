from flask import request
from utils import add_pos_rank, add_diff, make_table_html
from utils import load_rankings

# --- CSS Constant ---
DRAFT_CSS = """
<link href='https://fonts.googleapis.com/css?family=Inter:400,600&display=swap' rel='stylesheet'>
<style>body {font-family: 'Inter', Arial, sans-serif; background: #f6f8fa; margin: 0; padding: 0;} .container {max-width: 1100px; margin: 40px auto; background: #fff; border-radius: 18px; box-shadow: 0 6px 32px rgba(0,0,0,0.10); padding: 40px 32px 32px 32px;} h1 {font-size: 2.4rem; font-weight: 700; margin-bottom: 28px; color: #222; letter-spacing: -1px; text-align: left;} .draft-flex {display: flex; gap: 40px; align-items: flex-start; justify-content: space-between; overflow-x: auto; min-width: 0;} .draft-board, .drafted-list {background: #f9fafb; border-radius: 14px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); padding: 24px 18px 18px 18px; flex: 1 1 0; min-width: 320px; max-width: 480px;} .draft-board {margin-right: 0;} .drafted-list {margin-left: 0;} h2 {font-size: 1.35rem; font-weight: 600; margin-bottom: 18px; color: #0074d9; letter-spacing: -0.5px;} table {width: 100%; border-collapse: collapse; background: #fff; font-size: 1rem; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.03);} thead {background: #f0f4f8;} th, td {padding: 10px 8px; text-align: left;} th {font-weight: 600; color: #333; border-bottom: 2px solid #eaecef; background: #f0f4f8;} tr {transition: background 0.15s;} tbody tr:hover {background: #f6f8fa;} td {border-bottom: 1px solid #eaecef; color: #222;} td:last-child {font-weight: 600; text-align: center; border-left: 1px solid #eaecef;} @media (max-width: 900px) {.container {padding: 16px 4px;} .draft-flex {flex-direction: row; gap: 24px; overflow-x: auto;} .draft-board, .drafted-list {min-width: 320px; max-width: 480px; padding: 14px 4px 8px 4px;} table, thead, tbody, th, td, tr {font-size: 0.97rem;} th, td {padding: 7px 2px;}} @media (max-width: 700px) {.draft-flex {flex-direction: row; gap: 16px; overflow-x: auto;} .draft-board, .drafted-list {min-width: 280px; max-width: 400px;}}</style>
"""

def draft_route(app):
    @app.route('/draft', methods=['GET', 'POST'])
    def draft():
        platform = request.args.get('platform', 'sleeper')
        df = load_rankings(platform)
        df = add_diff(df)
        df = add_pos_rank(df)
        board_html = "<div class='draft-board'><h2>Draft Board</h2>" + make_table_html(df, ["My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff"], color_diff=True) + "</div>"
        drafted_html = "<div class='drafted-list'><h2>Players Drafted</h2>" + make_table_html(df.iloc[0:0], ["My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff"], color_diff=True) + "</div>"
        return f"""
{DRAFT_CSS}
<div class='container'>
  <h1>Fantasy Football Draft Board</h1>
  <div class='draft-flex'>
    {board_html}
    {drafted_html}
  </div>
</div>
"""
