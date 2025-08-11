import streamlit as st
import pandas as pd

st.set_page_config(page_title="Historique & Bilan", page_icon="📊")

st.title("📊 Historique & Bilan des Prédictions")

# Initialisation de la connexion à la base de données
conn = st.connection("predictions_db", type="sql", url="sqlite:///predictions.db")

# Récupération des données
try:
    predictions_df = conn.query('SELECT * FROM predictions ORDER BY prediction_ts DESC')

    # --- Bilan ---
    st.header("Bilan Global")
    total_predictions = len(predictions_df)
    st.metric(label="Nombre total de prédictions", value=total_predictions)
    # Note: Le calcul de la précision sera ajouté dans une future étape,
    # une fois que le script de mise à jour des résultats sera en place.

    # --- Historique ---
    st.header("Historique des prédictions")
    st.dataframe(
        predictions_df,
        column_config={
            "id": "ID",
            "prediction_ts": "Date de Prédiction",
            "fixture_id": "ID Match",
            "match_desc": "Match",
            "predicted_outcome": "Prédiction",
            "odds_home": "Cote Domicile",
            "odds_draw": "Cote Nul",
            "odds_away": "Cote Extérieur",
            "status": "Statut"
        },
        use_container_width=True
    )

except Exception as e:
    st.error(f"Erreur lors de la lecture de la base de données : {e}")
    st.warning("Avez-vous déjà fait une prédiction ? L'historique est peut-être vide.")
