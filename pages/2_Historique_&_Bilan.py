import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import api_client

# --- DATABASE ---
@st.cache_resource
def get_db_engine():
    """Crée et met en cache le moteur de base de données SQLAlchemy."""
    return create_engine("sqlite:///predictions.db")

def update_match_results():
    """Met à jour les résultats des matchs terminés."""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        # Récupérer tous les matchs PENDING des 7 derniers jours
        seven_days_ago = datetime.now() - timedelta(days=7)
        pending_predictions = session.execute(
            text("""
                SELECT fixture_id, predicted_outcome 
                FROM predictions 
                WHERE status = 'PENDING' 
                AND prediction_ts >= :seven_days_ago
            """),
            {"seven_days_ago": seven_days_ago}
        ).fetchall()
        
        updated_count = 0
        
        for pred in pending_predictions:
            fixture_id = pred[0]
            predicted_outcome = pred[1]
            
            try:
                # Récupérer le résultat du match depuis l'API
                result_data = api_client.get_fixture_result(fixture_id)
                
                if result_data and result_data.get('response'):
                    fixture_info = result_data['response'][0]
                    
                    # Vérifier si le match est terminé
                    if fixture_info['fixture']['status']['short'] in ['FT', 'AET', 'PEN']:
                        home_goals = fixture_info['goals']['home']
                        away_goals = fixture_info['goals']['away']
                        
                        # Déterminer le résultat réel
                        if home_goals > away_goals:
                            actual_result = "Victoire Domicile"
                        elif away_goals > home_goals:
                            actual_result = "Victoire Extérieur"
                        else:
                            actual_result = "Match Nul"
                        
                        # Déterminer si la prédiction était correcte
                        if predicted_outcome == actual_result:
                            status = "CORRECT"
                        else:
                            status = "INCORRECT"
                        
                        # Mettre à jour en base de données
                        session.execute(
                            text("""
                                UPDATE predictions 
                                SET status = :status
                                WHERE fixture_id = :fixture_id
                            """),
                            {
                                "status": status,
                                "fixture_id": fixture_id
                            }
                        )
                        updated_count += 1
                        
            except Exception as e:
                # En cas d'erreur, passer au suivant
                continue
        
        session.commit()
        return updated_count

# Ajouter les colonnes manquantes à la table (mise à jour du schéma)
def update_db_schema():
    """Met à jour le schéma de la base de données."""
    engine = get_db_engine()
    with engine.connect() as connection:
        try:
            # Vérifier si les colonnes existent déjà
            result = connection.execute(text("PRAGMA table_info(predictions)"))
            columns = [row[1] for row in result.fetchall()]
            
            # Ajouter les nouvelles colonnes si elles n'existent pas
            if 'actual_result' not in columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN actual_result TEXT"))
            if 'home_score' not in columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN home_score INTEGER"))
            if 'away_score' not in columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN away_score INTEGER"))
            connection.commit()
        except Exception as e:
            # Les colonnes existent déjà ou autre erreur
            pass

# --- UI ---
st.set_page_config(page_title="Historique & Bilan", page_icon="📊", layout="wide")
st.title("📊 Historique & Bilan des Prédictions")

engine = get_db_engine()

# Mettre à jour le schéma de la DB
update_db_schema()

# Bouton pour mettre à jour les résultats
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Mettre à jour les résultats"):
        with st.spinner("Mise à jour des résultats en cours..."):
            updated = update_match_results()
            if updated > 0:
                st.success(f"✅ {updated} résultats mis à jour !")
                st.rerun()
            else:
                st.info("ℹ️ Aucun nouveau résultat à mettre à jour.")

try:
    with engine.connect() as connection:
        # Vérifier d'abord quelles colonnes existent
        result = connection.execute(text("PRAGMA table_info(predictions)"))
        columns = [row[1] for row in result.fetchall()]
        
        # Construire la requête en fonction des colonnes disponibles
        base_columns = "id, prediction_ts, fixture_id, match_desc, predicted_outcome, odds_home, odds_draw, odds_away, status"
        
        if 'actual_result' in columns:
            query = f"SELECT {base_columns}, actual_result FROM predictions ORDER BY prediction_ts DESC"
        else:
            query = f"SELECT {base_columns} FROM predictions ORDER BY prediction_ts DESC"
        
        predictions_df = pd.read_sql(query, connection)
    
    # --- Bilan Global ---
    st.header("📈 Bilan Global")
    
    if len(predictions_df) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        total_predictions = len(predictions_df)
        correct_predictions = len(predictions_df[predictions_df['status'] == 'CORRECT'])
        incorrect_predictions = len(predictions_df[predictions_df['status'] == 'INCORRECT'])
        pending_predictions = len(predictions_df[predictions_df['status'] == 'PENDING'])
        
        with col1:
            st.metric(label="Total Prédictions", value=total_predictions)
        
        with col2:
            st.metric(label="✅ Correctes", value=correct_predictions)
        
        with col3:
            st.metric(label="❌ Incorrectes", value=incorrect_predictions)
        
        with col4:
            st.metric(label="⏳ En attente", value=pending_predictions)
        
        # Pourcentage de réussite
        if (correct_predictions + incorrect_predictions) > 0:
            success_rate = (correct_predictions / (correct_predictions + incorrect_predictions)) * 100
            st.metric(
                label="🎯 Taux de Réussite", 
                value=f"{success_rate:.1f}%",
                delta=f"{success_rate - 50:.1f}% vs hasard" if success_rate != 50 else None
            )
        
        # Graphique de répartition
        if correct_predictions + incorrect_predictions > 0:
            st.subheader("📊 Répartition des Résultats")
            chart_data = pd.DataFrame({
                'Statut': ['Correctes', 'Incorrectes', 'En attente'],
                'Nombre': [correct_predictions, incorrect_predictions, pending_predictions]
            })
            
            st.bar_chart(chart_data.set_index('Statut')['Nombre'])

    # --- Historique ---
    st.header("📝 Historique des prédictions")
    
    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filtrer par statut", 
            ["Tous", "PENDING", "CORRECT", "INCORRECT"]
        )
    
    with col2:
        days_filter = st.selectbox(
            "Période", 
            ["Tous", "7 derniers jours", "30 derniers jours"]
        )
    
    # Appliquer les filtres
    filtered_df = predictions_df.copy()
    
    if status_filter != "Tous":
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
    if days_filter == "7 derniers jours":
        seven_days_ago = datetime.now() - timedelta(days=7)
        filtered_df = filtered_df[pd.to_datetime(filtered_df['prediction_ts']) >= seven_days_ago]
    elif days_filter == "30 derniers jours":
        thirty_days_ago = datetime.now() - timedelta(days=30)
        filtered_df = filtered_df[pd.to_datetime(filtered_df['prediction_ts']) >= thirty_days_ago]
    
    # Affichage du tableau
    st.dataframe(
        filtered_df,
        column_config={
            "id": "ID",
            "prediction_ts": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm"),
            "fixture_id": "ID Match",
            "match_desc": "Match",
            "predicted_outcome": "Prédiction",
            "actual_result": "Résultat Réel",
            "odds_home": st.column_config.NumberColumn("Cote 1", format="%.2f"),
            "odds_draw": st.column_config.NumberColumn("Cote X", format="%.2f"),
            "odds_away": st.column_config.NumberColumn("Cote 2", format="%.2f"),
            "status": "Statut"
        },
        use_container_width=True,
        hide_index=True,
    )

except Exception as e:
    st.warning("La base de données de l'historique est vide ou n'a pas pu être lue. Faites une prédiction pour commencer.")
    st.error(f"Erreur: {e}")