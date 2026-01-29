#!/usr/bin/env python3
"""
Football Data Automation Bot - SYNDICATE EDITION V7 (ULTIMATE)
Features:
1. Groq AI for viral Facebook captions.
2. Pillow Image Generator (Pro Dark Mode with Auto-Fonts).
3. Strict Future-Only Filter (No past games).
4. Win/Loss Tracking via history.json.
5. Simulated Fair Odds Engine.
"""

import os
import sys
import json
import requests
import io
from datetime import datetime, timedelta
import pytz
import logging
import hashlib
import random
from PIL import Image, ImageDraw, ImageFont
from groq import Groq

# =============================================================================
# CONFIGURATION
# =============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

GMT = pytz.timezone('GMT')
API_REQUESTS_THIS_RUN = 0
MAX_API_CALLS_PER_RUN = 1
HISTORY_FILE = 'history.json'

# Affiliate Hooks (HTML Ready)
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
    "Championship", "Super Lig"
]

POWERHOUSE_TEAMS = [
    "Man City", "Liverpool", "Arsenal", "Real Madrid", "Barcelona",
    "Bayern", "Leverkusen", "Inter", "Juve", "Milan", "PSG",
    "Benfica", "Porto", "Al Hilal", "Al Nassr", "Chelsea"
]

# =============================================================================
# 📜 HISTORY MANAGER
# =============================================================================

class HistoryManager:
    @staticmethod
    def load_history():
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f: return json.load(f)
            except: return {}
        return {}

    @staticmethod
    def save_history(history):
        with open(HISTORY_FILE, 'w') as f: json.dump(history, f, indent=4)

    @staticmethod
    def check_results(matches):
        """Checks if yesterday's bets won"""
        history = HistoryManager.load_history()
        wins = []
        finished = [m for m in matches if m['status'] in ['FT', 'AET', 'PEN']]
        
        for m in finished:
            mid = f"{m['home']}-{m['away']}"
            if mid in history:
                pick = history[mid]['pick']
                hs, as_ = int(m['home_score']), int(m['away_score'])
                won = False
                
                # Simple Win Logic
                if "Win" in pick:
                    if m['home'] in pick and hs > as_: won = True
                    if m['away'] in pick and as_ > hs: won = True
                elif "Over" in pick and (hs + as_) > 2: won = True
                elif "Both Teams" in pick and hs > 0 and as_ > 0: won = True
                
                if won:
                    wins.append(f"{m['home']} vs {m['away']}")
                    del history[mid] # Remove after verifying
        
        HistoryManager.save_history(history)
        return wins

    @staticmethod
    def add_pending_bets(matches):
        history = HistoryManager.load_history()
        for m in matches[:5]:
            mid = f"{m['home']}-{m['away']}"
            if 'main' in m:
                history[mid] = {"date": datetime.now().strftime("%Y-%m-%d"), "pick": m['main']}
        HistoryManager.save_history(history)

# =============================================================================
# 🔢 ODDS ENGINE (Simulated)
# =============================================================================

class OddsEngine:
    @staticmethod
    def simulate_odds(match):
        """Generates realistic fair odds to save API credits"""
        r1, r2 = match['home_rank'], match['away_rank']
        h_pow = any(p in match['home'] for p in POWERHOUSE_TEAMS)
        
        h_odd = 2.40; d_odd = 3.20; a_odd = 2.90
        
        if h_pow: h_odd = 1.35; a_odd = 7.50
        elif abs(r1 - r2) > 8 and r1 < r2: h_odd = 1.75; a_odd = 4.20
        
        # Add random noise for realism
        h_odd = round(h_odd + random.uniform(-0.05, 0.05), 2)
        a_odd = round(a_odd + random.uniform(-0.05, 0.05), 2)
        d_odd = round(d_odd + random.uniform(-0.05, 0.05), 2)
        return {'1': h_odd, 'X': d_odd, '2': a_odd}

# =============================================================================
# 🎨 PRO IMAGE GENERATOR (Auto-Downloads Fonts)
# =============================================================================

class ImageGenerator:
    @staticmethod
    def get_font(size):
        """Downloads a Pro Font (Oswald) for consistent premium look"""
        font_url = "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald-Bold.ttf"
        try:
            resp = requests.get(font_url, timeout=10)
            return ImageFont.truetype(io.BytesIO(resp.content), size)
        except:
            return ImageFont.load_default()

    @staticmethod
    def create_match_card(match):
        """Generates a Visual Betting Card"""
        try:
            W, H = 1080, 1080
            bg_color = '#0f172a' # Dark Slate
            accent_color = '#22c55e' # Neon Green
            
            img = Image.new('RGB', (W, H), color=bg_color)
            draw = ImageDraw.Draw(img)
            
            font_xl = ImageGenerator.get_font(110)
            font_lg = ImageGenerator.get_font(70)
            font_md = ImageGenerator.get_font(50)

            # Header
            draw.text((50, 80), "💎 SYNDICATE INTELLIGENCE", font=font_lg, fill=accent_color)
            draw.line([(50, 180), (1030, 180)], fill=accent_color, width=5)

            # Match Info
            draw.text((50, 250), match['competition'].upper(), font=font_md, fill='#94a3b8')
            
            # Teams (Home vs Away)
            draw.text((50, 380), match['home'], font=font_xl, fill='white')
            draw.text((50, 520), "VS", font=font_lg, fill='#64748b')
            draw.text((50, 620), match['away'], font=font_xl, fill='white')
            
            # Pick Box
            box_y = 850
            draw.rectangle([0, box_y, 1080, 1080], fill='#1e293b')
            draw.line([(0, box_y), (1080, box_y)], fill=accent_color, width=4)
            
            draw.text((50, box_y + 40), "OFFICIAL SYNDICATE PICK:", font=font_md, fill='#94a3b8')
            draw.text((50, box_y + 110), str(match['main']).upper(), font=font_lg, fill=accent_color)

            filename = "post_image.jpg"
            img.save(filename)
            return filename
        except Exception as e:
            logger.error(f"Image Gen Error: {e}")
            return None

# =============================================================================
# 🧠 LOGIC & AI ENGINE
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

class LogicEngine:
    @staticmethod
    def analyze(match):
        h, a = match['home'], match['away']
        comp = match['competition']
        
        style = "BALANCED"
        for k, v in LEAGUE_PROFILES.items():
            if any(l in comp for l in v): style = k; break
        
        h_pow = any(p in h for p in POWERHOUSE_TEAMS)
        a_pow = any(p in a for p in POWERHOUSE_TEAMS)
        match_hash = int(hashlib.md5(f"{h}{a}".encode()).hexdigest(), 16)

        # Logic A: Powerhouse Home
        if h_pow and not a_pow:
            return {"edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Sharp Action Home", "insight": "Home xG metrics trending 20% above avg.", "main": f"{h} -1.0 AH", "alt": f"{h} to Win & Over 1.5"}
        
        # Logic B: Powerhouse Away
        if a_pow and not h_pow:
            return {"edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Visitors undervalued", "insight": "Class disparity favors visitors.", "main": f"{a} to Win", "alt": "Over 1.5 Goals"}
        
        # Logic C: High Scoring
        if style == "HIGH_SCORING":
            return {"edge": "🔥 𝚅𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢 𝙰𝚕𝚎𝚛𝚝", "insight": "Defensive injury crisis creating value.", "main": "Over 2.5 Goals", "alt": "Both Teams to Score"}

        # Logic D: Balanced / Random
        seed = len(h) + len(a)
        if seed % 3 == 0:
            return {"edge": "📈 𝙵𝚘𝚛𝚖 𝙼𝚘𝚖𝚎𝚗𝚝𝚞𝚖", "insight": "Both teams scoring consistently.", "main": "Both Teams to Score", "alt": "Over 2.5 Goals"}
        elif seed % 3 == 1:
            return {"edge": "🛡️ 𝚂𝚊𝚏𝚎𝚝𝚢 𝙵𝚒𝚛𝚜𝚝", "insight": "Home advantage is key.", "main": f"{h} Win or Draw", "alt": f"{h} Draw No Bet"}
        else:
            return {"edge": "🔥 𝙾𝚙𝚎𝚗 𝙶𝚊𝚖𝚎", "insight": "Weak transition defense.", "main": "Over 2.0 Goal Line", "alt": "Goal in Both Halves"}

class AIEngine:
    @staticmethod
    def generate_fb_caption(matches, wins):
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        m = matches[0]
        
        intro = ""
        if wins: intro = f"✅ WE SMASHED THE BOOKIES AGAIN! Yesterday: {wins[0]} won easily! 💰\n\n"
        
        prompt = f"""
        Write a viral Facebook betting post.
        {intro}
        Match: {m['home']} vs {m['away']}
        Insight: {m['insight']}
        Odds: {m['odds']['1']} / {m['odds']['2']}
        
        Hook: Mention "Market Trap", "Smart Money", or "Vegas Odds Error".
        Instruction: Analyze briefly why there is value.
        Call to Action: Check the final pick in Telegram. Do NOT reveal the winner here.
        Tone: Professional Syndicate. Use emojis.
        Length: Short (under 150 words).
        """
        
        try:
            return client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192"
            ).choices[0].message.content
        except:
            return f"{intro}🔥 SMART MONEY ALERT: {m['home']} vs {m['away']}!\n\nThe sharps are moving heavily here. Don't be on the wrong side.\n\n👇 OFFICIAL PICK:\n{TELEGRAM_CHANNEL_LINK}"

# =============================================================================
# 📢 CONTENT GENERATOR
# =============================================================================

class ContentGenerator:
    @staticmethod
    def telegram_feed(matches, wins):
        now_str = datetime.now(GMT).strftime("%d %b")
        title = TextStyler.to_bold_sans("SYNDICATE INTELLIGENCE")
        subtitle = TextStyler.to_mono(f"Daily Briefing | {now_str}")
        
        msg = f"💎 {title}\n{subtitle}\n\n"
        
        if wins:
            msg += f"✅ <b>YESTERDAY'S PROFITS:</b>\n"
            for w in wins[:2]: msg += f"💰 {w} ✅\n"
            msg += "\n"

        selected = matches[:5]
        if not selected: return f"💎 {title}\n\nNo market opportunities right now."

        for m in selected:
            data = LogicEngine.analyze(m)
            # Inject calculated logic back into match object for later
            m.update(data)
            
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
            clean = item['name'].split(" ")[1] if " " in item['name'] else item['name']
            emoji = item['name'].split(" ")[0] if " " in item['name'] else "👉"
            msg += f"{emoji} <b><a href=\"{item['link']}\">{clean}</a></b>: <i>{item['offer']}</i>\n"
            
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
    if not config.validate(): return
    
    # 1. Fetch Data
    api = requests.Session()
    date_str = datetime.now(GMT).strftime("%Y%m%d")
    try:
        url = f"{RAPIDAPI_BASE_URL}/matches/v2/list-by-date"
        data = api.get(url, params={"Category": "soccer", "Date": date_str, "Timezone": "0"}, 
                      headers={"X-RapidAPI-Key": config.rapidapi_key}).json()
        raw_matches = data.get('Stages', [])
    except: return

    # 2. Process & Filter
    matches = []
    now = datetime.now(GMT)
    
    for stage in raw_matches:
        is_major = any(m in stage.get('Snm', '') for m in MAJOR_COMPETITIONS)
        for evt in stage.get('Events', []):
            try:
                t_str = str(evt.get('Esd', ''))
                if len(t_str) < 12: continue
                dt = GMT.localize(datetime.strptime(t_str[:14], "%Y%m%d%H%M%S"))
                
                status = evt.get('Eps', 'NS')
                h = evt.get('T1')[0].get('Nm')
                a = evt.get('T2')[0].get('Nm')
                
                matches.append({
                    'home': h, 'away': a,
                    'status': status,
                    'start_time_dt': dt,
                    'start_time': dt.strftime("%H:%M"),
                    'competition': stage.get('Snm', 'Cup'),
                    'home_score': evt.get('Tr1', 0), 'away_score': evt.get('Tr2', 0),
                    'home_rank': 50, 'away_rank': 50,
                    'is_major': is_major, 'priority': 1 if is_major else 2
                })
            except: continue

    # 3. Check Wins (using ALL matches including finished ones)
    wins = HistoryManager.check_results(matches)

    # 4. Filter Future Only (Strict)
    future_matches = [m for m in matches if m['start_time_dt'] > now and m['status'] == 'NS']
    future_matches.sort(key=lambda x: (x['priority'], x['start_time']))
    
    if not future_matches: 
        logger.info("No future matches found.")
        return

    # 5. Telegram Post
    tg_text = ContentGenerator.telegram_feed(future_matches, wins)
    requests.post(f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage", 
                 json={"chat_id": config.telegram_chat_id, "text": tg_text, "parse_mode": "HTML", "disable_web_page_preview": True})

    # 6. Facebook Post (Top Match Only)
    top_match = future_matches[0]
    # Re-analyze specifically for image generation to get 'main' pick
    analysis = LogicEngine.analyze(top_match) 
    top_match.update(analysis)
    top_match['odds'] = OddsEngine.simulate_odds(top_match) # Add fake odds for AI
    
    # Generate Img & Text
    img_file = ImageGenerator.create_match_card(top_match)
    fb_text = AIEngine.generate_fb_caption([top_match], wins)
    
    if img_file and fb_text:
        with open(img_file, 'rb') as f:
            requests.post(f"https://graph.facebook.com/v18.0/{config.facebook_page_id}/photos", 
                         data={"message": fb_text, "access_token": config.facebook_page_access_token}, 
                         files={'source': f})

    # 7. Save Bets
    HistoryManager.add_pending_bets(future_matches)

if __name__ == "__main__":
    main()
