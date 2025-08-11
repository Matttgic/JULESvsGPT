# 🔮 Jules' Football Predictor (Streamlit Edition)

Ce projet est une application web conçue pour prédire les résultats de matchs de football et afficher les cotes, reconstruite avec [Streamlit](https://streamlit.io/) pour une interface utilisateur interactive et un déploiement simplifié.

## 🏆 Compétition
Ce projet a été réalisé par Jules, une IA ingénieure logicielle, dans le cadre d'une compétition amicale avec une autre IA pour créer le meilleur système de prédiction de paris sportifs. Cette version inclura un historique des prédictions pour suivre les performances.

## ✨ Fonctionnalités
- **Interface Interactive** : Une interface simple et claire construite avec Streamlit.
- **Modèle de Prédiction v1.0** : Prédiction de matchs basée sur une analyse pondérée de la **forme** récente des équipes et de l'historique des **confrontations directes (H2H)**.
- **Affichage des Cotes** : Intègre et affiche les cotes du bookmaker Bet365 pour chaque match analysé.
- **Transparence** : Le programme affiche les détails de l'analyse (scores de forme, H2H, etc.) pour que l'utilisateur comprenne la logique derrière chaque prédiction.
- **Déploiement Simplifié** : Conçu pour un déploiement en un clic sur [Streamlit Community Cloud](https://streamlit.io/cloud).

---

## 🚀 Instructions

### 1. Clé API
L'accès à l'API `api-football` nécessite une clé personnelle. L'application la lit depuis une variable d'environnement Streamlit Secrets.

### 2. Lancement Local
Pour faire tourner l'application sur votre machine :
1.  **Installez les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configurez votre clé API localement :**
    Créez un fichier `.streamlit/secrets.toml` et ajoutez-y votre clé :
    ```toml
    API_FOOTBALL_KEY = "VOTRE_CLE_API_PERSONNELLE"
    ```
    *Remplacez `VOTRE_CLE_API_PERSONNELLE` par la clé que vous avez obtenue sur [RapidAPI](https://rapidapi.com/api-sports/api/api-football).*

3.  **Lancez l'application :**
    ```bash
    streamlit run app.py
    ```

### 3. Déploiement sur Streamlit Cloud
1.  **Poussez ce code** sur votre propre dépôt GitHub.
2.  **Créez un compte** sur [Streamlit Community Cloud](https://streamlit.io/cloud).
3.  Cliquez sur **"New app"** et connectez votre dépôt GitHub.
4.  Dans les **"Advanced settings"**, ajoutez le secret `API_FOOTBALL_KEY` avec votre clé API comme valeur.
5.  Cliquez sur **"Deploy!"**. L'application sera disponible sur une URL publique.
