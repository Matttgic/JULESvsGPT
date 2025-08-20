import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import api_client
import os
import glob

# --- DATABASE ---
@st.cache_resource
def get_db_engine():
    """Crée et met en cache le moteur de base de données SQLAlchemy."""
    return create_engine("sqlite:///predictions.db")

def load_github_predictions():
    """Charge toutes les prédictions depuis les fichiers CSV GitHub Actions."""
    all_predictions = []
    
    # Chercher tous les fichiers de prédictions dans le dossier data
    prediction_files = []
    
    # Patterns de recherche pour les fichiers de prédictions
    search_patterns = [
        "data/predictions/*.csv",
        "data/*predictions*.csv", 
        "predictions_*.csv",
        "daily_predictions_*.csv"
    ]
    
    for pattern in search_patterns:
        prediction_files.extend(glob.glob(pattern))
    
    if not prediction_files:
        st.info("🔍 Aucun fichier de prédictions GitHub Actions trouvé")
        return pd.DataFrame()
    
    for file_path in prediction_files:
        try:
            df = pd.read_csv(file_path)
            
            # Standardiser les colonnes si nécessaire
            if 'prediction_date' in df.columns:
                df['prediction_ts'] = pd.to_datetime(df['prediction_date'])
            
            # Ajouter la source du fichier
            df['source'] = 'GitHub Actions'
            df['source_file'] = os.path.basename(file_path)
            
            all_predictions.append(df)
            
        except Exception as e:
            st.warning(f"⚠️ Erreur lecture fichier {file_path}: {e}")
    
    if all_predictions:
        combined_df = pd.concat(all_predictions, ignore_index=True)
        return combined_df
    
    return pd.DataFrame()

def load_streamlit_predictions():
    """Charge les prédictions de la base SQLite locale."""
    engine = get_db_engine()
    
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
            
            df = pd.read_sql(query, connection)
            
            if not df.empty:
                df['source'] = 'Streamlit Local'
                df['source_file'] = 'predictions.db'
            
            return df
            
    except Exception as e:
        st.warning(f"⚠️ Erreur lecture base SQLite: {e}")
        return pd.DataFrame()

def combine_all_predictions():
    """Combine toutes les prédictions (GitHub + Streamlit)."""
    github_preds = load_github_predictions()
    streamlit_preds = load_streamlit_predictions()
    
    all_predictions = []
    
    if not github_preds.empty:
        all_predictions.append(github_preds)
        st.success(f"📊 {len(github_preds)} prédictions GitHub Actions chargées")
    
    if not streamlit_preds.empty:
        all_predictions.append(streamlit_preds)
        st.success(f"💻 {len(streamlit_preds)} prédictions Streamlit chargées")
    
    if all_predictions:
        combined = pd.concat(all_predictions, ignore_index=True, sort=False)
        
        # Standardiser les colonnes dates
        if 'prediction_ts' in combined.columns:
            combined['prediction_ts'] = pd.to_datetime(combined['prediction_ts'])
            combined = combined.sort_values('prediction_ts', ascending=False)
        
        # Supprimer les doublons potentiels (même fixture_id et même date)
        if 'fixture_id' in combined.columns and 'prediction_ts' in combined.columns:
            combined = combined.drop_duplicates(subset=['fixture_id', 'prediction_ts'], keep='first')
        
        return combined
    
    return pd.DataFrame()

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
st.set_page_config(page_title="Historique & Bilan Complet", page_icon="📊", layout="wide")
st.title("📊 Historique & Bilan Complet des Prédictions")
st.caption("Affiche TOUTES les prédictions : GitHub Actions + Streamlit Local")

# Mettre à jour le schéma de la DB
update_db_schema()

# Bouton pour recharger les données
col1, col2, col3 = st.columns([2, 1, 1])

with col2:
    if st.button("🔄 Recharger les données"):
        st.cache_data.clear()
        st.rerun()

with col3:
    if st.button("📈 Mettre à jour les résultats"):
        with st.spinner("Mise à jour des résultats en cours..."):
            updated = update_match_results()
            if updated > 0:
                st.success(f"✅ {updated} résultats mis à jour !")
                st.rerun()
            else:
                st.info("ℹ️ Aucun nouveau résultat à mettre à jour.")

# Chargement de toutes les prédictions
with st.spinner("Chargement de l'historique complet..."):
    all_predictions_df = combine_all_predictions()

if all_predictions_df.empty:
    st.warning("❌ Aucune prédiction trouvée dans les fichiers GitHub Actions ou la base Streamlit.")
    st.info("""
    **Vérifications à faire :**
    1. Les workflows GitHub Actions ont-ils générés des fichiers CSV ?
    2. Les fichiers sont-ils dans le bon dossier (data/) ?
    3. Avez-vous fait des prédictions via l'interface Streamlit ?
    """)
else:
    # --- Bilan Global ---
    st.header("📈 Bilan Global Complet")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_predictions = len(all_predictions_df)
    github_predictions = len(all_predictions_df[all_predictions_df['source'] == 'GitHub Actions']) if 'source' in all_predictions_df.columns else 0
    streamlit_predictions = len(all_predictions_df[all_predictions_df['source'] == 'Streamlit Local']) if 'source' in all_predictions_df.columns else 0
    
    with col1:
        st.metric(label="📊 Total Prédictions", value=total_predictions)
    
    with col2:
        st.metric(label="🤖 GitHub Actions", value=github_predictions)
    
    with col3:
        st.metric(label="💻 Streamlit Local", value=streamlit_predictions)
    
    with col4:
        if 'prediction_ts' in all_predictions_df.columns:
            latest_date = all_predictions_df['prediction_ts'].max()
            if pd.notna(latest_date):
                days_ago = (datetime.now() - latest_date).days
                st.metric(label="🗓️ Dernière prédiction", value=f"Il y a {days_ago} jour(s)")
    
    # Graphiques de répartition
    st.subheader("📊 Répartition par Source")
    if 'source' in all_predictions_df.columns:
        source_counts = all_predictions_df['source'].value_counts()
        st.bar_chart(source_counts)
    
    # Statistiques de performance (si disponibles)
    if 'status' in all_predictions_df.columns:
        st.subheader("🎯 Performance")
        
        performance_stats = all_predictions_df['status'].value_counts()
        
        col1, col2, col3 = st.columns(3)
        
        correct_count = performance_stats.get('CORRECT', 0)
        incorrect_count = performance_stats.get('INCORRECT', 0) 
        pending_count = performance_stats.get('PENDING', 0)
        
        with col1:
            st.metric(label="✅ Correctes", value=correct_count)
        
        with col2:
            st.metric(label="❌ Incorrectes", value=incorrect_count)
        
        with col3:
            st.metric(label="⏳ En attente", value=pending_count)
        
        if (correct_count + incorrect_count) > 0:
            success_rate = (correct_count / (correct_count + incorrect_count)) * 100
            st.metric(
                label="🏆 Taux de Réussite Global", 
                value=f"{success_rate:.1f}%",
                delta=f"{success_rate - 50:.1f}% vs hasard" if success_rate != 50 else None
            )

    # --- Historique Complet ---
    st.header("📝 Historique Complet")
    
    # Filtres avancés
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'status' in all_predictions_df.columns:
            status_options = ["Tous"] + list(all_predictions_df['status'].unique())
            status_filter = st.selectbox("Filtrer par statut", status_options)
        else:
            status_filter = "Tous"
    
    with col2:
        if 'source' in all_predictions_df.columns:
            source_options = ["Tous"] + list(all_predictions_df['source'].unique())
            source_filter = st.selectbox("Filtrer par source", source_options)
        else:
            source_filter = "Tous"
    
    with col3:
        days_filter = st.selectbox(
            "Période", 
            ["Tous", "7 derniers jours", "30 derniers jours", "90 derniers jours"]
        )
    
    # Application des filtres
    filtered_df = all_predictions_df.copy()
    
    if 'status' in filtered_df.columns and status_filter != "Tous":
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
    if 'source' in filtered_df.columns and source_filter != "Tous":
        filtered_df = filtered_df[filtered_df['source'] == source_filter]
    
    if 'prediction_ts' in filtered_df.columns and days_filter != "Tous":
        days_map = {"7 derniers jours": 7, "30 derniers jours": 30, "90 derniers jours": 90}
        if days_filter in days_map:
            cutoff_date = datetime.now() - timedelta(days=days_map[days_filter])
            filtered_df = filtered_df[pd.to_datetime(filtered_df['prediction_ts']) >= cutoff_date]
    
    # Résumé des filtres
    st.info(f"📋 Affichage de {len(filtered_df)} prédictions sur {len(all_predictions_df)} au total")
    
    # Configuration des colonnes pour l'affichage
    column_config = {}
    if 'prediction_ts' in filtered_df.columns:
        column_config["prediction_ts"] = st.column_config.DatetimeColumn("Date/Heure", format="D MMM YYYY, HH:mm")
    if 'odds_home' in filtered_df.columns:
        column_config["odds_home"] = st.column_config.NumberColumn("Cote 1", format="%.2f")
    if 'odds_draw' in filtered_df.columns:
        column_config["odds_draw"] = st.column_config.NumberColumn("Cote X", format="%.2f") 
    if 'odds_away' in filtered_df.columns:
        column_config["odds_away"] = st.column_config.NumberColumn("Cote 2", format="%.2f")
    
    # Affichage du tableau
    if not filtered_df.empty:
        st.dataframe(
            filtered_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
        )
        
        # Option de téléchargement
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="💾 Télécharger l'historique (CSV)",
            data=csv,
            file_name=f"historique_predictions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("❌ Aucune prédiction ne correspond aux filtres sélectionnés.")

    # --- Debug Info ---
    if st.checkbox("🔧 Afficher les infos de debug"):
        st.subheader("🔧 Informations de Debug")
        
        st.write("**Colonnes disponibles:**")
        st.write(list(all_predictions_df.columns))
        
        st.write("**Exemples de données:**")
        st.write(all_predictions_df.head())
        
        st.write("**Types de données:**")
        st.write(all_predictions_df.dtypes)
        
        if 'source' in all_predictions_df.columns:
            st.write("**Répartition par source:**")
            st.write(all_predictions_df['source'].value_counts())
