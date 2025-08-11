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

def main():
    st.set_page_config(page_title="Jules' Football Predictor", page_icon="⚽")

    st.title("🔮 Jules' Football Predictor")
    st.write("Sélectionnez un championnat et une date pour voir les matchs et obtenir des prédictions.")

    # --- Section de sélection ---
    st.header("1. Choisissez un match")

    col1, col2 = st.columns(2)

    with col1:
        league_name = st.selectbox(
            "Championnat",
            options=list(MAJOR_LEAGUES.keys())
        )

    with col2:
        selected_date = st.date_input(
            "Date",
            value=datetime.today(),
            min_value=datetime(2020, 1, 1)
        )

    league_id = MAJOR_LEAGUES[league_name]
    date_str = selected_date.strftime('%Y-%m-%d')

    if st.button("Voir les matchs"):
        # Logique pour calculer la saison
        match_date = datetime.strptime(date_str, '%Y-%m-%d')
        season = match_date.year - 1 if match_date.month < 7 else match_date.year

        with st.spinner(f"Recherche des matchs pour le {date_str}..."):
            fixtures_data = api_client.get_fixtures_for_date(date_str, league_id, season)

            if fixtures_data and fixtures_data.get('response'):
                fixtures = fixtures_data['response']
                st.session_state.fixtures = fixtures # Sauvegarde dans l'état de la session
            else:
                fixtures = []
                st.session_state.fixtures = []

        if not st.session_state.fixtures:
            st.warning("Aucun match trouvé pour cette date et ce championnat.")
        else:
            st.success(f"{len(st.session_state.fixtures)} matchs trouvés !")

    # --- Section d'affichage des matchs ---
    if 'fixtures' in st.session_state and st.session_state.fixtures:
        st.header("2. Résultats de la recherche")
        for fixture in st.session_state.fixtures:
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
                        else:
                            st.warning("Cotes non disponibles pour ce match.")

if __name__ == "__main__":
    main()
