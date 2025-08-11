import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# Fonction pour initialiser la connexion à la base de données et la mettre en cache
@st.cache_resource
def get_db_engine():
    return create_engine("sqlite:///predictions.db")

st.set_page_config(page_title="Historique & Bilan", page_icon="📊", layout="wide")

st.title("📊 Historique & Bilan des Prédictions")

engine = get_db_engine()

# Récupération des données
try:
    with engine.connect() as connection:
        predictions_df = pd.read_sql('SELECT * FROM predictions ORDER BY prediction_ts DESC', connection)

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
            "prediction_ts": st.column_config.DatetimeColumn("Date de Prédiction", format="D MMM YYYY, HH:mm"),
            "fixture_id": "ID Match",
            "match_desc": "Match",
            "predicted_outcome": "Prédiction",
            "odds_home": "Cote Domicile",
            "odds_draw": "Cote Nul",
            "odds_away": "Cote Extérieur",
            "status": "Statut"
        },
        use_container_width=True,
        hide_index=True,
    )

except Exception as e:
    st.error(f"Erreur lors de la lecture de la base de données : {e}")
    st.warning("Avez-vous déjà fait une prédiction ? L'historique est peut-être vide.")
