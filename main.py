#!/usr/bin/env python3
"""
Football Data Automation Bot - FIXED CONTENT GENERATION
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

# =============================================================================
# CONFIGURATION
# =============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

GMT = pytz.timezone('GMT')
API_REQUESTS_THIS_RUN = 0
MAX_API_CALLS_PER_RUN = 1

# AFFILIATE LINKS
AFFILIATE_LINKS = {
    "🎰 Stake": "https://stake.com/?c=GlobalScoreUpdates",
    "📊 Linebet": "https://linebet.com?bf=695d695c66d7a_13053616523",
    "🏆 1xBet": "https://ma-1xbet.com?bf=695d66e22c1b5_7531017325"
}

TELEGRAM_CHANNEL_LINK = "https://t.me/+xAQ3DCVJa8A2ZmY8"

RAPIDAPI_HOST = "livescore6.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"

# EXPANDED list to catch more matches
MAJOR_COMPETITIONS = [
    "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
    "Champions League", "Europa", "Conference", "World Cup", "Euro",
    "FA Cup", "Copa", "Eredivisie", "Primeira", "Saudi", "MLS", 
    "Championship", "League One", "Super Lig", "Super League"
]

POWERHOUSE_TEAMS = [
    "Man City", "Liverpool", "Arsenal", "Real Madrid", "Barcelona",
    "Bayern", "Leverkusen", "Inter", "Juve", "Milan", "PSG", 
    "Benfica", "Porto", "Sporting", "Al Hilal", "Al Nassr", "Chelsea", "Man Utd"
]

# =============================================================================
# SETUP
# =============================================================================

class Config:
    def __init__(self):
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY')
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.facebook_page_access_token = os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN')
        self.facebook_page_id = os.environ.get('FACEBOOK_PAGE_ID')

    def validate(self):
        return all([self.rapidapi_key, self.telegram_bot_token, self.telegram_chat_id, 
                   self.facebook_page_access_token, self.facebook_page_id])

config = Config()

# =============================================================================
# API
# =============================================================================

class FootballAPI:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": RAPIDAPI_HOST})
        self.request_count = 0

    def get_matches(self):
        global API_REQUESTS_THIS_RUN
        if self.request_count >= MAX_API_CALLS_PER_RUN: return []
        
        # Get TODAY'S date in YYYYMMDD
        date_str = datetime.now(GMT).strftime("%Y%m%d")
        
        try:
            url = f"{RAPIDAPI_BASE_URL}/matches/v2/list-by-date"
            resp = self.session.get(url, params={"Category": "soccer", "Date": date_str, "Timezone": "0"}, timeout=30)
            self.request_count += 1
            API_REQUESTS_THIS_RUN += 1
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data.get('Stages', []))
        except Exception as e:
            logger.error(f"API Error: {e}")
            return []

    def _parse(self, stages):
        matches = []
        for stage in stages:
            comp = stage.get('Snm', stage.get('Cnm', 'Unknown'))
            # Check if this is a "Major" league, but we will store ALL matches
            is_major = any(m.lower() in comp.lower() for m in MAJOR_COMPETITIONS)
            
            for evt in stage.get('Events', []):
                t1 = evt.get('T1', [{}])[0]
                t2 = evt.get('T2', [{}])[0]
                
                match = {
                    'competition': comp,
                    'home': t1.get('Nm', 'Unknown'),
                    'away': t2.get('Nm', 'Unknown'),
                    'home_score': evt.get('Tr1', '-'),
                    'away_score': evt.get('Tr2', '-'),
                    'status': evt.get('Eps', 'NS'),
                    'start_time': self._fmt_time(evt.get('Esd', '')),
                    'is_live': evt.get('Eps') in ['1H','2H','HT','LIVE','ET'],
                    'is_major': is_major,
                    # Fallback logic: If league is major, rank is 1. If not, rank is 2.
                    'priority': 1 if is_major else 2
                }
                matches.append(match)
        
        # Sort matches: Live first, then Major, then others
        matches.sort(key=lambda x: (0 if x['is_live'] else 1, x['priority']))
        return matches

    def _fmt_time(self, t):
        try:
            return GMT.localize(datetime.strptime(str(t)[:14], "%Y%m%d%H%M%S")).strftime("%H:%M GMT")
        except: return "TBD"

# =============================================================================
# CONTENT GENERATOR (FIXED)
# =============================================================================

class ContentGenerator:
    
    @staticmethod
    def get_prediction(match):
        """Simple logic to ensure EVERY match has a prediction"""
        h, a = match['home'], match['away']
        
        # Powerhouse Logic
        h_pow = any(p in h for p in POWERHOUSE_TEAMS)
        a_pow = any(p in a for p in POWERHOUSE_TEAMS)
        
        if h_pow and not a_pow: return f"🟢 {h} to Win"
        if a_pow and not h_pow: return f"🟣 {a} to Win"
        
        # Random but realistic variations for non-powerhouse games
        # (Since we don't have odds/stats to save API calls)
        seed = len(h) + len(a) # Deterministic "random" based on name length
        if seed % 3 == 0: return "🛡️ Double Chance: 1X"
        if seed % 3 == 1: return "🔥 Both Teams to Score"
        return "⚽ Over 1.5 Goals"

    @staticmethod
    def telegram_post(matches):
        now_str = datetime.now(GMT).strftime("%A, %d %B")
        
        # Filter: Get all upcoming matches
        upcoming = [m for m in matches if m['status'] in ['NS', 'Upcoming', '']]
        
        # If no Upcoming, check for Live
        if not upcoming:
            upcoming = [m for m in matches if m['is_live']]

        # Select top matches (Major first, then others). Limit to 12 max to avoid text limit.
        selected_matches = upcoming[:12]

        msg = f"📅 *VIP PREDICTIONS FOR TODAY* 📅\n📆 {now_str}\n\n"

        if not selected_matches:
            msg += "⚠️ No matches found right now. Check back later!\n\n"
        else:
            # Group by League
            by_league = {}
            for m in selected_matches:
                if m['competition'] not in by_league: by_league[m['competition']] = []
                by_league[m['competition']].append(m)

            for comp, games in by_league.items():
                msg += f"🏆 *{comp}*\n"
                for g in games:
                    pred = ContentGenerator.get_prediction(g)
                    time = g['start_time'].split(' ')[0]
                    msg += f"⏰ {time} | {g['home']} 🆚 {g['away']}\n"
                    msg += f"   💡 *Tip:* {pred}\n"
                msg += "\n"

        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💰 *BET HERE & GET A BONUS:* 💰\n\n"
        for n, l in AFFILIATE_LINKS.items():
            msg += f"👉 {n}: {l}\n"
        
        msg += "\n#Football #Predictions #BettingTips"
        return msg

    @staticmethod
    def facebook_teaser(matches):
        # Get upcoming matches (Major first, then any)
        upcoming = [m for m in matches if m['status'] in ['NS', 'Upcoming', '']]
        selected = upcoming[:4] # Take top 4 matches
        
        if not selected:
            # Fallback text if truly no matches
            return f"""🔥 FOOTBALL BETTING TIPS 🔥
            
We have analyzed the markets! 💎

👇 GET THE PREDICTIONS HERE FREE 👇
📲 {TELEGRAM_CHANNEL_LINK}

#Football #Predictions"""

        # Build list of matches
        match_txt = ""
        for m in selected:
            match_txt += f"⚽ {m['home']} 🆚 {m['away']}\n"

        return f"""🔥 TODAY'S EXPERT PREDICTIONS 🔥

{match_txt}
We have posted WINNING tips for these matches! 💎

👇 GET THE PREDICTIONS HERE FREE 👇
📲 {TELEGRAM_CHANNEL_LINK}

#Football #Predictions #Betting"""

# =============================================================================
# MAIN
# =============================================================================

def main():
    if not config.validate(): return
    
    bot = FootballAPI(config.rapidapi_key)
    tg_url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    fb_url = f"https://graph.facebook.com/v18.0/{config.facebook_page_id}/feed"

    logger.info("🚀 Fetching matches...")
    matches = bot.get_matches()
    
    if not matches:
        logger.warning("❌ No data received from API")
        return

    logger.info(f"✅ Found {len(matches)} matches")

    # 1. Telegram Post
    tg_text = ContentGenerator.telegram_post(matches)
    try:
        requests.post(tg_url, json={"chat_id": config.telegram_chat_id, "text": tg_text, "parse_mode": "Markdown", "disable_web_page_preview": True})
        logger.info("✅ Telegram Sent")
    except Exception as e: logger.error(f"TG Error: {e}")

    # 2. Facebook Post
    fb_text = ContentGenerator.facebook_teaser(matches)
    try:
        requests.post(fb_url, data={"message": fb_text, "access_token": config.facebook_page_access_token})
        logger.info("✅ Facebook Sent")
    except Exception as e: logger.error(f"FB Error: {e}")

if __name__ == "__main__":
    main()
