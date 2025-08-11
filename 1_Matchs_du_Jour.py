import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import api_client
import prediction_engine
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
import os
import hashlib

# --- CONFIGURATION ---
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

# --- CACHE CONFIGURATION ---
CACHE_FILE = "predictions_cache.json"
CACHE_DURATION_HOURS = 6  # Cache valide pendant 6 heures

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

# --- DATABASE FUNCTIONS ---
def load_predictions_from_db_for_today(engine):
    """Charge les prédictions du jour depuis la base de données."""
    today_str = datetime.today().strftime('%Y-%m-%d')
    try:
        Session = sessionmaker(bind=engine)
        with Session() as session:
            result = session.execute(
                text("""
                    SELECT fixture_id, match_desc, predicted_outcome, 
                           odds_home, odds_draw, odds_away, prediction_ts 
                    FROM predictions 
                    WHERE DATE(prediction_ts) = :today
                """),
                {"today": today_str}
            )
            predictions = result.fetchall()
            return predictions if predictions else None
    except Exception as e:
        st.error(f"Erreur lors du chargement depuis la DB: {e}")
        return None

def get_fixture_info_for_prediction(fixture_id):
    """Récupère les infos d'un match depuis l'API (pour l'affichage)."""
    try:
        # On fait un seul appel API pour récupérer les infos du match
        today_str = datetime.today().strftime('%Y-%m-%d')
        match_date = datetime.strptime(today_str, '%Y-%m-%d')
        season = match_date.year - 1 if match_date.month < 7 else match_date.year
        
        for league_id in ALL_LEAGUES.values():
            fixtures_data = api_client.get_fixtures_for_date(today_str, league_id, season)
            if fixtures_data and fixtures_data.get('response'):
                for fixture in fixtures_data['response']:
                    if fixture['fixture']['id'] == fixture_id:
                        return fixture
        return None
    except Exception as e:
        return None

def display_predictions_from_db(db_predictions, engine):
    """Affiche les prédictions chargées depuis la base de données."""
    st.success(f"🤖 {len(db_predictions)} prédictions générées automatiquement par GitHub Actions !")
    
    # Organiser par fixture_id pour éviter les doublons
    predictions_dict = {}
    for pred in db_predictions:
        fixture_id = pred[0]
        if fixture_id not in predictions_dict:
            predictions_dict[fixture_id] = {
                'match_desc': pred[1],
                'predicted_outcome': pred[2],
                'odds_home': pred[3],
                'odds_draw': pred[4],
                'odds_away': pred[5],
                'prediction_ts': pred[6]
            }
    
    # Récupérer les infos des matchs depuis l'API (une seule fois)
    with st.spinner("Chargement des informations des matchs..."):
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
                continue
    
    # Organiser par ligue
    fixtures_by_league = {}
    for fixture in all_fixtures:
        fixture_id = fixture['fixture']['id']
        if fixture_id in predictions_dict:
            league_name = fixture['league']['name']
            if league_name not in fixtures_by_league:
                fixtures_by_league[league_name] = []
            fixtures_by_league[league_name].append({
                'fixture': fixture,
                'prediction_data': predictions_dict[fixture_id]
            })
    
    # Affichage
    for league_name, matches in fixtures_by_league.items():
        st.subheader(f"🏆 {league_name}")
        
        for match_info in matches:
            fixture = match_info['fixture']
            pred_data = match_info['prediction_data']
            
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            
            with st.container():
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
                
                with col4:
                    st.write("**🔮 Prédiction:**")
                    st.success(pred_data['predicted_outcome'])
                
                with col5:
                    st.write("**💰 Cotes:**")
                    if pred_data['odds_home'] and pred_data['odds_draw'] and pred_data['odds_away']:
                        st.write(f"1: {pred_data['odds_home']}")
                        st.write(f"X: {pred_data['odds_draw']}")
                        st.write(f"2: {pred_data['odds_away']}")
                    else:
                        st.write("Non disponibles")
                
                st.write(f"**📍 {fixture['fixture']['venue']['name']}, {fixture['fixture']['venue']['city']}**")
                st.caption(f"Prédiction générée à: {datetime.fromisoformat(str(pred_data['prediction_ts'])).strftime('%H:%M:%S')}")
                
                st.divider()

# --- CACHE FUNCTIONS (gardées pour fallback) ---
def get_cache_key():
    """Génère une clé de cache basée sur la date du jour."""
    today_str = datetime.today().strftime('%Y-%m-%d')
    return hashlib.md5(today_str.encode()).hexdigest()

def load_cache():
    """Charge le cache depuis le fichier."""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Vérifier si le cache est encore valide
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cache_time > timedelta(hours=CACHE_DURATION_HOURS):
            return None
        
        # Vérifier si c'est le même jour
        cache_key = cache_data.get('cache_key')
        if cache_key != get_cache_key():
            return None
            
        return cache_data
    except Exception as e:
        st.error(f"Erreur lors du chargement du cache: {e}")
        return None

def save_cache(data):
    """Sauvegarde les données dans le cache."""
    try:
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'cache_key': get_cache_key(),
            'data': data
        }
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du cache: {e}")

# --- API & DATA (gardées pour fallback) ---
def load_fixtures_today():
    """Charge les matchs du jour pour tous les championnats."""
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

def process_all_fixtures():
    """Traite tous les matchs et génère les prédictions."""
    fixtures_today = load_fixtures_today()
    
    if not fixtures_today:
        return {}
    
    processed_data = {}
    total_fixtures = len(fixtures_today)
    
    # Progress bar
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    for i, fixture in enumerate(fixtures_today):
        fixture_id = fixture['fixture']['id']
        league_name = fixture['league']['name']
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        
        # Mise à jour de la progress bar
        progress = (i + 1) / total_fixtures
        progress_bar.progress(progress)
        progress_text.text(f"Traitement des matchs: {i + 1}/{total_fixtures} - {home_team} vs {away_team}")
        
        # Génération de la prédiction
        prediction, odds, analysis_logs = get_prediction_and_odds(fixture)
        
        # Organisation par ligue
        if league_name not in processed_data:
            processed_data[league_name] = []
        
        processed_data[league_name].append({
            'fixture': fixture,
            'prediction': prediction,
            'odds': odds,
            'analysis_logs': analysis_logs
        })
    
    progress_bar.empty()
    progress_text.empty()
    
    return processed_data

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

def display_matches(processed_data, engine):
    """Affiche tous les matchs avec leurs prédictions (fallback)."""
    total_matches = sum(len(fixtures) for fixtures in processed_data.values())
    st.success(f"{total_matches} matchs trouvés avec prédictions en cache !")
    
    for league_name, fixtures_data in processed_data.items():
        st.subheader(f"🏆 {league_name}")
        
        for match_data in fixtures_data:
            fixture = match_data['fixture']
            prediction = match_data['prediction']
            odds = match_data['odds']
            analysis_logs = match_data['analysis_logs']
            
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            
            # Container pour chaque match
            with st.container():
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
                
                st.write(f"**📍 {fixture['fixture']['venue']['name']}, {fixture['fixture']['venue']['city']}**")
                
                if st.checkbox(f"Voir l'analyse détaillée", key=f"analysis_{fixture['fixture']['id']}"):
                    st.text_area("Logs d'analyse", value="\n".join(analysis_logs), height=100, key=f"logs_{fixture['fixture']['id']}")
                
                st.divider()

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Jules' Football Predictor", page_icon="⚽", layout="wide")
    
    engine = get_db_engine()
    init_db(engine)

    st.title("🔮 Jules' Football Predictor")
    st.header(f"Matchs du Jour avec Prédictions ({datetime.today().strftime('%d/%m/%Y')})")

    # PRIORITÉ 1 : Vérifier d'abord la base de données (GitHub Actions)
    db_predictions = load_predictions_from_db_for_today(engine)
    
    if db_predictions:
        # ✅ Prédictions trouvées dans la DB (générées par GitHub Actions)
        display_predictions_from_db(db_predictions, engine)
        
        # Option pour forcer le rechargement manuel
        if st.button("🔄 Générer de nouvelles prédictions manuellement"):
            st.experimental_rerun()
            
    else:
        # PRIORITÉ 2 : Fallback sur le système de cache local
        st.info("⚠️ Aucune prédiction automatique trouvée. Vérification du cache local...")
        
        cache_data = load_cache()
        
        if cache_data:
            # Cache valide trouvé
            st.info(f"📦 Prédictions chargées depuis le cache local (dernière mise à jour: {datetime.fromisoformat(cache_data['timestamp']).strftime('%H:%M:%S')})")
            display_matches(cache_data['data'], engine)
            
            # Option pour forcer le rechargement
            if st.button("🔄 Forcer le rechargement des prédictions"):
                st.experimental_rerun()
        else:
            # PRIORITÉ 3 : Génération manuelle (dernier recours)
            st.warning("⏳ Aucune prédiction trouvée. Génération manuelle en cours...")
            
            with st.spinner("Chargement des matchs et génération des prédictions..."):
                try:
                    processed_data = process_all_fixtures()
                    
                    if not processed_data:
                        st.warning("Aucun match trouvé pour aujourd'hui.")
                        return
                    
                    # Sauvegarder dans le cache
                    save_cache(processed_data)
                    st.success("✅ Prédictions générées et mises en cache !")
                    
                    # Afficher les résultats
                    display_matches(processed_data, engine)
                    
                except Exception as e:
                    st.error(f"Erreur lors de la génération des prédictions: {e}")

if __name__ == "__main__":
    main()