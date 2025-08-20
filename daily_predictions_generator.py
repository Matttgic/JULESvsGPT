#!/usr/bin/env python3
"""
Générateur automatique de prédictions quotidiennes
Utilise le même moteur que Streamlit mais sauvegarde dans des fichiers CSV
"""

import os
import sys
import requests
import pandas as pd
import logging
from datetime import datetime, date, timedelta
import json
from typing import Dict, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_predictions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyPredictionsGenerator:
    """Générateur de prédictions quotidiennes pour GitHub Actions"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }
        
        # Configuration des ligues principales
        self.leagues = {
            "UEFA Champions League": 2,
            "UEFA Europa League": 3,
            "Premier League": 39,
            "Championship": 40,
            "Ligue 1": 61,
            "Ligue 2": 62,
            "Bundesliga": 78,
            "2. Bundesliga": 79,
            "Eredivisie": 88,
            "Primeira Liga": 94,
            "Serie A": 135,
            "Serie B": 136,
            "La Liga": 140,
            "Segunda División": 141,
            "Jupiler Pro League": 144,
            "Major League Soccer": 253,
            "Liga MX": 262
        }
        
        self.today = date.today()
        self.predictions_folder = "data/predictions"
        
        # Statistiques
        self.stats = {
            'total_leagues_checked': 0,
            'total_matches_found': 0,
            'total_predictions_generated': 0,
            'api_calls': 0,
            'failed_requests': 0
        }
    
    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Effectue une requête à l'API avec gestion d'erreurs"""
        url = f"{self.base_url}/{endpoint}"
        self.stats['api_calls'] += 1
        
        try:
            logger.debug(f"API Request #{self.stats['api_calls']}: {endpoint}")
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.error(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                self.stats['failed_requests'] += 1
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur de requête: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    def get_fixtures_for_date(self, date_str: str, league_id: int, season: int) -> Optional[Dict]:
        """Récupère les matchs pour une date, ligue et saison"""
        params = {'date': date_str, 'league': league_id, 'season': season}
        return self.make_api_request('fixtures', params)
    
    def get_team_last_fixtures(self, team_id: int, n: int = 5) -> Optional[Dict]:
        """Récupère les n derniers matchs d'une équipe"""
        params = {'team': team_id, 'last': n}
        return self.make_api_request('fixtures', params)
    
    def get_head_to_head(self, team1_id: int, team2_id: int) -> Optional[Dict]:
        """Récupère l'historique des confrontations"""
        h2h_str = f"{team1_id}-{team2_id}"
        params = {'h2h': h2h_str}
        return self.make_api_request('fixtures/headtohead', params)
    
    def get_odds(self, fixture_id: int, bookmaker_id: int = 8) -> Optional[Dict]:
        """Récupère les cotes pour un match"""
        params = {'fixture': fixture_id, 'bookmaker': bookmaker_id}
        return self.make_api_request('odds', params)
    
    def calculate_form_score(self, team_id: int) -> float:
        """Calcule le score de forme d'une équipe (derniers 5 matchs)"""
        form_score = 0
        last_fixtures = self.get_team_last_fixtures(team_id, 5)
        
        if not last_fixtures or not last_fixtures.get('response'):
            return form_score

        for match in last_fixtures['response']:
            goals_home = match['goals']['home']
            goals_away = match['goals']['away']

            # Ignorer les matchs non terminés
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
            # 0 point pour une défaite
                
        return form_score
    
    def calculate_h2h_score(self, h2h_data: Dict, home_team_id: int) -> float:
        """Calcule le score basé sur l'historique des confrontations"""
        home_score = 0
        if not h2h_data or not h2h_data.get('response'):
            return home_score

        for match in h2h_data['response']:
            goals_home = match['goals']['home']
            goals_away = match['goals']['away']

            # Ignorer les matchs non terminés
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
    
    def predict_match(self, fixture: Dict) -> tuple[str, List[str], float]:
        """Génère une prédiction pour un match"""
        home_team_id = fixture['teams']['home']['id']
        away_team_id = fixture['teams']['away']['id']
        
        home_team_name = fixture['teams']['home']['name']
        away_team_name = fixture['teams']['away']['name']

        analysis_logs = []
        analysis_logs.append(f"--- Analyse: {home_team_name} vs {away_team_name} ---")

        # 1. Calcul du score de forme
        home_form_score = self.calculate_form_score(home_team_id)
        away_form_score = self.calculate_form_score(away_team_id)
        analysis_logs.append(f"Forme: {home_team_name} ({home_form_score}) vs {away_team_name} ({away_form_score})")
        
        # 2. Calcul du score H2H
        h2h_data = self.get_head_to_head(home_team_id, away_team_id)
        h2h_score = self.calculate_h2h_score(h2h_data, home_team_id)
        analysis_logs.append(f"H2H (avantage {home_team_name}): {h2h_score}")

        # 3. Calcul final avec pondération
        final_home_score = (home_form_score * 0.7) + (h2h_score * 0.3)
        final_away_score = away_form_score * 0.7
        analysis_logs.append(f"Score Final: {home_team_name} ({final_home_score:.2f}) vs {away_team_name} ({final_away_score:.2f})")

        # 4. Logique de décision
        confidence = 0.5  # Confiance de base
        
        if final_home_score > final_away_score + 1.5:
            prediction = "Victoire Domicile"
            confidence = min(0.9, 0.5 + (final_home_score - final_away_score) * 0.1)
        elif final_away_score > final_home_score + 1.5:
            prediction = "Victoire Extérieur" 
            confidence = min(0.9, 0.5 + (final_away_score - final_home_score) * 0.1)
        else:
            prediction = "Match Nul"
            confidence = 0.6  # Légèrement plus confiant pour les nuls équilibrés

        analysis_logs.append(f"Prédiction: {prediction} (Confiance: {confidence:.2f})")
        return prediction, analysis_logs, confidence
    
    def get_prediction_and_odds(self, fixture: Dict) -> tuple[str, Optional[Dict], List[str], float]:
        """Génère prédiction et récupère les cotes"""
        prediction, analysis_logs, confidence = self.predict_match(fixture)
        
        # Récupérer les cotes
        odds_data = self.get_odds(fixture['fixture']['id'])
        parsed_odds = None
        
        if odds_data and odds_data.get('response'):
            try:
                bookmaker = odds_data['response'][0]['bookmakers'][0]
                bet = next((b for b in bookmaker['bets'] if b['name'] == 'Match Winner'), None)
                if bet:
                    parsed_odds = {
                        'home': next((o['odd'] for o in bet['values'] if o['value'] == 'Home'), None),
                        'draw': next((o['odd'] for o in bet['values'] if o['value'] == 'Draw'), None), 
                        'away': next((o['odd'] for o in bet['values'] if o['value'] == 'Away'), None),
                    }
            except (IndexError, KeyError):
                analysis_logs.append("⚠️ Erreur récupération cotes")
        else:
            analysis_logs.append("⚠️ Aucune cote disponible")
        
        return prediction, parsed_odds, analysis_logs, confidence
    
    def load_fixtures_today(self) -> List[Dict]:
        """Charge tous les matchs du jour"""
        today_str = self.today.strftime('%Y-%m-%d')
        all_fixtures = []
        season = self.today.year - 1 if self.today.month < 7 else self.today.year
        
        logger.info(f"🔍 Recherche des matchs pour le {today_str} (saison {season})")
        
        for league_name, league_id in self.leagues.items():
            try:
                fixtures_data = self.get_fixtures_for_date(today_str, league_id, season)
                self.stats['total_leagues_checked'] += 1
                
                if fixtures_data and fixtures_data.get('response'):
                    league_matches = len(fixtures_data['response'])
                    logger.info(f"🏆 {league_name}: {league_matches} matchs trouvés")
                    all_fixtures.extend(fixtures_data['response'])
                    self.stats['total_matches_found'] += league_matches
                else:
                    logger.debug(f"ℹ️ {league_name}: Aucun match")
                    
            except Exception as e:
                logger.error(f"❌ Erreur pour {league_name}: {e}")
                continue
        
        logger.info(f"📊 Total: {len(all_fixtures)} matchs trouvés dans {self.stats['total_leagues_checked']} ligues")
        return all_fixtures
    
    def process_and_save_predictions(self, fixtures: List[Dict]) -> None:
        """Traite tous les matchs et sauvegarde les prédictions"""
        if not fixtures:
            logger.warning("❌ Aucun match à traiter")
            return
        
        predictions_data = []
        today_str = self.today.strftime('%Y-%m-%d')
        
        logger.info(f"🔮 Génération des prédictions pour {len(fixtures)} matchs...")
        
        for i, fixture in enumerate(fixtures, 1):
            try:
                logger.info(f"⚽ [{i}/{len(fixtures)}] {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}")
                
                prediction, odds, analysis_logs, confidence = self.get_prediction_and_odds(fixture)
                
                # Préparer les données
                match_data = {
                    'prediction_date': today_str,
                    'prediction_timestamp': datetime.now().isoformat(),
                    'fixture_id': fixture['fixture']['id'],
                    'league_id': fixture['league']['id'],
                    'league_name': fixture['league']['name'],
                    'match_datetime': datetime.fromtimestamp(fixture['fixture']['timestamp']).isoformat(),
                    'home_team_id': fixture['teams']['home']['id'],
                    'home_team_name': fixture['teams']['home']['name'],
                    'away_team_id': fixture['teams']['away']['id'], 
                    'away_team_name': fixture['teams']['away']['name'],
                    'venue_name': fixture['fixture']['venue']['name'],
                    'venue_city': fixture['fixture']['venue']['city'],
                    'predicted_outcome': prediction,
                    'confidence': confidence,
                    'match_desc': f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}",
                    'status': 'PENDING',
                    'source': 'GitHub Actions',
                    'analysis_summary': ' | '.join(analysis_logs[-3:])  # Dernières 3 lignes d'analyse
                }
                
                # Ajouter les cotes si disponibles
                if odds:
                    match_data.update({
                        'odds_home': odds.get('home'),
                        'odds_draw': odds.get('draw'),
                        'odds_away': odds.get('away')
                    })
                else:
                    match_data.update({
                        'odds_home': None,
                        'odds_draw': None,
                        'odds_away': None
                    })
                
                predictions_data.append(match_data)
                self.stats['total_predictions_generated'] += 1
                
                # Pause pour ne pas surcharger l'API
                if i % 10 == 0:
                    logger.info("⏱️ Pause de 2 secondes...")
                    import time
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Erreur traitement match {fixture['fixture']['id']}: {e}")
                continue
        
        # Sauvegarder les prédictions
        if predictions_data:
            self.save_predictions_to_csv(predictions_data, today_str)
        else:
            logger.warning("⚠️ Aucune prédiction générée")
    
    def save_predictions_to_csv(self, predictions: List[Dict], date_str: str) -> None:
        """Sauvegarde les prédictions dans un fichier CSV"""
        
        # Créer le dossier si nécessaire
        os.makedirs(self.predictions_folder, exist_ok=True)
        
        # Nom du fichier avec timestamp
        timestamp = datetime.now().strftime('%H%M')
        filename = f"predictions_{date_str}_{timestamp}.csv"
        filepath = os.path.join(self.predictions_folder, filename)
        
        try:
            df = pd.DataFrame(predictions)
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            logger.info(f"💾 Prédictions sauvegardées: {filepath}")
            logger.info(f"📊 {len(predictions)} prédictions dans le fichier")
            
            # Créer aussi un fichier "latest" pour faciliter l'accès
            latest_filepath = os.path.join(self.predictions_folder, "latest_predictions.csv")
            df.to_csv(latest_filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Fichier latest mis à jour: {latest_filepath}")
            
            # Afficher un échantillon
            logger.info("🔍 Échantillon des prédictions générées:")
            sample_df = df[['match_desc', 'predicted_outcome', 'confidence', 'odds_home', 'odds_draw', 'odds_away']].head(5)
            logger.info(f"\n{sample_df.to_string(index=False)}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {e}")
    
    def run(self) -> None:
        """Exécution principale du générateur"""
        logger.info("🚀 === DÉBUT DE LA GÉNÉRATION DES PRÉDICTIONS QUOTIDIENNES ===")
        logger.info(f"📅 Date: {self.today}")
        
        start_time = datetime.now()
        
        try:
            # 1. Charger les matchs du jour
            fixtures = self.load_fixtures_today()
            
            if not fixtures:
                logger.warning("⚠️ Aucun match trouvé pour aujourd'hui")
                return
            
            # 2. Traiter et sauvegarder les prédictions
            self.process_and_save_predictions(fixtures)
            
        except Exception as e:
            logger.error(f"❌ Erreur critique: {e}")
            return
        
        # 3. Résumé final
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"\n🎉 === GÉNÉRATION TERMINÉE ===")
        logger.info(f"⏱️ Durée totale: {duration}")
        logger.info(f"🏆 Ligues vérifiées: {self.stats['total_leagues_checked']}")
        logger.info(f"⚽ Matchs trouvés: {self.stats['total_matches_found']}")
        logger.info(f"🔮 Prédictions générées: {self.stats['total_predictions_generated']}")
        logger.info(f"🌐 Requêtes API: {self.stats['api_calls']}")
        logger.info(f"❌ Requêtes échouées: {self.stats['failed_requests']}")
        
        if self.stats['total_predictions_generated'] > 0:
            success_rate = ((self.stats['api_calls'] - self.stats['failed_requests']) / self.stats['api_calls']) * 100
            logger.info(f"✅ Taux de succès API: {success_rate:.1f}%")
            logger.info(f"📁 Fichiers disponibles dans: {self.predictions_folder}/")

def main():
    """Fonction principale"""
    import os
    
    # Récupérer la clé API (essayer les deux variables)
    api_key = os.environ.get('RAPIDAPI_KEY') or os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        logger.error("⚠️ Clé API non trouvée. Vérifiez que RAPIDAPI_KEY ou API_FOOTBALL_KEY est définie dans les variables d'environnement")
        sys.exit(1)
    
    logger.info("✅ Clé API récupérée depuis les variables d'environnement")
    
    # Lancer le générateur
    generator = DailyPredictionsGenerator(api_key)
    generator.run()

if __name__ == "__main__":
    main() 
