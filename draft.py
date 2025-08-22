from flask import request, session, redirect, url_for
from utils import load_rankings, add_diff, add_pos_rank, make_table_html

# --- CSS Constant ---
DRAFT_CSS = """
<link href='https://fonts.googleapis.com/css?family=Inter:400,600&display=swap' rel='stylesheet'>
<style>body {font-family: 'Inter', Arial, sans-serif; background: #f6f8fa; margin: 0; padding: 0;} .container {max-width: 1100px; margin: 40px auto; background: #fff; border-radius: 18px; box-shadow: 0 6px 32px rgba(0,0,0,0.10); padding: 40px 32px 32px 32px; position: relative;} h1 {font-size: 2.4rem; font-weight: 700; margin-bottom: 28px; color: #222; letter-spacing: -1px; text-align: left;} .end-draft-btn {position: absolute; top: 32px; right: 32px; z-index: 10;} .draft-flex {display: flex; gap: 40px; align-items: flex-start; justify-content: space-between; overflow-x: auto; min-width: 0;} .draft-board, .drafted-list {background: #f9fafb; border-radius: 14px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); padding: 24px 18px 18px 18px; flex: 1 1 0; min-width: 320px; max-width: 480px;} .draft-board {margin-right: 0;} .drafted-list {margin-left: 0;} h2 {font-size: 1.35rem; font-weight: 600; margin-bottom: 18px; color: #0074d9; letter-spacing: -0.5px;} table {width: 100%; border-collapse: collapse; background: #fff; font-size: 1rem; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.03);} thead {background: #f0f4f8;} th, td {padding: 10px 8px; text-align: left;} th {font-weight: 600; color: #333; border-bottom: 2px solid #eaecef; background: #f0f4f8;} tr {transition: background 0.15s;} tbody tr:hover {background: #f6f8fa;} td {border-bottom: 1px solid #eaecef; color: #222;} td:last-child {font-weight: 600; text-align: center; border-left: 1px solid #eaecef;} @media (max-width: 900px) {.container {padding: 16px 4px;} .draft-flex {flex-direction: row; gap: 24px; overflow-x: auto;} .draft-board, .drafted-list {min-width: 320px; max-width: 480px; padding: 14px 4px 8px 4px;} table, thead, tbody, th, td, tr {font-size: 0.97rem;} th, td {padding: 7px 2px;}} @media (max-width: 700px) {.draft-flex {flex-direction: row; gap: 16px; overflow-x: auto;} .draft-board, .drafted-list {min-width: 280px; max-width: 400px;}}</style>
"""

def draft_route(app):
    @app.route('/draft', methods=['GET', 'POST'])
    def draft():
        # Handle End Draft action
        if request.method == 'POST' and request.form.get('end_draft') == '1':
            session['drafted_players'] = []
            return redirect(url_for('home'))
        platform = request.args.get('platform', 'sleeper')
        # Initialize drafted players in session if not present
        if 'drafted_players' not in session:
            session['drafted_players'] = []

        # Handle marking a player as drafted
        if request.method == 'POST' and request.form.get('drafted_idx') is not None:
            drafted_idx = int(request.form.get('drafted_idx'))
            drafted_players = session.get('drafted_players', [])
            drafted_players.append(drafted_idx)
            session['drafted_players'] = drafted_players

        df = load_rankings(platform)
        df = add_diff(df)
        df = add_pos_rank(df)

        # Split into draft board and drafted players
        drafted_players = session.get('drafted_players', [])
        board_df = df[~df.index.isin(drafted_players)]
        drafted_df = df[df.index.isin(drafted_players)]
        # Add Draft Position column based on order in drafted_players
        if not drafted_df.empty:
            draft_pos_map = {idx: pos+1 for pos, idx in enumerate(drafted_players)}
            drafted_df = drafted_df.copy()
            drafted_df['Draft Position'] = [draft_pos_map[idx] for idx in drafted_df.index]

        # Generate HTML for draft board with buttons
        board_html = "<div class='draft-board'><h2>Draft Board</h2><table><thead><tr>"
        columns = ["My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff", "Action"]
        for col in columns:
            board_html += f"<th>{col}</th>"
        board_html += "</tr></thead><tbody>"
        for idx, row in board_df.iterrows():
            board_html += "<tr>"
            for col in columns[:-1]:
                board_html += f"<td>{row[col]}</td>"
            # Add Mark Drafted button
            board_html += (
                f"<td>"
                f"<form method='POST' style='margin:0;'>"
                f"<input type='hidden' name='drafted_idx' value='{idx}'/>"
                f"<button type='submit'>Mark Drafted</button>"
                f"</form>"
                f"</td>"
            )
            board_html += "</tr>"
        board_html += "</tbody></table></div>"

        # Drafted players table
        if not drafted_df.empty and 'Draft Position' in drafted_df.columns:
            drafted_df = drafted_df.sort_values('Draft Position')
        drafted_html = "<div class='drafted-list'><h2>Players Drafted</h2>"
        drafted_html += make_table_html(drafted_df, ["Draft Position", "My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff"], color_diff=True)
        drafted_html += "</div>"

        # End Draft button HTML (top right)
        end_draft_html = ("<form method='POST' class='end-draft-btn'>"
                         "<input type='hidden' name='end_draft' value='1'/>"
                         "<button type='submit' style='background:#e74c3c;color:#fff;padding:10px 18px;border:none;border-radius:8px;font-size:1.1rem;cursor:pointer;'>End Draft</button>"
                         "</form>")

        return f"""
    {DRAFT_CSS}
    <div class='container'>
        {end_draft_html}
        <h1>Fantasy Football Draft Board</h1>
        <div class='draft-flex'>
            {board_html}
            {drafted_html}
        </div>
    </div>
    """
