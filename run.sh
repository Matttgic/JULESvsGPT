#!/bin/bash

# Script pour configurer et lancer l'application de prédiction de football.

# 1. Configuration de la clé API
# Le script lit la clé API depuis une variable d'environnement nommée API_FOOTBALL_KEY.
# Si elle n'est pas définie, le script en exporte une fausse pour permettre à l'application de démarrer.
# REMPLACEZ "VOTRE_CLE_API" ci-dessous par votre véritable clé API.
if [ -z "$API_FOOTBALL_KEY" ]; then
  export API_FOOTBALL_KEY="VOTRE_CLE_API"
  echo "Clé API non trouvée. Utilisation d'une clé de remplacement."
  echo "Pour utiliser l'application, veuillez définir la variable d'environnement API_FOOTBALL_KEY."
fi

# 2. Installation des dépendances
echo "Installation des dépendances depuis requirements.txt..."
pip install -r requirements.txt

# 3. Lancement de l'application Flask
echo "Lancement de l'application sur http://0.0.0.0:5001"
echo "Appuyez sur Ctrl+C pour arrêter le serveur."
python app.py
