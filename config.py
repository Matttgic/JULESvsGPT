# Fichier : config.py

# Fichier de configuration

import os

# Clé API pour api-football
# La clé est lue depuis une variable d'environnement pour plus de sécurité.
# Si la variable n'est pas définie, une valeur par défaut est utilisée.
API_KEY = os.getenv("API_FOOTBALL_KEY", "VOTRE_CLE_API")

# URL de base de l'API v3
API_HOST = "api-football-v1.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}/v3"

# ID du bookmaker à utiliser pour les cotes (Bet365)
BOOKMAKER_ID = 8
