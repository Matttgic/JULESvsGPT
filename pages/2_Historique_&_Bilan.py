import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --- DATABASE ---
@st.cache_resource
def get_db_engine():
    """Crée et met en cache le moteur de base de données SQLAlchemy."""
    return create_engine("sqlite:///predictions.db")

# --- UI ---
st.set_page_config(page_title="Historique & Bilan", page_icon="📊", layout="wide")
st.title("📊 Historique & Bilan des Prédictions")

engine = get_db_engine()

try:
    with engine.connect() as connection:
        predictions_df = pd.read_sql('SELECT * FROM predictions ORDER BY prediction_ts DESC', connection)

    # --- Bilan ---
    st.header("Bilan Global")
    total_predictions = len(predictions_df)
    st.metric(label="Nombre total de prédictions", value=total_predictions)
    # Note: Le bilan détaillé (précision, etc.) sera ajouté dans une future version.

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

except Exception:
    st.warning("La base de données de l'historique est vide ou n'a pas pu être lue. Faites une prédiction pour commencer.")
