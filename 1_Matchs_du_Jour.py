
import streamlit as st
from datetime import datetime
import pandas as pd
import api_client
import prediction_engine
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --- CONFIGURATION ---
# Liste complète de tous les championnats
ALL_LEAGUES = {
    "UEFA Champions League": 2,
    "UEFA Europa League": 3,
    "Euro Championship": 4,
    "Africa Cup of Nations": 6,
    "World Cup - Women": 8,
    "Friendlies": 10,
    "CONMEBOL Sudamericana": 11,
    "CONMEBOL Libertadores": 13,
    "FIFA Club World Cup": 15,
    "CONCACAF Champions League": 16,
    "CONCACAF Gold Cup": 22,
    "Africa Cup of Nations Qualification": 36,
    "UEFA U21 Championship": 38,
    "Premier League": 39,
    "Championship": 40,
    "FA Cup": 45,
    "Ligue 1": 61,
    "Ligue 2": 62,
    "Feminine Division 1": 64,
    "Coupe de France": 66,
    "Serie A (Brazil)": 71,
    "Bundesliga": 78,
    "2. Bundesliga": 79,
    "DFB Pokal": 81,
    "Eredivisie": 88,
    "Primeira Liga (Portugal)": 94,
    "Eliteserien (Norway)": 103,
    "Ekstraklasa (Poland)": 106,
    "Premier (Wales)": 110,
    "Allsvenskan (Sweden)": 113,
    "Superligaen (Denmark)": 119,
    "Serie A": 135,
    "Serie B": 136,
    "Coppa Italia": 137,
    "La Liga": 140,
    "Segunda División": 141,
    "Jupiler Pro League": 144,
    "Premier (Iceland)": 164,
    "A PFG (Bulgaria)": 172,
    "Premiership (Scotland)": 179,
    "Ligue 1 (Algeria)": 186,
    "Super League (Switzerland/Greece)": 197,
    "Super Lig (Turkey)": 203,
    "Prva HNL (Croatia)": 210,
    "Tipp3 Bundesliga (Austria)": 218,
    "Primera A (Colombia)": 239,
    "Serie A (Ecuador)": 242,
    "Veikkausliiga (Finland)": 244,
    "Primera Division - Apertura (Paraguay)": 250,
    "Primera Division - Clausura (Paraguay)": 252,
    "Major League Soccer": 253,
    "National Division (Luxembourg)": 261,
    "Liga MX": 262,
    "Primera Division (Chile)": 265,
    "NB I (Hungary)": 271,
    "Liga I (Romania)": 283,
    "Super Liga (Serbia)": 286,
    "Premijer Liga (Bosnia)": 315,
    "Erovnuli Liga (Georgia)": 327,
    "Meistriliiga (Estonia)": 329,
    "Super Liga (Slovakia)": 332,
    "Premier League (Ukraine)": 333,
    "Czech Liga": 345,
    "First League (Montenegro)": 355,
    "Premier Division (Ireland)": 357,
    "A Lyga (Lithuania)": 362,
    "Virsliga (Latvia)": 365,
    "1. SNL (Slovenia)": 373,
    "Divizia Națională (Moldova)": 394,
    "Premiership (Northern Ireland)": 408,
    "UEFA Champions League Women": 525,
    "Community Shield": 528,
    "Super Cup (Germany)": 529,
    "UEFA Super Cup": 531,
    "CONMEBOL Recopa": 541,
    "Super Cup (Spain)": 556,
    "Friendlies Women": 666,
    "UEFA Championship - Women": 743,
    "Leagues Cup": 772,
    "UEFA Europa Conference League": 848,
    "UEFA U21 Championship - Qualification": 850,
    "CONCACAF Gold Cup - Qualification": 858,
    "UEFA Nations League - Women": 1040,
    "UEFA Championship - Women - Qualification": 1083,
    "FIFA Club World Cup - Play-In": 1186
}

# --- DATABASE ---
@st.cache_resource
def get_db_engine():
    """Crée et met en cache le moteur de base de données SQLAlchemy."""
    return create_engine("sqlite:///predictions.db")

def init_db(engine):
    """Crée la table de prédictions si elle n'existe pas."""
    with engine.connect() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY,
                prediction_ts TIMESTAMP,
                fixture_id INTEGER UNIQUE,
                match_desc TEXT,
                predicted_outcome TEXT,
                odds_home REAL,
                odds_draw REAL,
                odds_away REAL,
                status TEXT DEFAULT 'PENDING'
            )
        """))
        connection.commit()

# --- API & DATA ---
@st.cache_data(ttl=3600)
def load_fixtures_today():
    """Charge les matchs du jour pour tous les championnats et les met en cache."""
    today_str = datetime.today().strftime('%Y-%m-%d')
    all_fixtures = []
    match_date = datetime.strptime(today_str, '%Y-%m-%d')
    season = match_date.year - 1 if match_date.month < 7 else match_date.year
    
    for league_id in ALL_LEAGUES.values():
        try:
            fixtures_data = api_client.get_fixtures_for_date(today_str, league_id, season)
            if fixtures_data and fixtures_data.get('response'):
                all_fixtures.extend(fixtures_data['response'])
        except Exception as e:
            # Continue même si une ligue échoue
            continue
    
    return all_fixtures

def get_prediction_and_odds(fixture):
    """Génère la prédiction et récupère les cotes pour un match."""
    try:
        prediction, analysis_logs = prediction_engine.predict_match(fixture)
        odds_data = api_client.get_odds(fixture['fixture']['id'], 8)
        
        parsed_odds = None
        if odds_data and odds_data.get('response'):
            try:
                bookmaker = odds_data['response'][0]['bookmakers'][0]
                bet = next((b for b in bookmaker['bets'] if b['name'] == 'Match Winner'), None)
                if bet:
                    parsed_odds = {
                        'home': next((o['odd'] for o in bet['values'] if o['value'] == 'Home'), 'N/A'),
                        'draw': next((o['odd'] for o in bet['values'] if o['value'] == 'Draw'), 'N/A'),
                        'away': next((o['odd'] for o in bet['values'] if o['value'] == 'Away'), 'N/A'),
                    }
            except (IndexError, KeyError):
                pass
        
        return prediction, parsed_odds, analysis_logs
    except Exception as e:
        return "Erreur de prédiction", None, [f"Erreur: {str(e)}"]

def save_prediction_to_db(engine, fixture, prediction, odds):
    """Sauvegarde une prédiction en base de données."""
    if odds and 'N/A' not in odds.values():
        try:
            Session = sessionmaker(bind=engine)
            with Session() as session:
                home_team = fixture['teams']['home']['name']
                away_team = fixture['teams']['away']['name']
                session.execute(
                    text('INSERT OR IGNORE INTO predictions (fixture_id, prediction_ts, match_desc, predicted_outcome, odds_home, odds_draw, odds_away) VALUES (:fid, :ts, :desc, :pred, :oh, :od, :oa)'),
                    [{
                        "fid": fixture['fixture']['id'], "ts": datetime.now(),
                        "desc": f"{home_team} vs {away_team}", "pred": prediction,
                        "oh": float(odds['home']), "od": float(odds['draw']),
                        "oa": float(odds['away'])
                    }]
                )
                session.commit()
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde: {str(e)}")

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Jules' Football Predictor", page_icon="⚽", layout="wide")
    
    engine = get_db_engine()
    init_db(engine)

    st.title("🔮 Jules' Football Predictor")
    st.header(f"Matchs du Jour avec Prédictions ({datetime.today().strftime('%d/%m/%Y')})")

    with st.spinner("Chargement des matchs et génération des prédictions..."):
        try:
            fixtures_today = load_fixtures_today()
        except Exception as e:
            st.error(f"Erreur lors de la récupération des matchs. La clé API est-elle correcte ?\n\n{e}")
            return

        if not fixtures_today:
            st.warning("Aucun match trouvé pour aujourd'hui.")
            return

        st.success(f"{len(fixtures_today)} matchs trouvés dans tous les championnats.")

        # Grouper les matchs par ligue pour une meilleure organisation
        fixtures_by_league = {}
        for fixture in fixtures_today:
            league_name = fixture['league']['name']
            if league_name not in fixtures_by_league:
                fixtures_by_league[league_name] = []
            fixtures_by_league[league_name].append(fixture)

        # Afficher les matchs groupés par ligue
        for league_name, fixtures in fixtures_by_league.items():
            st.subheader(f"🏆 {league_name}")
            
            for fixture in fixtures:
                home_team = fixture['teams']['home']['name']
                away_team = fixture['teams']['away']['name']
                
                # Container pour chaque match
                match_container = st.container()
                with match_container:
                    # En-tête du match
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 2])
                    
                    with col1:
                        st.image(fixture['teams']['home']['logo'], width=50)
                        st.write(f"**{home_team}**")
                    
                    with col2:
                        st.write("**VS**")
                        match_time = datetime.fromtimestamp(fixture['fixture']['timestamp']).strftime('%H:%M')
                        st.write(f"🕒 {match_time}")
                    
                    with col3:
                        st.image(fixture['teams']['away']['logo'], width=50)
                        st.write(f"**{away_team}**")
                    
                    # Génération automatique de la prédiction
                    prediction, odds, analysis_logs = get_prediction_and_odds(fixture)
                    
                    with col4:
                        st.write("**🔮 Prédiction:**")
                        if "Erreur" in prediction:
                            st.error(prediction)
                        else:
                            st.success(prediction)
                    
                    with col5:
                        st.write("**💰 Cotes:**")
                        if odds and 'N/A' not in odds.values():
                            st.write(f"1: {odds['home']}")
                            st.write(f"X: {odds['draw']}")
                            st.write(f"2: {odds['away']}")
                            
                            # Sauvegarder en base
                            save_prediction_to_db(engine, fixture, prediction, odds)
                        else:
                            st.write("Non disponibles")
                    
                    # Informations supplémentaires du match
                    st.write(f"**📍 {fixture['fixture']['venue']['name']}, {fixture['fixture']['venue']['city']}**")
                    
                    # Option pour voir le détail de l'analyse (optionnel)
                    if st.checkbox(f"Voir l'analyse détaillée", key=f"analysis_{fixture['fixture']['id']}"):
                        st.text_area("Logs d'analyse", value="\n".join(analysis_logs), height=100, key=f"logs_{fixture['fixture']['id']}")
                    
                    st.divider()  # Séparateur entre les matchs

if __name__ == "__main__":
    main()