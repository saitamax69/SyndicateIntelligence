#!/usr/bin/env python3
"""
Football Data Automation Bot - SYNDICATE EDITION
Premium Typography & "Smart Money" Styling
Optimized for 500 Requests/Month
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List
import pytz
import logging
import random

# =============================================================================
# CONFIGURATION
# =============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

GMT = pytz.timezone('GMT')
API_REQUESTS_THIS_RUN = 0
MAX_API_CALLS_PER_RUN = 1

# AFFILIATE LINKS (The Revenue Engine)
AFFILIATE_LINKS = {
    "🎰 Stake": "https://stake.com/?c=GlobalScoreUpdates",
    "📊 Linebet": "https://linebet.com?bf=695d695c66d7a_13053616523",
    "🏆 1xBet": "https://ma-1xbet.com?bf=695d66e22c1b5_7531017325"
}

TELEGRAM_CHANNEL_LINK = "https://t.me/+xAQ3DCVJa8A2ZmY8"

RAPIDAPI_HOST = "livescore6.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"

MAJOR_COMPETITIONS = [
    "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
    "Champions League", "Europa", "Conference", "World Cup", "Euro",
    "FA Cup", "Copa", "Eredivisie", "Primeira", "Saudi", "MLS", 
    "Championship", "League One", "Super Lig", "Super League"
]

POWERHOUSE_TEAMS = [
    "Man City", "Liverpool", "Arsenal", "Real Madrid", "Barcelona",
    "Bayern", "Leverkusen", "Inter", "Juve", "Milan", "PSG",
    "Benfica", "Porto", "Al Hilal", "Al Nassr", "Chelsea", "Man Utd"
]

# =============================================================================
# 🎨 PREMIUM TYPOGRAPHY ENGINE
# =============================================================================

class TextStyler:
    """Converts standard text to Premium Unicode Styles"""
    
    @staticmethod
    def to_bold_sans(text):
        """Converts text to 𝗕𝗢𝗟𝗗 𝗦𝗔𝗡𝗦 (Mathematical Sans-Serif Bold)"""
        # Mapping for A-Z, a-z, 0-9
        normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        # Unicode ranges for Math Sans Bold
        mapped = "".join([chr(0x1D5D4 + i) for i in range(26)]) + \
                 "".join([chr(0x1D5EE + i) for i in range(26)]) + \
                 "".join([chr(0x1D7EC + i) for i in range(10)])
        
        table = str.maketrans(normal, mapped)
        return text.translate(table)

    @staticmethod
    def to_mono(text):
        """Converts text to 𝙼𝚘𝚗𝚘𝚜𝚙𝚊𝚌𝚎 (Mathematical Monospace)"""
        normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        mapped = "".join([chr(0x1D670 + i) for i in range(26)]) + \
                 "".join([chr(0x1D68A + i) for i in range(26)]) + \
                 "".join([chr(0x1D7F6 + i) for i in range(10)])
        table = str.maketrans(normal, mapped)
        return text.translate(table)

# =============================================================================
# API CLIENT
# =============================================================================

class FootballAPI:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": RAPIDAPI_HOST})
        self.request_count = 0

    def get_matches(self):
        global API_REQUESTS_THIS_RUN
        if self.request_count >= MAX_API_CALLS_PER_RUN: return []
        
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
            is_major = any(m.lower() in comp.lower() for m in MAJOR_COMPETITIONS)
            
            for evt in stage.get('Events', []):
                t1 = evt.get('T1', [{}])[0]
                t2 = evt.get('T2', [{}])[0]
                
                # Rank Logic (Default to 50 if unknown for logic purposes)
                r1 = int(t1.get('Rnk', 50)) if str(t1.get('Rnk', '')).isdigit() else 50
                r2 = int(t2.get('Rnk', 50)) if str(t2.get('Rnk', '')).isdigit() else 50
                
                match = {
                    'competition': comp,
                    'home': t1.get('Nm', 'Unknown'),
                    'away': t2.get('Nm', 'Unknown'),
                    'home_rank': r1,
                    'away_rank': r2,
                    'home_score': evt.get('Tr1', '-'),
                    'away_score': evt.get('Tr2', '-'),
                    'status': evt.get('Eps', 'NS'),
                    'start_time': self._fmt_time(evt.get('Esd', '')),
                    'is_live': evt.get('Eps') in ['1H','2H','HT','LIVE','ET'],
                    'is_major': is_major,
                    # Priority for sorting: Live > Major > Others
                    'priority': 1 if is_major else 2
                }
                matches.append(match)
        
        # Sort matches
        matches.sort(key=lambda x: (0 if x['is_live'] else 1, x['priority']))
        return matches

    def _fmt_time(self, t):
        try:
            return GMT.localize(datetime.strptime(str(t)[:14], "%Y%m%d%H%M%S")).strftime("%H:%M")
        except: return "--:--"

# =============================================================================
# CONTENT GENERATOR (SYNDICATE STYLE)
# =============================================================================

class ContentGenerator:
    
    @staticmethod
    def get_analysis(match):
        """Generates the 'Edge' and the 'Pick' based on data to sound like a Pro"""
        h, a = match['home'], match['away']
        r1, r2 = match['home_rank'], match['away_rank']
        
        h_pow = any(p in h for p in POWERHOUSE_TEAMS)
        a_pow = any(p in a for p in POWERHOUSE_TEAMS)
        
        # Scenario 1: Mismatch (Powerhouse vs Weak)
        if h_pow and not a_pow:
            return {
                "edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Heavy sharp action on Home.",
                "reason": f"Class disparity evident. {h} is a fortress.",
                "pick": f"{h} -0.75 AH"
            }
        if a_pow and not h_pow:
            return {
                "edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Away side underpriced.",
                "reason": f"{a} form metrics superior to host.",
                "pick": f"{a} to Win"
            }
        
        # Scenario 2: Close Ranks (Tight Game)
        if abs(r1 - r2) < 4:
            return {
                "edge": "⚖️ 𝚃𝚊𝚌𝚝𝚒𝚌𝚊𝚕 𝚂𝚝𝚊𝚗𝚍𝚘𝚏𝚏",
                "reason": "Both defensive units trending well.",
                "pick": "Under 3.5 Goals / Draw"
            }
            
        # Scenario 3: Default High Scoring for Leagues
        return {
            "edge": "🔥 𝙵𝚘𝚛𝚖 𝚂𝚙𝚒𝚔𝚎",
            "reason": "Offensive output trending up for both.",
            "pick": "Over 1.5 Goals"
        }

    @staticmethod
    def telegram_feed(matches):
        """Generates the 'Syndicate' looking post"""
        now_str = datetime.now(GMT).strftime("%d %b")
        
        # Header
        title = TextStyler.to_bold_sans("SYNDICATE INTELLIGENCE")
        subtitle = TextStyler.to_mono(f"Daily Briefing | {now_str}")
        
        msg = f"💎 {title}\n{subtitle}\n\n"
        
        # Filter Logic: Upcoming first, then Live
        upcoming = [m for m in matches if m['status'] in ['NS', 'Upcoming', '']]
        if not upcoming:
            upcoming = [m for m in matches if m['is_live']]
            
        # If still empty (extremely rare)
        if not upcoming:
            return f"💎 {title}\n\nNo market opportunities detected right now.\nSystem standby."

        # Process Top 5 Matches (Mix of Major + others if needed)
        selected = upcoming[:5]
        
        for m in selected:
            data = ContentGenerator.get_analysis(m)
            comp = TextStyler.to_bold_sans(m['competition'].upper())
            teams = f"{m['home']} vs {m['away']}"
            time = m['start_time']
            
            # Box Drawing Construction - Syndicate Style
            msg += f"┌── {comp} ──────────\n"
            msg += f"│ ⚔️ {teams}\n"
            msg += f"│ ⏰ {time} GMT\n"
            msg += f"│\n"
            msg += f"│ {data['edge']}\n"
            msg += f"│ └─ {data['reason']}\n"
            msg += f"│\n"
            msg += f"└─ 🎯 𝗧𝗛𝗘 𝗣𝗜𝗖𝗞: {TextStyler.to_bold_sans(data['pick'])}\n\n"

        # Footer / Affiliate Section
        msg += "────── 🔒 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗔𝗖𝗖𝗘𝗦𝗦 ──────\n"
        msg += "Maximize your edge with our partners:\n\n"
        
        for name, link in AFFILIATE_LINKS.items():
            msg += f"👉 {TextStyler.to_bold_sans(name)}: {link}\n"
            
        return msg

    @staticmethod
    def facebook_teaser(matches):
        """Click-baity but professional teaser"""
        if not matches: return "Market Analysis pending..."
        
        # Try to find a Major match, otherwise take the first available
        major = next((m for m in matches if m['is_major']), None)
        top_match = major if major else matches[0]
        
        h, a = top_match['home'], top_match['away']
        
        header = TextStyler.to_bold_sans("SMART MONEY MOVE")
        teams = TextStyler.to_bold_sans(f"{h} vs {a}")
        
        return f"""💎 {header}
        
We have detected a significant liquidity spike in today's fixture:

⚽ {teams}

📉 𝗠𝗮𝗿𝗸𝗲𝘁 𝗔𝗻𝗮𝗹𝘆𝘀𝗶𝘀:
The sharps are moving heavily on one side. The public is on the other. 

Don't be on the wrong side of the variance.

👇 𝗦𝗘𝗘 𝗧𝗛𝗘 𝗢𝗙𝗙𝗜𝗖𝗜𝗔𝗟 𝗣𝗜𝗖𝗞 𝗛𝗘𝗥𝗘:
📲 {TELEGRAM_CHANNEL_LINK}

#Syndicate #ValueBet #SmartMoney #FootballTips"""

# =============================================================================
# MAIN
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

def main():
    config = Config()
    if not config.validate(): return
    
    bot = FootballAPI(config.rapidapi_key)
    
    logger.info("🚀 Fetching market data...")
    matches = bot.get_matches()
    
    if not matches:
        logger.warning("No matches found.")
        return

    logger.info(f"✅ Analyzed {len(matches)} matches")

    # Generate Content
    tg_content = ContentGenerator.telegram_feed(matches)
    fb_content = ContentGenerator.facebook_teaser(matches)
    
    # Send Telegram
    try:
        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        # Note: HTML parse mode is not used here because we rely on Unicode characters for bolding
        requests.post(url, json={
            "chat_id": config.telegram_chat_id, 
            "text": tg_content, 
            "parse_mode": "", # Empty parse mode as we use raw Unicode
            "disable_web_page_preview": True
        })
        logger.info("✅ Syndicate Intelligence Sent to Telegram")
    except Exception as e: logger.error(f"Telegram Error: {e}")

    # Send Facebook
    try:
        url = f"https://graph.facebook.com/v18.0/{config.facebook_page_id}/feed"
        requests.post(url, data={"message": fb_content, "access_token": config.facebook_page_access_token})
        logger.info("✅ Smart Money Move Sent to Facebook")
    except Exception as e: logger.error(f"Facebook Error: {e}")

if __name__ == "__main__":
    main()
