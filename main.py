#!/usr/bin/env python3
"""
Football Data Automation Bot - OPTIMIZED FOR 500 REQUESTS/MONTH
With SMART PREDICTION ENGINE
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import pytz
import logging
import time
import random

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

GMT = pytz.timezone('GMT')

# STRICT API LIMITS
API_REQUESTS_THIS_RUN = 0
MAX_API_CALLS_PER_RUN = 1

AFFILIATE_LINKS = {
    "🎰 Stake": "https://stake.com/?c=GlobalScoreUpdates",
    "📊 Linebet": "https://linebet.com?bf=695d695c66d7a_13053616523",
    "🏆 1xBet": "https://ma-1xbet.com?bf=695d66e22c1b5_7531017325"
}

TELEGRAM_CHANNEL_LINK = "https://t.me/+xAQ3DCVJa8A2ZmY8"

RAPIDAPI_HOST = "livescore6.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"

MAJOR_COMPETITIONS = [
    "Premier League", "La Liga", "Serie A", "Bundesliga",
    "Ligue 1", "Champions League", "Europa League",
    "World Cup", "Euro", "FA Cup", "Eredivisie", "Primeira Liga",
    "Saudi Pro League", "MLS", "Brasileiro Serie A"
]

# List of strong teams to bias predictions towards
POWERHOUSE_TEAMS = [
    "Manchester City", "Liverpool", "Arsenal", "Real Madrid", "Barcelona",
    "Bayern Munich", "Bayer Leverkusen", "Inter", "Juventus", "Milan",
    "PSG", "Benfica", "Porto", "Sporting", "Al Hilal", "Al Nassr"
]

# =============================================================================
# CONFIG & API CLIENT (Optimized)
# =============================================================================

class Config:
    def __init__(self):
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY')
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.facebook_page_access_token = os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN')
        self.facebook_page_id = os.environ.get('FACEBOOK_PAGE_ID')

    def validate(self) -> bool:
        required = [
            ('RAPIDAPI_KEY', self.rapidapi_key),
            ('TELEGRAM_BOT_TOKEN', self.telegram_bot_token),
            ('TELEGRAM_CHAT_ID', self.telegram_chat_id),
            ('FACEBOOK_PAGE_ACCESS_TOKEN', self.facebook_page_access_token),
            ('FACEBOOK_PAGE_ID', self.facebook_page_id)
        ]
        missing = [name for name, value in required if not value]
        if missing:
            logger.error(f"Missing environment variables: {', '.join(missing)}")
            return False
        return True

config = Config()

class FootballAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.request_count = 0

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        global API_REQUESTS_THIS_RUN
        if self.request_count >= MAX_API_CALLS_PER_RUN:
            return None
        
        url = f"{RAPIDAPI_BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            self.request_count += 1
            API_REQUESTS_THIS_RUN += 1
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API Error: {e}")
            return None

    def get_matches_by_date(self, date: str) -> Optional[List[Dict]]:
        endpoint = "/matches/v2/list-by-date"
        params = {"Category": "soccer", "Date": date, "Timezone": "0"}
        data = self._make_request(endpoint, params)
        if data and 'Stages' in data:
            return self._parse_matches(data['Stages'])
        return None

    def _parse_matches(self, stages: List[Dict]) -> List[Dict]:
        matches = []
        for stage in stages:
            competition = stage.get('Snm', stage.get('Cnm', 'Unknown'))
            for event in stage.get('Events', []):
                # Extract Team Info
                t1 = event.get('T1', [{}])[0]
                t2 = event.get('T2', [{}])[0]
                
                home_team = t1.get('Nm', 'Unknown')
                away_team = t2.get('Nm', 'Unknown')
                
                # Get Ranks (Important for predictions)
                try:
                    home_rank = int(t1.get('Rnk', 99))
                except (ValueError, TypeError):
                    home_rank = 99
                    
                try:
                    away_rank = int(t2.get('Rnk', 99))
                except (ValueError, TypeError):
                    away_rank = 99

                eps = event.get('Eps', '')
                is_live = eps in ['HT', '1H', '2H', 'LIVE', 'ET', 'BT', 'PT']
                is_finished = eps in ['FT', 'AET', 'PEN', 'AP']
                
                match = {
                    'id': event.get('Eid', ''),
                    'competition': competition,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': event.get('Tr1', '-'),
                    'away_score': event.get('Tr2', '-'),
                    'status': eps if eps else 'Upcoming',
                    'start_time': self._parse_time(event.get('Esd', '')),
                    'is_live': is_live,
                    'is_finished': is_finished,
                    'is_major': any(m.lower() in competition.lower() for m in MAJOR_COMPETITIONS),
                    'home_rank': home_rank,
                    'away_rank': away_rank,
                }
                matches.append(match)
        return matches

    def _parse_time(self, time_str: str) -> str:
        try:
            dt = datetime.strptime(str(time_str)[:14], "%Y%m%d%H%M%S")
            return GMT.localize(dt).strftime("%H:%M GMT")
        except:
            return "TBD"

# =============================================================================
# SMART PREDICTION ENGINE (NEW!)
# =============================================================================

class ContentGenerator:
    
    @staticmethod
    def get_smart_prediction(match: Dict) -> Dict[str, str]:
        """
        Generates a prediction based on Rank, Powerhouse status, and Home Advantage.
        Returns a dict with 'tip', 'market', and 'emoji'.
        """
        home = match['home_team']
        away = match['away_team']
        h_rank = match['home_rank']
        a_rank = match['away_rank']
        
        home_is_power = any(p in home for p in POWERHOUSE_TEAMS)
        away_is_power = any(p in away for p in POWERHOUSE_TEAMS)
        
        # Logic 1: Powerhouse Mismatch
        if home_is_power and not away_is_power:
            return {"tip": f"{home} to Win", "market": "1X2", "emoji": "🟢"}
        if away_is_power and not home_is_power:
            return {"tip": f"{away} to Win", "market": "1X2", "emoji": "🟣"}
            
        # Logic 2: Table Ranking (Difference of 5+ positions)
        if h_rank != 99 and a_rank != 99:
            diff = a_rank - h_rank # Positive means Home is higher ranked (lower number)
            
            if diff > 5:
                return {"tip": f"{home} Win or Draw", "market": "Double Chance", "emoji": "🛡️"}
            elif diff < -5:
                return {"tip": f"{away} Win or Draw", "market": "Double Chance", "emoji": "🛡️"}
            elif abs(diff) <= 3:
                # Close ranks implies tight game or goals
                return {"tip": "Both Teams to Score", "market": "BTTS", "emoji": "🔥"}

        # Logic 3: Default Home Advantage / High Scoring for Major Leagues
        if match.get('is_major'):
            return {"tip": "Over 1.5 Goals", "market": "Goals", "emoji": "⚽"}
            
        return {"tip": "Home to Win or Draw", "market": "Double Chance", "emoji": "🎲"}

    @staticmethod
    def generate_telegram_daily_summary(matches: List[Dict], live_matches: List[Dict] = None) -> str:
        """Generates summary where EVERY match line has a prediction"""
        
        now_gmt = datetime.now(GMT)
        today_str = now_gmt.strftime("%A, %d %B")
        
        message = f"📅 *VIP PREDICTIONS FOR TODAY* 📅\n📆 {today_str}\n\n"
        
        # 1. LIVE SECTION
        if live_matches:
            message += "🔴 *LIVE NOW*\n"
            for m in live_matches[:3]:
                score = f"{m['home_score']}-{m['away_score']}"
                message += f"⚽ {m['home_team']} {score} {m['away_team']}\n"
            message += "\n"

        # 2. UPCOMING WITH PREDICTIONS
        upcoming = [m for m in matches if m['status'] == 'Upcoming' and m.get('is_major')]
        
        if upcoming:
            # Group by league
            by_comp = {}
            for m in upcoming:
                comp = m['competition']
                if comp not in by_comp: by_comp[comp] = []
                by_comp[comp].append(m)
            
            # Limit to top 5 leagues to fit text limits
            for comp, comp_matches in list(by_comp.items())[:6]:
                message += f"🏆 *{comp}*\n"
                for m in comp_matches[:4]: # Max 4 per league
                    pred = ContentGenerator.get_smart_prediction(m)
                    time = m['start_time'].split(' ')[0]
                    # Format: 14:00 | Man City vs Luton 👉 Home Win
                    message += f"⏰ {time} | {m['home_team']} 🆚 {m['away_team']}\n"
                    message += f"   💡 *Tip:* {pred['emoji']} {pred['tip']}\n"
                message += "\n"
        else:
            message += "⚠️ No major matches scheduled for today.\n\n"

        # 3. CALL TO ACTION
        message += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "💰 *BET HERE & GET A BONUS:* 💰\n\n"
        for name, link in AFFILIATE_LINKS.items():
            message += f"👉 {name}: {link}\n"
            
        message += "\n#Football #Predictions #BettingTips"
        return message.strip()

    @staticmethod
    def generate_telegram_match_post(match: Dict) -> str:
        """Detailed single match post with analysis"""
        pred = ContentGenerator.get_smart_prediction(match)
        
        message = f"""
⚽ *PREMIUM MATCH PREDICTION* ⚽

🏆 *{match['competition']}*
⏰ {match['start_time']}

🔵 *{match['home_team']}*
         🆚
🔴 *{match['away_team']}*

━━━━━━━━━━━━━━━━━━━━━
🧠 *AI PREDICTION:*
👀 Market: {pred['market']}
💎 *Pick: {pred['tip']}* {pred['emoji']}
━━━━━━━━━━━━━━━━━━━━━

💰 *BET NOW - BEST ODDS:*

"""
        for name, link in AFFILIATE_LINKS.items():
            message += f"👉 {name}: {link}\n"
            
        return message.strip()

    @staticmethod
    def generate_facebook_teaser(matches: List[Dict]) -> str:
        """Facebook Teaser - Drives traffic to Telegram for the predictions"""
        upcoming = [m for m in matches if m['status'] == 'Upcoming' and m.get('is_major')][:3]
        
        txt = "🔥 TODAY'S EXPERT PREDICTIONS 🔥\n\n"
        for m in upcoming:
            txt += f"⚽ {m['home_team']} 🆚 {m['away_team']}\n"
            
        txt += "\nWe have posted WINNING tips for these matches! 💎\n\n"
        txt += "👇 GET THE PREDICTIONS HERE FREE 👇\n"
        txt += f"📲 {TELEGRAM_CHANNEL_LINK}\n"
        txt += f"📲 {TELEGRAM_CHANNEL_LINK}\n\n"
        txt += "#Football #Predictions #Betting"
        return txt

# =============================================================================
# SOCIAL CLIENTS
# =============================================================================

class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str):
        self.url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id
    
    def send(self, text: str):
        try:
            requests.post(self.url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}, timeout=10)
            logger.info("✅ Telegram Sent")
        except Exception as e:
            logger.error(f"Telegram Fail: {e}")

class FacebookClient:
    def __init__(self, page_id: str, token: str):
        self.url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
        self.token = token
    
    def post(self, text: str):
        try:
            requests.post(self.url, data={"message": text, "access_token": self.token}, timeout=10)
            logger.info("✅ Facebook Sent")
        except Exception as e:
            logger.error(f"Facebook Fail: {e}")

# =============================================================================
# MAIN LOGIC
# =============================================================================

def main():
    logger.info("🚀 Starting Football Bot with Predictions...")
    
    if not config.validate(): return

    bot_api = FootballAPI(config.rapidapi_key)
    tg = TelegramClient(config.telegram_bot_token, config.telegram_chat_id)
    fb = FacebookClient(config.facebook_page_id, config.facebook_page_access_token)
    
    # 1. API Call
    now = datetime.now(GMT)
    today = now.strftime("%Y%m%d")
    matches = bot_api.get_matches_by_date(today)
    
    if not matches:
        logger.warning("No matches today")
        return

    # 2. Daily Summary Post (With Predictions for ALL matches listed)
    # We execute this every time the bot runs (every 3 hours) to keep feed fresh
    summary_text = ContentGenerator.generate_telegram_daily_summary(matches)
    tg.send(summary_text)
    
    # 3. Facebook Teaser
    fb_text = ContentGenerator.generate_facebook_teaser(matches)
    fb.post(fb_text)
    
    # 4. Highlight specific upcoming Major Match (Single detailed post)
    upcoming_majors = [m for m in matches if m['status'] == 'Upcoming' and m.get('is_major')]
    
    # Check if there is a match starting in the next 3 hours
    for match in upcoming_majors:
        try:
            start = datetime.strptime(match['start_time'], "%H:%M GMT").replace(year=now.year, month=now.month, day=now.day)
            start = GMT.localize(start)
            # If match starts within 2 hours
            diff = (start - now).total_seconds() / 3600
            if 0 < diff <= 3:
                detailed_msg = ContentGenerator.generate_telegram_match_post(match)
                tg.send(detailed_msg)
                break # Only one detailed highlight per run
        except:
            continue

    logger.info("✅ Done")

if __name__ == "__main__":
    main()
