from flask import Flask, render_template_string, jsonify
import pandas as pd
import requests

app = Flask(__name__)

def get_adp_data():
    url = "https://api.sleeper.com/v1/players/nfl/adp"
    response = requests.get(url)
    if response.status_code != 200:
        return pd.DataFrame()
    adp_data = response.json()
    # Extract relevant fields for top 200 players
    players = []
    for player in adp_data[:10]:
        players.append({
            'Player': player.get('full_name', 'N/A'),
            'Position': player.get('position', 'N/A'),
            'Team': player.get('team', 'N/A'),
            'ADP': round(player.get('adp', 0), 2)
        })
    return pd.DataFrame(players)

template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Fantasy Football Table</title>
    <style>
        .spinner {
            margin: 50px auto;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        table { border-collapse: collapse; width: 60%; margin: 30px auto; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
    </style>
    <!-- Include Sortable.js from CDN -->
    <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
</head>
<body>
    <h2 style="text-align:center;">Fantasy Football Data</h2>
    <div id="loading" style="text-align:center;">
        <div class="spinner"></div>
        <p>Loading data...</p>
    </div>
    <div id="table-container" style="width: 60%; margin: 0 auto; display:none;">
        <table id="fantasy-table" class="table">
            <thead>
                <tr>
                    <th>Player</th>
                    <th>Position</th>
                    <th>Team</th>
                    <th>ADP</th>
                </tr>
            </thead>
            <tbody>
                <!-- Table rows will be inserted here by JS -->
            </tbody>
        </table>
    </div>
    <script>
        // Fetch data and build table
        window.onload = function() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.querySelector('#fantasy-table tbody');
                    tbody.innerHTML = '';
                    data.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `<td>${row.Player}</td><td>${row.Position}</td><td>${row.Team}</td><td>${row.ADP}</td>`;
                        tbody.appendChild(tr);
                    });
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('table-container').style.display = 'block';
                    new Sortable(document.querySelector('#fantasy-table tbody'), {
                        animation: 150,
                        ghostClass: 'sortable-ghost'
                    });
                });
        }
    </script>
</body>
</html>
'''


# Main page route
@app.route('/')
def home():
    return render_template_string(template)

# Data endpoint for AJAX
@app.route('/data')
def data():
    df = get_adp_data()
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
