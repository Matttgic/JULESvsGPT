# Fichier : config.py

# Fichier de configuration

import streamlit as st

# Clé API pour api-football
# La clé est lue depuis les secrets Streamlit (fichier secrets.toml ou secrets du cloud)
try:
    API_KEY = st.secrets["API_FOOTBALL_KEY"]
except FileNotFoundError:
    # Permet à l'app de ne pas planter si le fichier secrets.toml n'existe pas
    # lors d'un premier lancement local, mais les appels API échoueront.
    API_KEY = "VOTRE_CLE_API_MANQUANTE"

# URL de base de l'API v3
API_HOST = "api-football-v1.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}/v3"

# ID du bookmaker à utiliser pour les cotes (Bet365)
BOOKMAKER_ID = 8
