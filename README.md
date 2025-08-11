# Fichier : README.md

# Système de Prédiction de Paris Sportifs Football

Ce projet est une **application web** conçue pour prédire les résultats de matchs de football et afficher les cotes, le tout accessible depuis un navigateur, y compris sur smartphone.

## 🏆 Compétition
Ce projet a été réalisé par Jules, une IA ingénieure logicielle, dans le cadre d'une compétition amicale avec ChatGPT pour créer le meilleur et le plus complet des systèmes de prédiction.

## ✨ Fonctionnalités
- **Interface Web Adaptée Mobile** : Une interface simple et claire, utilisable sur n'importe quel appareil doté d'un navigateur web.
- **Modèle de Prédiction v1.0** : Prédiction de matchs basée sur une analyse pondérée de la **forme** récente des équipes et de l'historique des **confrontations directes (H2H)**.
- **Affichage des Cotes** : Intègre et affiche les cotes du bookmaker Bet365 pour chaque match analysé.
- **Transparence** : Le programme affiche les scores de forme et H2H calculés pour que l'utilisateur comprenne la logique derrière chaque prédiction.
- **Structure Modulaire** : Le code est organisé en modules clairs (`api_client`, `prediction_engine`, `app.py`), ce qui le rend facile à maintenir et à améliorer.

## 🚀 Instructions d'Installation et d'Utilisation

### Méthode 1 : Utilisation du Script `run.sh` (Recommandé)

Le moyen le plus simple de lancer l'application est d'utiliser le script `run.sh` fourni.

1.  **Configurez votre clé API** :
    Le script utilise une variable d'environnement nommée `API_FOOTBALL_KEY`. Vous pouvez la définir de manière permanente dans votre système ou la définir temporairement avant de lancer le script :
    ```bash
    export API_FOOTBALL_KEY="VOTRE_CLE_API_PERSONNELLE"
    ```
    *Remplacez `VOTRE_CLE_API_PERSONNELLE` par la clé que vous avez obtenue sur [RapidAPI](https://rapidapi.com/api-sports/api/api-football).*

2.  **Exécutez le script** :
    Ouvrez un terminal dans le répertoire du projet et lancez la commande suivante :
    ```bash
    ./run.sh
    ```
    Le script installera automatiquement les dépendances nécessaires et démarrera le serveur web.

### Méthode 2 : Manuelle

Si vous préférez lancer l'application manuellement, suivez ces étapes.

1.  **Configurez votre clé API** :
    Définissez la variable d'environnement `API_FOOTBALL_KEY` :
    ```bash
    export API_FOOTBALL_KEY="VOTRE_CLE_API_PERSONNELLE"
    ```

2.  **Installez les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

3.  **Lancez l'application** :
    ```bash
    python app.py
    ```

Dans les deux cas, l'application sera accessible à l'adresse `http://127.0.0.1:5001` dans votre navigateur.
💡 Améliorations Futures Possibles
Ce projet est une base solide. Voici quelques pistes pour le rendre encore meilleur :

Intégrer plus de données : Classements, statistiques détaillées des joueurs, informations sur les blessés et suspendus.
Affiner l'algorithme : Utiliser des modèles statistiques plus avancés ou du Machine Learning.
Déploiement Cloud : Héberger l'application sur un service cloud pour qu'elle soit accessible de n'importe où, sans avoir à lancer le serveur localement. 
