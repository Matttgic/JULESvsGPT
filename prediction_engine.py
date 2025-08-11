Fichier : prediction_engine.py

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
        winner_id = None
        # La structure de la réponse pour 'winner' peut être différente
        if 'winner' in match['teams']['home'] and match['teams']['home']['winner']:
            winner_id = match['teams']['home']['id']
        elif 'winner' in match['teams']['away'] and match['teams']['away']['winner']:
            winner_id = match['teams']['away']['id']

        # Gestion des cas où 'winner' est un booléen ou l'ID n'est pas présent
        if winner_id is None:
             # Tentative de déduire le vainqueur par les buts si 'winner' n'est pas clair
            if match['goals']['home'] > match['goals']['away']:
                winner_id = match['teams']['home']['id']
            elif match['goals']['home'] < match['goals']['away']:
                winner_id = match['teams']['away']['id']

        if winner_id == home_team_id:
            home_score += 2
        elif winner_id is None: # Match nul
            home_score += 1
        else: # Défaite
            home_score -= 2
            
    return home_score

def _calculate_form_score(team_id):
    """Calcule un score de forme basé sur les 5 derniers matchs."""
    form_score = 0
    last_fixtures = api_client.get_last_n_fixtures(team_id, n=5)
    
    if not last_fixtures or not last_fixtures.get('response'):
        return form_score

    for match in last_fixtures['response']:
        # Logique similaire à H2H pour déterminer le vainqueur
        winner_id = None
        if match['teams']['home']['winner']:
            winner_id = match['teams']['home']['id']
        elif match['teams']['away']['winner']:
            winner_id = match['teams']['away']['id']

        if winner_id is None:
            if match['goals']['home'] > match['goals']['away']:
                winner_id = match['teams']['home']['id']
            elif match['goals']['home'] < match['goals']['away']:
                winner_id = match['teams']['away']['id']

        if winner_id == team_id:
            form_score += 2 # Victoire
        elif winner_id is None: # Match nul
            form_score += 1
        # Aucun point pour une défaite
        
    return form_score

def predict_match(fixture):
    """
    Analyse un match et prédit son issue.
    
    Args:
        fixture (dict): Un dictionnaire représentant un match, venant de l'API.
        
    Returns:
        str: La prédiction ("Victoire Domicile", "Match Nul", "Victoire Extérieur").
    """
    home_team_id = fixture['teams']['home']['id']
    away_team_id = fixture['teams']['away']['id']
    
    home_team_name = fixture['teams']['home']['name']
    away_team_name = fixture['teams']['away']['name']

    print(f"\n--- Analyse du match : {home_team_name} vs {away_team_name} ---")

    # 1. Calcul du score de forme
    home_form_score = _calculate_form_score(home_team_id)
    away_form_score = _calculate_form_score(away_team_id)
    print(f"Score de Forme : {home_team_name} ({home_form_score}) vs {away_team_name} ({away_form_score})")
    
    # 2. Calcul du score H2H (Head-to-Head)
    h2h_data = api_client.get_head_to_head(home_team_id, away_team_id)
    h2h_score = _calculate_h2h_score(h2h_data, home_team_id)
    print(f"Score H2H (avantage {home_team_name}): {h2h_score}")

    # 3. Calcul du score final et prédiction
    final_home_score = (home_form_score * 0.7) + (h2h_score * 0.3)
    final_away_score = away_form_score * 0.7

    print(f"Score Final Pondéré : {home_team_name} ({final_home_score:.2f}) vs {away_team_name} ({final_away_score:.2f})")

    # Logique de décision
    if final_home_score > final_away_score + 1:
        return f"Victoire {home_team_name}"
    elif final_away_score > final_home_score + 1:
        return f"Victoire {away_team_name}"
    else:
        return "Match Nul"
