# Fichier : prediction_engine.py

"""
Moteur de prédiction des résultats de matchs de football.

Ce module utilisera les données collectées par l'api_client pour
calculer des probabilités et prédire l'issue des matchs.
"""
import api_client

def _calculate_h2h_score(h2h_data, home_team_id):
    """Calcule un score basé sur l'historique des confrontations."""
    home_score = 0
    if not h2h_data or not h2h_data.get('response'):
        return home_score

    for match in h2h_data['response']:
        goals_home = match['goals']['home']
        goals_away = match['goals']['away']

        # On ignore les matchs non terminés
        if goals_home is None or goals_away is None:
            continue

        winner_id = None
        if goals_home > goals_away:
            winner_id = match['teams']['home']['id']
        elif goals_away > goals_home:
            winner_id = match['teams']['away']['id']

        if winner_id == home_team_id:
            home_score += 2  # Victoire à domicile
        elif winner_id is None:  # Match nul
            home_score += 1
        else:  # Défaite à domicile
            home_score -= 2
            
    return home_score

def _calculate_form_score(team_id):
    """Calcule un score de forme basé sur les 5 derniers matchs."""
    form_score = 0
    last_fixtures = api_client.get_last_n_fixtures(team_id, n=5)
    
    if not last_fixtures or not last_fixtures.get('response'):
        return form_score

    for match in last_fixtures['response']:
        goals_home = match['goals']['home']
        goals_away = match['goals']['away']

        # On ignore les matchs non terminés
        if goals_home is None or goals_away is None:
            continue

        winner_id = None
        if goals_home > goals_away:
            winner_id = match['teams']['home']['id']
        elif goals_away > goals_home:
            winner_id = match['teams']['away']['id']

        if winner_id == team_id:
            form_score += 2  # Victoire
        elif winner_id is None:  # Match nul
            form_score += 1
        # Aucun point pour une défaite
        
    return form_score

def predict_match(fixture):
    """
    Analyse un match et prédit son issue.
    
    Args:
        fixture (dict): Un dictionnaire représentant un match, venant de l'API.
        
    Returns:
        tuple[str, list[str]]: La prédiction et une liste de logs d'analyse.
    """
    home_team_id = fixture['teams']['home']['id']
    away_team_id = fixture['teams']['away']['id']
    
    home_team_name = fixture['teams']['home']['name']
    away_team_name = fixture['teams']['away']['name']

    analysis_logs = []
    analysis_logs.append(f"--- Analyse du match : {home_team_name} vs {away_team_name} ---")

    # 1. Calcul du score de forme
    home_form_score = _calculate_form_score(home_team_id)
    away_form_score = _calculate_form_score(away_team_id)
    analysis_logs.append(f"Score de Forme : {home_team_name} ({home_form_score}) vs {away_team_name} ({away_form_score})")
    
    # 2. Calcul du score H2H (Head-to-Head)
    h2h_data = api_client.get_head_to_head(home_team_id, away_team_id)
    h2h_score = _calculate_h2h_score(h2h_data, home_team_id)
    analysis_logs.append(f"Score H2H (avantage {home_team_name}): {h2h_score}")

    # 3. Calcul du score final et prédiction
    final_home_score = (home_form_score * 0.7) + (h2h_score * 0.3)
    final_away_score = away_form_score * 0.7
    analysis_logs.append(f"Score Final Pondéré : {home_team_name} ({final_home_score:.2f}) vs {away_team_name} ({final_away_score:.2f})")

    # Logique de décision
    if final_home_score > final_away_score + 1:
        prediction = f"Victoire {home_team_name}"
    elif final_away_score > final_home_score + 1:
        prediction = f"Victoire {away_team_name}"
    else:
        prediction = "Match Nul"

    return prediction, analysis_logs
