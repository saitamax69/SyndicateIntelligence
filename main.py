#!/usr/bin/env python3
"""
Football Data Automation Bot - SYNDICATE EDITION V6 (AI POWERED)
Features:
1. Groq AI for unique, viral Facebook posts.
2. Simulated Fair Odds Calculation.
3. Syndicate Styling for Telegram (unchanged).
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
import pytz
import logging
import hashlib
import random
from groq import Groq  # IMPORT GROQ

# =============================================================================
# CONFIGURATION
# =============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

GMT = pytz.timezone('GMT')
API_REQUESTS_THIS_RUN = 0
MAX_API_CALLS_PER_RUN = 1

# AFFILIATE CONFIG WITH HOOKS
AFFILIATE_CONFIG = [
    {"name": "🎰 Stake", "link": "https://stake.com/?c=GlobalScoreUpdates", "offer": "200% Deposit Bonus | Instant Cashout ⚡"},
    {"name": "📊 Linebet", "link": "https://linebet.com?bf=695d695c66d7a_13053616523", "offer": "High Odds | Fast Payouts 💸"},
    {"name": "🏆 1xBet", "link": "https://ma-1xbet.com?bf=695d66e22c1b5_7531017325", "offer": "300% First Deposit Bonus 💰"}
]

TELEGRAM_CHANNEL_LINK = "https://t.me/+xAQ3DCVJa8A2ZmY8"
RAPIDAPI_HOST = "livescore6.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"

LEAGUE_PROFILES = {
    "HIGH_SCORING": ["Bundesliga", "Eredivisie", "MLS", "Saudi", "Jupiler", "Allsvenskan"],
    "DEFENSIVE": ["Serie A", "Ligue 1", "Segunda", "Brasileiro", "Argentina"],
    "BALANCED": ["Premier League", "La Liga", "Championship", "Champions League", "Europa"]
}

MAJOR_COMPETITIONS = [
    "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
    "Champions League", "Europa", "Conference", "World Cup", "Euro",
    "FA Cup", "Copa", "Eredivisie", "Primeira", "Saudi", "MLS", 
    "Championship", "League One", "Super Lig"
]

POWERHOUSE_TEAMS = [
    "Man City", "Liverpool", "Arsenal", "Real Madrid", "Barcelona",
    "Bayern", "Leverkusen", "Inter", "Juve", "Milan", "PSG",
    "Benfica", "Porto", "Al Hilal", "Al Nassr", "Chelsea"
]

# =============================================================================
# ODDS ENGINE (Simulate Realistic Odds)
# =============================================================================

class OddsEngine:
    @staticmethod
    def calculate_fair_odds(match):
        """Calculates realistic odds based on rankings"""
        r1, r2 = match['home_rank'], match['away_rank']
        h_pow = any(p in match['home'] for p in POWERHOUSE_TEAMS)
        a_pow = any(p in match['away'] for p in POWERHOUSE_TEAMS)
        
        # Base odds
        h_odd = 2.40
        a_odd = 2.90
        d_odd = 3.20

        # Adjust for Powerhouse
        if h_pow: h_odd = 1.35; a_odd = 7.50; d_odd = 4.50
        elif a_pow: a_odd = 1.45; h_odd = 6.00; d_odd = 4.20
        
        # Adjust for Rank Diff (if not powerhouse)
        elif abs(r1 - r2) > 8:
            if r1 < r2: h_odd = 1.75; a_odd = 4.20  # Home stronger
            else: a_odd = 2.10; h_odd = 3.40  # Away stronger
        
        # Add random fluctuation to look real
        h_odd = round(h_odd + random.uniform(-0.05, 0.05), 2)
        a_odd = round(a_odd + random.uniform(-0.05, 0.05), 2)
        
        return h_odd, d_odd, a_odd

# =============================================================================
# TYPOGRAPHY & INSIGHTS (For Telegram)
# =============================================================================

class TextStyler:
    @staticmethod
    def to_bold_sans(text):
        normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        mapped = "".join([chr(0x1D5D4 + i) for i in range(26)]) + \
                 "".join([chr(0x1D5EE + i) for i in range(26)]) + \
                 "".join([chr(0x1D7EC + i) for i in range(10)])
        return text.translate(str.maketrans(normal, mapped))

    @staticmethod
    def to_mono(text):
        normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        mapped = "".join([chr(0x1D670 + i) for i in range(26)]) + \
                 "".join([chr(0x1D68A + i) for i in range(26)]) + \
                 "".join([chr(0x1D7F6 + i) for i in range(10)])
        return text.translate(str.maketrans(normal, mapped))

class Insights:
    DOMINANT_HOME = ["Home side xG metrics trending 20% above league avg.", "Visitors struggle against high-press systems.", "Host defense conceded zero open-play goals recently."]
    GOALS_EXPECTED = ["Both sides ranking top 5 for shots created.", "Defensive injury crisis creating value.", "H2H indicates an open game."]
    TIGHT_MATCH = ["Midfield congestion expected to limit chances.", "Both managers prioritize structure.", "Late season pressure suggests caution."]
    UNDERDOG_VALUE = ["Market overreacting to brand name.", "Visitors have best counter-attacking stats.", "Home side resting key players."]

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
            return self._parse(resp.json().get('Stages', []))
        except Exception as e:
            logger.error(f"API Error: {e}")
            return []

    def _parse(self, stages):
        matches = []
        now = datetime.now(GMT)
        
        for stage in stages:
            comp = stage.get('Snm', stage.get('Cnm', 'Unknown'))
            is_major = any(m.lower() in comp.lower() for m in MAJOR_COMPETITIONS)
            
            for evt in stage.get('Events', []):
                start_str = str(evt.get('Esd', ''))
                try:
                    if len(start_str) >= 12:
                        match_dt = GMT.localize(datetime.strptime(start_str[:14], "%Y%m%d%H%M%S"))
                        if match_dt <= now: continue # Future only
                        
                        t1 = evt.get('T1', [{}])[0]
                        t2 = evt.get('T2', [{}])[0]
                        
                        match = {
                            'competition': comp,
                            'home': t1.get('Nm', 'Unknown'),
                            'away': t2.get('Nm', 'Unknown'),
                            'home_rank': int(t1.get('Rnk', 50)) if str(t1.get('Rnk', '')).isdigit() else 50,
                            'away_rank': int(t2.get('Rnk', 50)) if str(t2.get('Rnk', '')).isdigit() else 50,
                            'start_time': match_dt.strftime("%H:%M"),
                            'is_major': is_major,
                            'priority': 1 if is_major else 2
                        }
                        
                        # Add calculated odds
                        h_odd, d_odd, a_odd = OddsEngine.calculate_fair_odds(match)
                        match['odds'] = {'1': h_odd, 'X': d_odd, '2': a_odd}
                        
                        matches.append(match)
                except: continue

        matches.sort(key=lambda x: (x['priority'], x['start_time']))
        return matches

# =============================================================================
# LOGIC & AI ENGINE
# =============================================================================

class LogicEngine:
    @staticmethod
    def analyze_telegram(match):
        """Standard deterministic logic for Telegram"""
        h, a = match['home'], match['away']
        comp = match['competition']
        
        style = "BALANCED"
        for k, v in LEAGUE_PROFILES.items():
            if any(l in comp for l in v): style = k; break
        
        h_pow = any(p in h for p in POWERHOUSE_TEAMS)
        a_pow = any(p in a for p in POWERHOUSE_TEAMS)
        match_hash = int(hashlib.md5(f"{h}{a}".encode()).hexdigest(), 16)

        if h_pow and not a_pow:
            insight = Insights.DOMINANT_HOME[match_hash % len(Insights.DOMINANT_HOME)]
            return {"edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Sharp Action Home", "insight": insight, "main": f"{h} -1.0 AH", "alt": f"{h} to Win & Over 1.5"}
        if a_pow and not h_pow:
            insight = Insights.UNDERDOG_VALUE[match_hash % len(Insights.UNDERDOG_VALUE)]
            return {"edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Visitors undervalued", "insight": "Class disparity favors the visitors.", "main": f"{a} to Win", "alt": "Over 1.5 Goals"}
        if style == "HIGH_SCORING":
            insight = Insights.GOALS_EXPECTED[match_hash % len(Insights.GOALS_EXPECTED)]
            return {"edge": "🔥 𝚅𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢 𝙰𝚕𝚎𝚛𝚝", "insight": insight, "main": "Over 2.5 Goals", "alt": "Both Teams to Score"}
        
        # Default Balanced
        seed = len(h) + len(a)
        if seed % 3 == 0: return {"edge": "📈 𝙵𝚘𝚛𝚖 𝙼𝚘𝚖𝚎𝚗𝚝𝚞𝚖", "insight": "Both teams scoring consistently.", "main": "Both Teams to Score", "alt": "Over 2.5 Goals"}
        return {"edge": "🛡️ 𝚂𝚊𝚏𝚎𝚝𝚢 𝙵𝚒𝚛𝚜𝚝", "insight": "Home advantage is key.", "main": f"{h} Win or Draw", "alt": f"{h} Draw No Bet"}

class AIEngine:
    @staticmethod
    def generate_viral_fb_post(matches):
        """Uses Groq to generate a unique, persuasive Facebook post"""
        if not matches: return None
        
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        # Prepare data for AI
        selected = matches[:2] # Take top 2
        match_data = ""
        for m in selected:
            match_data += f"- Match: {m['home']} vs {m['away']} ({m['competition']})\n"
            match_data += f"  Odds: Home {m['odds']['1']} | Draw {m['odds']['X']} | Away {m['odds']['2']}\n"
            match_data += f"  Context: Home Rank {m['home_rank']} vs Away Rank {m['away_rank']}\n"

        prompt = f"""
        Act as a professional sports betting syndicate analyst. Write a short, viral Facebook post about today's upcoming football matches.
        
        DATA:
        {match_data}
        
        INSTRUCTIONS:
        1. Start with a killer hook about "Market Errors" or "Trap Odds".
        2. Analyze both matches briefly. Mention the specific odds provided.
        3. Explain WHY there is value (e.g., "The bookies underestimated the home form").
        4. CRITICAL: Do NOT reveal the final winning pick. Say "We have confirmed the winner in the VIP channel".
        5. Use emojis 🔥 📉 💰.
        6. End with a Call to Action to join Telegram: {TELEGRAM_CHANNEL_LINK}
        7. Keep it under 200 words.
        8. Make it look different from generic bot posts. Use varied sentence structure.
        """

        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192", # High quality model
                temperature=0.7,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq Error: {e}")
            # Fallback if AI fails
            return f"🔥 MARKET ALERT 🔥\n\nWe found huge value in {selected[0]['home']} vs {selected[0]['away']}!\n\nThe odds ({selected[0]['odds']['1']}) are dropping fast.\n\n👇 GET THE WINNER HERE:\n{TELEGRAM_CHANNEL_LINK}"

# =============================================================================
# CONTENT GENERATOR
# =============================================================================

class ContentGenerator:
    @staticmethod
    def telegram_feed(matches):
        now_str = datetime.now(GMT).strftime("%d %b")
        title = TextStyler.to_bold_sans("SYNDICATE INTELLIGENCE")
        subtitle = TextStyler.to_mono(f"Daily Briefing | {now_str}")
        
        msg = f"💎 {title}\n{subtitle}\n\n"
        selected = matches[:5]
        
        if not selected: return f"💎 {title}\n\nNo market opportunities right now."

        for m in selected:
            data = LogicEngine.analyze_telegram(m)
            comp = TextStyler.to_bold_sans(m['competition'].upper())
            teams = f"{m['home']} vs {m['away']}"
            
            msg += f"┌── {comp} ──────────\n"
            msg += f"│ ⚔️ {teams}\n"
            msg += f"│ ⏰ {m['start_time']} GMT\n"
            msg += f"│\n"
            msg += f"│ {data['edge']}\n"
            msg += f"│ 🧠 {data['insight']}\n"
            msg += f"│\n"
            msg += f"│ 🎯 𝗠𝗔𝗜𝗡: {TextStyler.to_bold_sans(data['main'])}\n"
            msg += f"└─ 🛡️ 𝗔𝗟𝗧:  {data['alt']}\n\n"

        msg += "────── 🔒 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗔𝗖𝗖𝗘𝗦𝗦 ──────\n"
        msg += "Maximize your edge with our partners:\n\n"
        
        for item in AFFILIATE_CONFIG:
            clean_name = item['name'].split(" ")[1] if " " in item['name'] else item['name']
            emoji = item['name'].split(" ")[0] if " " in item['name'] else "👉"
            msg += f"{emoji} <b><a href=\"{item['link']}\">{clean_name}</a></b>: <i>{item['offer']}</i>\n"
            
        return msg

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
        self.groq_api_key = os.environ.get('GROQ_API_KEY')

    def validate(self):
        return all([self.rapidapi_key, self.telegram_bot_token, self.telegram_chat_id, 
                   self.facebook_page_access_token, self.facebook_page_id, self.groq_api_key])

def main():
    config = Config()
    if not config.validate(): 
        logger.error("Missing Env Vars")
        return
    
    bot = FootballAPI(config.rapidapi_key)
    logger.info("🚀 Fetching market data...")
    matches = bot.get_matches()
    
    if not matches: return

    # 1. Telegram (Standard Syndicate Style)
    tg_content = ContentGenerator.telegram_feed(matches)
    try:
        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        requests.post(url, json={"chat_id": config.telegram_chat_id, "text": tg_content, "parse_mode": "HTML", "disable_web_page_preview": True})
        logger.info("✅ Telegram Sent")
    except Exception as e: logger.error(f"Telegram Error: {e}")

    # 2. Facebook (AI Generated)
    fb_content = AIEngine.generate_viral_fb_post(matches)
    if fb_content:
        try:
            url = f"https://graph.facebook.com/v18.0/{config.facebook_page_id}/feed"
            requests.post(url, data={"message": fb_content, "access_token": config.facebook_page_access_token})
            logger.info("✅ Facebook Sent (AI Generated)")
        except Exception as e: logger.error(f"Facebook Error: {e}")

if __name__ == "__main__":
    main()
