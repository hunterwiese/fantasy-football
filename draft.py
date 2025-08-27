from flask import request, session, redirect, url_for
from utils import load_rankings, add_diff, add_pos_rank
import time

# Small in-process cache to avoid recomputing rankings every request
_CACHE_TTL = 30  # seconds
_df_cache = {}   # { platform: {"df": DataFrame, "ts": float} }

def _get_rankings_cached(platform: str):
    now = time.time()
    entry = _df_cache.get(platform)
    if entry and (now - entry["ts"] < _CACHE_TTL):
        # Return a shallow copy so filters don’t mutate cache
        return entry["df"].copy(deep=False)
    df = load_rankings(platform)
    # Compute once; these are stable for a given platform/order
    df = add_diff(df)
    df = add_pos_rank(df)
    # Precompute lowercase name key for fast, case-insensitive search
    if "name_key" not in df.columns:
        df["name_key"] = df["Player Team (Bye)"].astype(str).str.lower()
    _df_cache[platform] = {"df": df, "ts": now}
    return df.copy(deep=False)

# Gradient color for Diff like on My Rankings (max magnitude = 10)
def _diff_bg_color(diff, max_diff=10):
    # NaN-safe
    try:
        if diff != diff:
            return "#fff"
    except Exception:
        return "#fff"
    # Clamp
    norm = max(-max_diff, min(max_diff, float(diff)))
    if norm < 0:
        pct = abs(norm) / max_diff
        r = round(255 - 155 * pct)
        g = 255
        b = round(255 - 155 * pct)
        return f"rgb({r},{g},{b})"
    elif norm > 0:
        pct = norm / max_diff
        r = 255
        g = round(255 - 155 * pct)
        b = round(255 - 155 * pct)
        return f"rgb({r},{g},{b})"
    return "#fff"

def _render_board_table(board_df, pos_filter: str, q: str):
    cols = ["My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP", "Diff", "Action"]
    th = "".join(f"<th>{c}</th>" for c in cols)
    rows = []
    for idx, row in board_df.iterrows():
        diff_val = row["Diff"] if (row["Diff"] == row["Diff"]) else None
        diff_bg = _diff_bg_color(diff_val) if diff_val is not None else "#fff"
        tds = [
            f"<td>{row['My Ranking']}</td>",
            f"<td>{row['Player Team (Bye)']}</td>",
            f"<td>{row['POS']}</td>",
            f"<td>{row['POS Rank']}</td>",
            f"<td>{row['ADP']}</td>",
            f"<td style='background:{diff_bg};'>{'' if diff_val is None else diff_val}</td>",
            (
                "<td>"
                "<form method='POST' style='margin:0;'>"
                f"<input type='hidden' name='drafted_idx' value='{idx}'/>"
                f"<input type='hidden' name='pos' value='{pos_filter or ''}'/>"
                f"<input type='hidden' name='q' value='{q or ''}'/>"
                "<button class='btn btn-primary' type='submit'>Mark Drafted</button>"
                "</form>"
                "</td>"
            ),
        ]
        rows.append(f"<tr>{''.join(tds)}</tr>")
    return (
        "<div class='card'>"
        "<h2>Draft Board</h2>"
        "<table class='table'><thead><tr>" + th + "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
        "</div>"
    )

def _render_drafted_table(drafted_df, drafted_order):
    if drafted_df.empty:
        return (
            "<div class='card'>"
            "<h2>Players Drafted</h2>"
            "<div class='empty'>No players drafted yet.</div>"
            "</div>"
        )
    # Map index -> draft position by order clicked
    draft_pos_map = {idx: pos + 1 for pos, idx in enumerate(drafted_order)}
    drafted_df = drafted_df.copy()
    drafted_df["Draft Position"] = [draft_pos_map.get(ix, 0) for ix in drafted_df.index]
    # Show newest draftees first
    drafted_df.sort_values("Draft Position", ascending=False, inplace=True)

    # Removed "Diff" column from the drafted table
    cols = ["Draft Position", "My Ranking", "Player Team (Bye)", "POS", "POS Rank", "ADP"]
    th = "".join(f"<th>{c}</th>" for c in cols)
    rows = []
    for idx, row in drafted_df.iterrows():
        tds = [
            f"<td>{int(row['Draft Position'])}</td>",
            f"<td>{row['My Ranking']}</td>",
            f"<td>{row['Player Team (Bye)']}</td>",
            f"<td>{row['POS']}</td>",
            f"<td>{row['POS Rank']}</td>",
            f"<td>{row['ADP']}</td>",
        ]
        rows.append(f"<tr>{''.join(tds)}</tr>")
    return (
        "<div class='card'>"
        "<h2>Players Drafted</h2>"
        "<table class='table'><thead><tr>" + th + "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
        "</div>"
    )

DRAFT_PAGE_CSS = """
<style>
  .container { max-width: 1200px; margin: 24px auto; padding: 0 16px; }
  .header { position: relative; display:flex; align-items:center; justify-content:center; }
  .end-draft { position:absolute; right:0; top:0; }
  .btn { cursor:pointer; border:none; border-radius:8px; padding:8px 14px; }
  .btn-primary { background:#1664d9; color:#fff; }
  .btn-danger  { background:#e74c3c; color:#fff; }
  .grid { display:flex; gap:16px; }
  .card { flex:1; background:#fff; border-radius:12px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,0.06); min-width: 460px; }
  .table { width:100%; border-collapse:collapse; }
  .table th, .table td { padding:10px; border-bottom:1px solid #eaecef; text-align:left; }
  .table thead th { background:#f4f6f8; }
  .empty { color:#6b7280; font-style:italic; padding:8px 0; }
  @media (max-width: 1100px) {
    .grid { overflow-x:auto; }
    .card { min-width:540px; }
  }
</style>
"""

def draft_route(app):
    @app.route('/draft', methods=['GET', 'POST'])
    def draft():
        platform = request.args.get('platform', 'sleeper')
        pos_filter = request.args.get('pos', '')  # '' means All
        q = request.args.get('q', '').strip()

        # Initialize drafted list
        drafted_order = session.get('drafted_players', []) or []

        if request.method == 'POST':
            # Preserve current filters on POST
            pos_filter = request.form.get('pos', pos_filter)
            q = request.form.get('q', q).strip()

            # End Draft
            if request.form.get('end_draft') == '1':
                session['drafted_players'] = []
                return redirect(url_for('home'))

            # Mark Drafted (PRG)
            drafted_idx = request.form.get('drafted_idx')
            if drafted_idx is not None:
                try:
                    drafted_idx = int(drafted_idx)
                except ValueError:
                    return redirect(url_for('draft', platform=platform, pos=pos_filter or None, q=q or None))
                if drafted_idx not in drafted_order:
                    drafted_order.append(drafted_idx)
                    session['drafted_players'] = drafted_order
                return redirect(url_for('draft', platform=platform, pos=pos_filter or None, q=q or None))

        # Get cached rankings
        df = _get_rankings_cached(platform)

        # Split into board and drafted
        drafted_set = set(drafted_order)
        board_df = df.loc[~df.index.isin(drafted_set)]
        drafted_df = df.loc[df.index.isin(drafted_set)]

        # Apply POS filter if selected
        if pos_filter:
            board_df = board_df[board_df['POS'] == pos_filter]
            drafted_df = drafted_df[drafted_df['POS'] == pos_filter]

        # Apply fast substring filter on player name (case-insensitive)
        if q:
            key = q.lower()
            # Use precomputed lowercase column and regex=False for speed
            if 'name_key' not in board_df.columns:
                # In case of sliced DF losing the column (shouldn't happen), recompute cheaply
                board_df = board_df.assign(name_key=board_df["Player Team (Bye)"].astype(str).str.lower())
            if 'name_key' not in drafted_df.columns and not drafted_df.empty:
                drafted_df = drafted_df.assign(name_key=drafted_df["Player Team (Bye)"].astype(str).str.lower())
            board_df = board_df[board_df['name_key'].str.contains(key, regex=False, na=False)]
            drafted_df = drafted_df[drafted_df['name_key'].str.contains(key, regex=False, na=False)]

        # Build position filter options from full DF (so options don’t disappear)
        positions = sorted(p for p in df['POS'].dropna().unique().tolist())
        pos_options = ["<option value=''>All</option>"] + [
            f"<option value='{p}'{' selected' if p == pos_filter else ''}>{p}</option>"
            for p in positions
        ]
        # Filter/search form: submit via Enter or Apply button
        filter_form = (
            "<form method='get' class='filter' style='margin:0 0 16px 0; display:flex; gap:10px; align-items:center;'>"
            f"<input type='hidden' name='platform' value='{platform}'>"
            "<label for='pos' style='font-weight:600;color:#444;'>Position:</label>"
            f"<select name='pos' id='pos'>{''.join(pos_options)}</select>"
            "<label for='q' style='font-weight:600;color:#444;margin-left:10px;'>Search:</label>"
            f"<input type='text' id='q' name='q' value='{q}' placeholder='Search players...' "
            "style='padding:6px 10px; border:1px solid #d0d7de; border-radius:6px; min-width:220px;'>"
            "<button type='submit' class='btn btn-primary' style='margin-left:8px;'>Apply</button>"
            "</form>"
        )

        # Render tables
        board_html = _render_board_table(board_df, pos_filter, q)
        drafted_html = _render_drafted_table(drafted_df, drafted_order)

        # End Draft button (preserve filters)
        end_draft_html = (
            "<form method='POST' class='end-draft' style='position:absolute; right:0; top:0;'>"
            "<input type='hidden' name='end_draft' value='1'/>"
            f"<input type='hidden' name='pos' value='{pos_filter or ''}'/>"
            f"<input type='hidden' name='q' value='{q or ''}'/>"
            "<button class='btn btn-danger' type='submit'>End Draft</button>"
            "</form>"
        )

        return f"""
{DRAFT_PAGE_CSS}
<div class="container">
  <div class="header">
    <h1>Fantasy Football Draft Board</h1>
    {end_draft_html}
  </div>
  {filter_form}
  <div class="grid">
    {board_html}
    {drafted_html}
  </div>
</div>
"""
