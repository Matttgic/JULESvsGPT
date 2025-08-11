import streamlit as st
from datetime import datetime
import pandas as pd
import api_client
import prediction_engine

# Pour l'instant, on garde la liste des ligues ici.
# On pourrait la déplacer ou la charger depuis une source externe plus tard.
MAJOR_LEAGUES = {
    "Premier League": 39,
    "Ligue 1": 61,
    "Bundesliga": 78,
    "Serie A": 135,
    "La Liga": 140,
    "UEFA Champions League": 2,
    "UEFA Europa League": 3,
}

# Initialisation de la connexion à la base de données
conn = st.connection("predictions_db", type="sql", url="sqlite:///predictions.db")

# Fonction pour créer la table si elle n'existe pas
def init_db():
    with conn.session as s:
        s.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY,
                prediction_ts TIMESTAMP,
                fixture_id INTEGER,
                match_desc TEXT,
                predicted_outcome TEXT,
                odds_home REAL,
                odds_draw REAL,
                odds_away REAL,
                status TEXT DEFAULT 'PENDING'
            )
        """)

# Fonction pour charger les matchs du jour
@st.cache_data(ttl=3600) # Cache les résultats pour 1 heure
def load_fixtures_today():
    today_str = datetime.today().strftime('%Y-%m-%d')
    all_fixtures = []

    # Logique pour calculer la saison
    match_date = datetime.strptime(today_str, '%Y-%m-%d')
    season = match_date.year - 1 if match_date.month < 7 else match_date.year

    for league_name, league_id in MAJOR_LEAGUES.items():
        fixtures_data = api_client.get_fixtures_for_date(today_str, league_id, season)
        if fixtures_data and fixtures_data.get('response'):
            all_fixtures.extend(fixtures_data['response'])
    return all_fixtures

def main():
    st.set_page_config(page_title="Jules' Football Predictor", page_icon="⚽")

    # Initialise la base de données au démarrage
    init_db()

    st.title("🔮 Jules' Football Predictor")
    st.header("Matchs du Jour")

    try:
        fixtures_today = load_fixtures_today()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des matchs. La clé API est-elle correcte ?\n\n{e}")
        return

    if not fixtures_today:
        st.warning("Aucun match trouvé dans les grands championnats pour aujourd'hui.")
        return

    st.success(f"{len(fixtures_today)} matchs trouvés pour aujourd'hui.")

    for fixture in fixtures_today:
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']

            with st.expander(f"⚽ {home_team} vs {away_team}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.image(fixture['teams']['home']['logo'], width=60)
                    st.write(f"**{home_team}**")
                with col2:
                    st.write("vs")
                with col3:
                    st.image(fixture['teams']['away']['logo'], width=60)
                    st.write(f"**{away_team}**")

                st.write(f"**Stade :** {fixture['fixture']['venue']['name']}, {fixture['fixture']['venue']['city']}")
                st.write(f"**Heure :** {datetime.fromtimestamp(fixture['fixture']['timestamp']).strftime('%H:%M')}")

                # Bouton de prédiction
                if st.button("Lancer la prédiction", key=f"predict_{fixture['fixture']['id']}"):
                    with st.spinner("Analyse du match en cours..."):
                        prediction, analysis_logs = prediction_engine.predict_match(fixture)
                        odds_data = api_client.get_odds(fixture['fixture']['id'], 8) # 8 = Bet365

                        st.subheader("Résultats de l'analyse")

                        # Affichage de la prédiction
                        st.success(f"**Prédiction : {prediction}**")

                        # Affichage des détails de l'analyse
                        with st.expander("Voir le détail de l'analyse"):
                            for log in analysis_logs:
                                st.text(log)

                        # Affichage des cotes
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
                                pass # Erreur silencieuse si les données ne sont pas là

                        st.write("**Cotes (Bet365) :**")
                        if parsed_odds:
                            col1, col2, col3 = st.columns(3)
                            col1.metric(label=f"Victoire {home_team}", value=parsed_odds['home'])
                            col2.metric(label="Match Nul", value=parsed_odds['draw'])
                            col3.metric(label=f"Victoire {away_team}", value=parsed_odds['away'])

                            # Sauvegarde de la prédiction en base de données
                            with conn.session as s:
                                s.execute(
                                    'INSERT INTO predictions (prediction_ts, fixture_id, match_desc, predicted_outcome, odds_home, odds_draw, odds_away) VALUES (:ts, :fid, :desc, :pred, :oh, :od, :oa)',
                                    params=dict(
                                        ts=datetime.now(),
                                        fid=fixture['fixture']['id'],
                                        desc=f"{home_team} vs {away_team}",
                                        pred=prediction,
                                        oh=float(parsed_odds['home']),
                                        od=float(parsed_odds['draw']),
                                        oa=float(parsed_odds['away'])
                                    )
                                )
                                s.commit()
                            st.toast("Prédiction sauvegardée dans l'historique !")
                        else:
                            st.warning("Cotes non disponibles pour ce match.")

if __name__ == "__main__":
    main()
