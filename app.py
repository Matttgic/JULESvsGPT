# Fichier : app.py

from flask import Flask, render_template, request, json
from datetime import datetime
import api_client
import prediction_engine
from config import BOOKMAKER_ID

app = Flask(__name__)

# Liste des championnats déplacée ici pour plus de propreté et de sécurité
MAJOR_LEAGUES = {
    "UEFA Champions League": 2, "UEFA Europa League": 3, "Euro Championship": 4,
    "Africa Cup of Nations": 6, "World Cup - Women": 8, "Friendlies": 10,
    "CONMEBOL Sudamericana": 11, "CONMEBOL Libertadores": 13, "FIFA Club World Cup": 15,
    "CONCACAF Champions League": 16, "CONCACAF Gold Cup": 22, "Africa Cup of Nations Qualification": 36,
    "UEFA U21 Championship": 38, "Premier League": 39, "Championship": 40, "FA Cup": 45,
    "Ligue 1": 61, "Ligue 2": 62, "Feminine Division 1": 64, "Coupe de France": 66,
    "Serie A (Brazil)": 71, "Bundesliga": 78, "2. Bundesliga": 79, "DFB Pokal": 81,
    "Eredivisie": 88, "Primeira Liga (Portugal)": 94, "Eliteserien (Norway)": 103,
    "Ekstraklasa (Poland)": 106, "Premier (Wales)": 110, "Allsvenskan (Sweden)": 113,
    "Superligaen (Denmark)": 119, "Serie A": 135, "Serie B": 136, "Coppa Italia": 137,
    "La Liga": 140, "Segunda División": 141, "Jupiler Pro League": 144,
    "Premier (Iceland)": 164, "A PFG (Bulgaria)": 172, "Premiership (Scotland)": 179,
    "Ligue 1 (Algeria)": 186, "Super League (Switzerland/Greece)": 197, "Super Lig (Turkey)": 203,
    "Prva HNL (Croatia)": 210, "Tipp3 Bundesliga (Austria)": 218, "Primera A (Colombia)": 239,
    "Serie A (Ecuador)": 242, "Veikkausliiga (Finland)": 244, "Primera Division - Apertura (Paraguay)": 250,
    "Primera Division - Clausura (Paraguay)": 252, "Major League Soccer": 253,
    "National Division (Luxembourg)": 261, "Liga MX": 262, "Primera Division (Chile)": 265,
    "NB I (Hungary)": 271, "Liga I (Romania)": 283, "Super Liga (Serbia)": 286,
    "Premijer Liga (Bosnia)": 315, "Erovnuli Liga (Georgia)": 327, "Meistriliiga (Estonia)": 329,
    "Super Liga (Slovakia)": 332, "Premier League (Ukraine)": 333, "Czech Liga": 345,
    "First League (Montenegro)": 355, "Premier Division (Ireland)": 357, "A Lyga (Lithuania)": 362,
    "Virsliga (Latvia)": 365, "1. SNL (Slovenia)": 373, "Divizia Națională (Moldova)": 394,
    "Premiership (Northern Ireland)": 408, "UEFA Champions League Women": 525, "Community Shield": 528,
    "Super Cup (Germany)": 529, "UEFA Super Cup": 531, "CONMEBOL Recopa": 541,
    "Super Cup (Spain)": 556, "Friendlies Women": 666, "UEFA Championship - Women": 743,
    "Leagues Cup": 772, "UEFA Europa Conference League": 848, "UEFA U21 Championship - Qualification": 850,
    "CONCACAF Gold Cup - Qualification": 858, "UEFA Nations League - Women": 1040,
    "UEFA Championship - Women - Qualification": 1083, "FIFA Club World Cup - Play-In": 1186
}

# Permet d'utiliser `tojson` dans les templates pour passer des données complexes
app.jinja_env.filters['tojson'] = json.dumps

@app.route('/')
def index():
    sorted_leagues = dict(sorted(MAJOR_LEAGUES.items()))
    return render_template('index.html', leagues=sorted_leagues)

@app.route('/fixtures', methods=['POST'])
def show_fixtures():
    league_id = request.form['league_id']
    date_str = request.form['date']

    # Calcule la saison dynamiquement à partir de la date
    # Si le mois est avant juillet, on considère que c'est la fin de la saison précédente
    # (ex: mai 2024 fait partie de la saison 2023)
    match_date = datetime.strptime(date_str, '%Y-%m-%d')
    season = match_date.year - 1 if match_date.month < 7 else match_date.year

    fixtures_data = api_client.get_fixtures_for_date(date_str, league_id, season)

    fixtures = []
    if fixtures_data and fixtures_data.get('response'):
        fixtures = fixtures_data['response']

    return render_template('fixtures.html', fixtures=fixtures, date=date_str)

@app.route('/result', methods=['POST'])
def show_result():
    fixture = json.loads(request.form['fixture_data'])
    prediction = prediction_engine.predict_match(fixture)
    odds_data = api_client.get_odds(fixture['fixture']['id'], BOOKMAKER_ID)
    
    parsed_odds = None
    if odds_data and odds_data.get('response'):
        try:
            bookmaker = odds_data['response'][0]['bookmakers'][0]
            for bet in bookmaker['bets']:
                if bet['name'] == 'Match Winner':
                    parsed_odds = {
                        'home': next((o['odd'] for o in bet['values'] if o['value'] == 'Home'), 'N/A'),
                        'draw': next((o['odd'] for o in bet['values'] if o['value'] == 'Draw'), 'N/A'),
                        'away': next((o['odd'] for o in bet['values'] if o['value'] == 'Away'), 'N/A'),
                    }
                    break
        except (IndexError, KeyError):
            pass

    return render_template('result.html', fixture=fixture, prediction=prediction, odds=parsed_odds)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
