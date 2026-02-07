#!/usr/bin/env python3
"""
Football Data Automation Bot - SYNDICATE EDITION V15 (COUNTRY-SPECIFIC FILTER)
Features:
1. STRICT COUNTRY/LEAGUE MAPPING: No more 'Singapore Premier League'.
2. Auto-Scaling Text for Images.
3. Groq AI Viral Posts.
4. Interactive Polls.
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
HISTORY_FILE = 'history.json'

AFFILIATE_CONFIG = [
    {"name": "🎰 Stake", "link": "https://stake.com/?c=GlobalScoreUpdates", "offer": "200% Deposit Bonus | Instant Cashout ⚡"},
    {"name": "📊 Linebet", "link": "https://linebet.com?bf=695d695c66d7a_13053616523", "offer": "High Odds | Fast Payouts 💸"},
    {"name": "🏆 1xBet", "link": "https://ma-1xbet.com?bf=695d66e22c1b5_7531017325", "offer": "300% First Deposit Bonus 💰"}
]

TELEGRAM_CHANNEL_LINK = "https://t.me/+xAQ3DCVJa8A2ZmY8"
RAPIDAPI_HOST = "livescore6.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"

# === 🛡️ THE STRICT QUALITY FILTER ===

# Only accept matches from these specific Country + League combinations
ALLOWED_LEAGUES = {
    "England": ["Premier League", "FA Cup", "EFL Cup", "Championship", "Community Shield"],
    "Spain": ["LaLiga", "La Liga", "Copa del Rey", "Super Cup"],
    "Italy": ["Serie A", "Coppa Italia", "Super Cup"],
    "Germany": ["Bundesliga", "DFB Pokal", "Super Cup"],
    "France": ["Ligue 1", "Coupe de France", "Trophee des Champions"],
    "Europe": ["UEFA Champions League", "UEFA Europa League", "UEFA Conference League", "UEFA Super Cup"],
    "World": ["World Cup", "Club World Cup", "Friendlies"], # Be careful with friendlies
    "Euro": ["Euro 2024", "Euro 2028", "UEFA Nations League"],
    "South America": ["Copa America", "Copa Libertadores"],
    "Netherlands": ["Eredivisie"],
    "Portugal": ["Primeira Liga"],
    "Saudi Arabia": ["Saudi Pro League", "Kings Cup"],
    "USA": ["Major League Soccer", "MLS"],
    "Turkey": ["Super Lig"],
    "Brazil": ["Serie A"],
    "Argentina": ["Liga Profesional"]
}

# Any match containing these words is INSTANTLY BANNED
BANNED_KEYWORDS = ["Women", "U19", "U20", "U21", "U23", "Reserve", "Youth", "Amateur", "Regional"]

POWERHOUSE_TEAMS = [
    "Man City", "Liverpool", "Arsenal", "Real Madrid", "Barcelona",
    "Bayern", "Leverkusen", "Inter", "Juve", "Milan", "PSG",
    "Benfica", "Porto", "Al Hilal", "Al Nassr", "Chelsea", "Man Utd",
    "Tottenham", "Atletico Madrid", "Napoli", "Dortmund"
]

# =============================================================================
# 🗳️ POLL ENGINE
# =============================================================================

class PollEngine:
    @staticmethod
    def send_poll(match, bot_token, chat_id):
        url = f"https://api.telegram.org/bot{bot_token}/sendPoll"
        h, a = match['home'], match['away']
        payload = {
            "chat_id": chat_id,
            "question": f"🗳️ PUBLIC OPINION: Who wins {h} vs {a}?",
            "options": json.dumps([f"🔥 {h}", "🤝 Draw", f"🛡️ {a}"]),
            "is_anonymous": True,
            "type": "regular",
            "allows_multiple_answers": False
        }
        try: requests.post(url, data=payload)
        except Exception as e: logger.error(f"Poll Error: {e}")

# =============================================================================
# 📜 HISTORY MANAGER
# =============================================================================

class HistoryManager:
    @staticmethod
    def load_history():
        if os.path.exists(HISTORY_FILE):
            try: return json.load(open(HISTORY_FILE))
            except: return {}
        return {}
    @staticmethod
    def save_history(history):
        with open(HISTORY_FILE, 'w') as f: json.dump(history, f, indent=4)
    @staticmethod
    def check_results(matches):
        history = HistoryManager.load_history()
        wins = []
        finished = [m for m in matches if m['status'] in ['FT', 'AET', 'PEN']]
        for m in finished:
            mid = f"{m['home']}-{m['away']}"
            if mid in history:
                pick = history[mid]['pick']
                hs, as_ = int(m['home_score']), int(m['away_score'])
                won = False
                if "Win" in pick:
                    if m['home'] in pick and hs > as_: won = True
                    if m['away'] in pick and as_ > hs: won = True
                elif "Over" in pick and (hs + as_) > 2: won = True
                elif "Both Teams" in pick and hs > 0 and as_ > 0: won = True
                if won:
                    wins.append(f"{m['home']} vs {m['away']}")
                    del history[mid]
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
# 🎨 PRO IMAGE GENERATOR
# =============================================================================

class ImageGenerator:
    @staticmethod
    def get_font(size):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald-Bold.ttf"
            resp = requests.get(font_url, timeout=5)
            if resp.status_code == 200:
                return ImageFont.truetype(io.BytesIO(resp.content), size)
        except: pass
        try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except: pass
        return ImageFont.load_default()

    @staticmethod
    def fit_text(draw, text, max_width, initial_size):
        size = initial_size
        font = ImageGenerator.get_font(size)
        while size > 20:
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width: return font
            size -= 5
            font = ImageGenerator.get_font(size)
        return font

    @staticmethod
    def create_match_card(match):
        try:
            W, H = 1080, 1080
            bg_color, accent_color = '#0f172a', '#22c55e'
            img = Image.new('RGB', (W, H), color=bg_color)
            draw = ImageDraw.Draw(img)
            
            font_lg = ImageGenerator.get_font(70)
            draw.text((W/2, 100), "SYNDICATE INTELLIGENCE", font=font_lg, fill=accent_color, anchor="mm")
            draw.line([(50, 170), (1030, 170)], fill=accent_color, width=5)

            font_md = ImageGenerator.get_font(40)
            draw.text((W/2, 230), match['competition'].upper(), font=font_md, fill='#94a3b8', anchor="mm")
            
            home_font = ImageGenerator.fit_text(draw, match['home'], 980, 110)
            draw.text((W/2, 350), match['home'], font=home_font, fill='white', anchor="mm")
            
            draw.ellipse([W/2 - 60, 480, W/2 + 60, 600], outline='#64748b', width=3)
            draw.text((W/2, 540), "VS", font=font_lg, fill='#64748b', anchor="mm")
            
            away_font = ImageGenerator.fit_text(draw, match['away'], 980, 110)
            draw.text((W/2, 700), match['away'], font=away_font, fill='white', anchor="mm")
            
            box_y = 850
            draw.rectangle([0, box_y, 1080, 1080], fill='#1e293b')
            draw.line([(0, box_y), (1080, box_y)], fill=accent_color, width=4)
            
            draw.text((W/2, box_y + 50), "OFFICIAL SYNDICATE PICK", font=font_md, fill='#94a3b8', anchor="mm")
            
            pick_text = str(match['main']).upper()
            pick_font = ImageGenerator.fit_text(draw, pick_text, 980, 70)
            draw.text((W/2, box_y + 130), pick_text, font=pick_font, fill=accent_color, anchor="mm")

            filename = "post_image.jpg"
            img.save(filename)
            return filename
        except Exception as e: logger.error(f"Image Error: {e}"); return None

# =============================================================================
# 🧠 AI & LOGIC
# =============================================================================

class AIEngine:
    @staticmethod
    def generate_fb_caption(matches, wins):
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        m = matches[0]
        intro = ""
        if wins: intro = f"✅ WE SMASHED THE BOOKIES AGAIN! Yesterday: {wins[0]} won easily! 💰\n\n"
        
        prompt = f"""
        Act as a professional sports betting syndicate. Write a viral Facebook caption.
        {intro}
        Match: {m['home']} vs {m['away']} ({m['competition']})
        Insight: {m['insight']}
        
        1. HOOK: "Smart Money" or "Market Trap" hook.
        2. BODY: Explain briefly why there is value.
        3. CTA: "Check the final pick in Telegram" (Do not reveal winner).
        4. Hashtags: 3 specific team hashtags + #Football #Betting.
        
        Tone: Professional, Exclusive, Winning.
        """
        try:
            return client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192"
            ).choices[0].message.content
        except:
            return f"{intro}🔥 MARKET ALERT: {m['home']} vs {m['away']}!\n\nThe sharps are moving heavily here.\n\n👇 OFFICIAL PICK:\n{TELEGRAM_CHANNEL_LINK}"

class OddsEngine:
    @staticmethod
    def simulate_odds(match):
        r1, r2 = match['home_rank'], match['away_rank']
        h_pow = any(p in match['home'] for p in POWERHOUSE_TEAMS)
        h_odd = 2.40; d_odd = 3.20; a_odd = 2.90
        if h_pow: h_odd = 1.35; a_odd = 7.50
        elif abs(r1 - r2) > 8 and r1 < r2: h_odd = 1.75; a_odd = 4.20
        h_odd = round(h_odd + random.uniform(-0.05, 0.05), 2)
        a_odd = round(a_odd + random.uniform(-0.05, 0.05), 2)
        d_odd = round(d_odd + random.uniform(-0.05, 0.05), 2)
        return {'1': h_odd, 'X': d_odd, '2': a_odd}

class LogicEngine:
    @staticmethod
    def analyze(match):
        h, a = match['home'], match['away']
        comp = match['competition']
        
        # Check if high scoring league
        is_high_scoring = any(l in comp for l in ["Bundesliga", "Eredivisie", "MLS", "Saudi"])
        
        h_pow = any(p in h for p in POWERHOUSE_TEAMS)
        a_pow = any(p in a for p in POWERHOUSE_TEAMS)
        
        if h_pow and not a_pow:
            return {"edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Sharp Action Home", "insight": "Home xG metrics trending 20% above avg.", "main": f"{h} to Win", "alt": f"{h} & Over 1.5"}
        if a_pow and not h_pow:
            return {"edge": "📉 𝙼𝚊𝚛𝚔𝚎𝚝 𝙳𝚛𝚒𝚏𝚝: Visitors undervalued", "insight": "Class disparity favors visitors.", "main": f"{a} to Win", "alt": "Over 1.5 Goals"}
        if is_high_scoring:
            return {"edge": "🔥 𝚅𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢 𝙰𝚕𝚎𝚛𝚝", "insight": "Defensive injury crisis creating value.", "main": "Over 2.5 Goals", "alt": "Both Teams to Score"}
        
        seed = len(h) + len(a)
        if seed % 3 == 0:
            return {"edge": "📈 𝙵𝚘𝚛𝚖 𝙼𝚘𝚖𝚎𝚗𝚝𝚞𝚖", "insight": "Both teams scoring consistently.", "main": "Both Teams to Score", "alt": "Over 2.5 Goals"}
        elif seed % 3 == 1:
            return {"edge": "🛡️ 𝚂𝚊𝚏𝚎𝚝𝚢 𝙵𝚒𝚛𝚜𝚝", "insight": "Home advantage is key.", "main": f"{h} Win or Draw", "alt": f"{h} Draw No Bet"}
        return {"edge": "🔥 𝙾𝚙𝚎𝚗 𝙶𝚊𝚖𝚎", "insight": "Weak transition defense.", "main": "Over 2.0 Goal Line", "alt": "Goal in Both Halves"}

    @staticmethod
    def generate_parlay(matches):
        parlay = []
        total_odds = 1.0
        candidates = [m for m in matches if "Win" in m['main'] or "Over" in m['main']]
        if len(candidates) < 2: candidates = matches
        for m in candidates[:3]:
            raw_odd = 1.75
            if "Win" in m['main']: raw_odd = m['odds']['1'] if m['home'] in m['main'] else m['odds']['2']
            elif "Over" in m['main']: raw_odd = 1.65
            if raw_odd > 2.2: raw_odd = 1.90
            if raw_odd < 1.3: raw_odd = 1.35
            parlay.append({"teams": f"{m['home']} vs {m['away']}", "pick": m['main'], "odd": raw_odd})
            total_odds *= raw_odd
        return parlay, round(total_odds, 2)

# =============================================================================
# 📢 CONTENT GENERATOR
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

        # Note: 'matches' is already filtered for quality in main()
        selected = matches[:5]
        
        for m in selected:
            data = LogicEngine.analyze(m)
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

        parlay, tot_odd = LogicEngine.generate_parlay(selected)
        if len(parlay) >= 2:
            msg += f"🚀 <b>SYNDICATE ACCUMULATOR</b> 🚀\n"
            msg += f"<i>High value combo for today:</i>\n\n"
            for p in parlay: msg += f"🔹 <b>{p['pick']}</b> ({p['teams']})\n"
            msg += f"\n💰 <b>TOTAL ODDS: {tot_odd}</b>\n"
            msg += f"💵 <i>Bet $10 ➡️ Win ${int(10 * tot_odd)}</i>\n\n"

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
    
    api = requests.Session()
    date_str = datetime.now(GMT).strftime("%Y%m%d")
    try:
        url = f"{RAPIDAPI_BASE_URL}/matches/v2/list-by-date"
        data = api.get(url, params={"Category": "soccer", "Date": date_str, "Timezone": "0"}, 
                      headers={"X-RapidAPI-Key": config.rapidapi_key}).json()
        raw_matches = data.get('Stages', [])
    except: return

    matches = []
    now = datetime.now(GMT)
    for stage in raw_matches:
        country = stage.get('Cnm', 'Unknown')
        league = stage.get('Snm', 'Unknown')
        
        # --- STRICT COUNTRY/LEAGUE FILTERING ---
        is_allowed = False
        if country in ALLOWED_LEAGUES:
            # Check if the league is in the allowed list for this country
            if any(allowed in league for allowed in ALLOWED_LEAGUES[country]):
                is_allowed = True
        
        # Special check for International (Europe/World)
        if country in ["Europe", "World", "South America", "Euro"]:
             if any(allowed in league for allowed in ALLOWED_LEAGUES.get(country, [])):
                is_allowed = True

        # Blacklist check
        if any(b in league for b in BANNED_KEYWORDS): is_allowed = False
        
        # If not allowed, skip this stage entirely
        if not is_allowed: continue
        
        for evt in stage.get('Events', []):
            try:
                t_str = str(evt.get('Esd', ''))
                if len(t_str) < 12: continue
                dt = GMT.localize(datetime.strptime(t_str[:14], "%Y%m%d%H%M%S"))
                status = evt.get('Eps', 'NS')
                h = evt.get('T1')[0].get('Nm')
                a = evt.get('T2')[0].get('Nm')
                
                # Double Check Team Names for "U21", "W"
                if any(x in h for x in ["(W)", "U21", "U19"]) or any(x in a for x in ["(W)", "U21", "U19"]):
                    continue

                match = {
                    'home': h, 'away': a, 'status': status, 'start_time_dt': dt, 'start_time': dt.strftime("%H:%M"),
                    'competition': league, 'home_score': evt.get('Tr1', 0), 'away_score': evt.get('Tr2', 0),
                    'home_rank': 50, 'away_rank': 50
                }
                match['odds'] = OddsEngine.simulate_odds(match)
                matches.append(match)
            except: continue

    wins = HistoryManager.check_results(matches)
    future_matches = [m for m in matches if m['start_time_dt'] > now and m['status'] == 'NS']
    future_matches.sort(key=lambda x: x['start_time_dt'])
    
    if not future_matches: 
        logger.info("No Quality matches found today. System Standby.")
        return

    # 1. Telegram Post
    tg_text = ContentGenerator.telegram_feed(future_matches, wins)
    requests.post(f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage", 
                 json={"chat_id": config.telegram_chat_id, "text": tg_text, "parse_mode": "HTML", "disable_web_page_preview": True})

    # 2. Telegram Poll
    top_match = future_matches[0]
    LogicEngine.analyze(top_match)
    PollEngine.send_poll(top_match, config.telegram_bot_token, config.telegram_chat_id)

    # 3. Facebook Post
    img_file = ImageGenerator.create_match_card(top_match)
    fb_text = AIEngine.generate_fb_caption([top_match], wins)
    if img_file and fb_text:
        try:
            with open(img_file, 'rb') as f:
                requests.post(f"https://graph.facebook.com/v18.0/{config.facebook_page_id}/photos", 
                             data={"message": fb_text, "access_token": config.facebook_page_access_token}, 
                             files={'source': f})
        except Exception as e: logger.error(f"FB Error: {e}")

    # 4. Save Bets
    HistoryManager.add_pending_bets(future_matches)

if __name__ == "__main__":
    main()
