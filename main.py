#!/usr/bin/env python3
"""
Football Data Automation Bot - OPTIMIZED FOR 500 REQUESTS/MONTH
Fetches football data from RapidAPI and posts to Telegram & Facebook
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
import hashlib

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Timezone
GMT = pytz.timezone('GMT')

# API Request Tracking (for monitoring)
API_REQUESTS_THIS_RUN = 0
MAX_API_CALLS_PER_RUN = 1  # STRICT: Only 1 API call per run to save quota

# Affiliate Links (for Telegram only)
AFFILIATE_LINKS = {
    "🎰 Stake": "https://stake.com/?c=GlobalScoreUpdates",
    "📊 Linebet": "https://linebet.com?bf=695d695c66d7a_13053616523",
    "🏆 1xBet": "https://ma-1xbet.com?bf=695d66e22c1b5_7531017325"
}

# Telegram Channel Link (for Facebook posts)
TELEGRAM_CHANNEL_LINK = "https://t.me/+xAQ3DCVJa8A2ZmY8"

# RapidAPI Configuration
RAPIDAPI_HOST = "livescore6.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"

# Major Leagues/Competitions to focus on
MAJOR_COMPETITIONS = [
    "Premier League", "La Liga", "Serie A", "Bundesliga",
    "Ligue 1", "Champions League", "Europa League",
    "World Cup", "Euro", "FA Cup", "Copa del Rey",
    "Conference League", "Nations League", "MLS", "Liga MX"
]

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

class Config:
    """Configuration class to manage environment variables"""

    def __init__(self):
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY')
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.facebook_page_access_token = os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN')
        self.facebook_page_id = os.environ.get('FACEBOOK_PAGE_ID')

    def validate(self) -> bool:
        """Validate all required environment variables are set"""
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

        logger.info("✅ All environment variables validated successfully")
        return True


config = Config()

# =============================================================================
# API CLIENT - OPTIMIZED FOR RATE LIMITS
# =============================================================================

class FootballAPI:
    """Client for fetching football data from RapidAPI LiveScore - OPTIMIZED"""

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
        """Make API request with error handling and counting"""
        global API_REQUESTS_THIS_RUN
        
        # Check if we've exceeded our per-run limit
        if self.request_count >= MAX_API_CALLS_PER_RUN:
            logger.warning(f"⚠️ Skipping API call - already made {self.request_count} calls this run")
            return None
        
        url = f"{RAPIDAPI_BASE_URL}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)
            self.request_count += 1
            API_REQUESTS_THIS_RUN += 1
            
            logger.info(f"📡 API Request #{self.request_count} - Status: {response.status_code}")
            
            # Log remaining quota if available in headers
            remaining = response.headers.get('X-RateLimit-Requests-Remaining', 'Unknown')
            logger.info(f"📊 API Requests Remaining: {remaining}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None

    def get_matches_by_date(self, date: str) -> Optional[List[Dict]]:
        """
        Get matches for a specific date - THIS IS OUR MAIN ENDPOINT
        Date format: YYYYMMDD
        """
        endpoint = "/matches/v2/list-by-date"
        params = {
            "Category": "soccer",
            "Date": date,
            "Timezone": "0"  # GMT
        }

        data = self._make_request(endpoint, params)
        if data and 'Stages' in data:
            return self._parse_matches(data['Stages'])
        return None

    def _parse_matches(self, stages: List[Dict]) -> List[Dict]:
        """Parse and extract match information from API response"""
        matches = []

        for stage in stages:
            competition_name = stage.get('Snm', stage.get('Cnm', 'Unknown League'))
            country = stage.get('Cnm', '')

            events = stage.get('Events', [])

            for event in events:
                home_team = 'Unknown'
                away_team = 'Unknown'
                home_position = None
                away_position = None

                if event.get('T1') and len(event.get('T1', [])) > 0:
                    home_team = event['T1'][0].get('Nm', 'Unknown')
                    home_position = event['T1'][0].get('Rnk', None)

                if event.get('T2') and len(event.get('T2', [])) > 0:
                    away_team = event['T2'][0].get('Nm', 'Unknown')
                    away_position = event['T2'][0].get('Rnk', None)

                # Determine match status
                eps = event.get('Eps', '')
                is_live = eps in ['HT', '1H', '2H', 'LIVE', 'ET', 'BT', 'PT']
                is_finished = eps in ['FT', 'AET', 'PEN', 'AP']
                
                match = {
                    'id': event.get('Eid', ''),
                    'competition': competition_name,
                    'country': country,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': event.get('Tr1', '-'),
                    'away_score': event.get('Tr2', '-'),
                    'status': self._get_match_status(event),
                    'start_time': self._parse_time(event.get('Esd', '')),
                    'start_time_raw': event.get('Esd', ''),
                    'is_live': is_live,
                    'is_finished': is_finished,
                    'minute': eps if is_live else '',
                    'is_major': self._is_major_match(competition_name),
                    'home_position': home_position,
                    'away_position': away_position,
                }

                matches.append(match)

        return matches

    def _get_match_status(self, event: Dict) -> str:
        """Determine match status"""
        eps = event.get('Eps', '')

        status_map = {
            'NS': 'Upcoming',
            'HT': 'Half Time',
            '1H': 'First Half',
            '2H': 'Second Half',
            'FT': 'Finished',
            'AET': 'After Extra Time',
            'PEN': 'Penalties',
            'AP': 'After Penalties',
            'POST': 'Postponed',
            'CANC': 'Cancelled',
            'ABD': 'Abandoned',
            'LIVE': 'Live',
            'ET': 'Extra Time',
            'BT': 'Break Time',
            'PT': 'Penalty Shootout'
        }

        return status_map.get(eps, eps if eps else 'Upcoming')

    def _parse_time(self, time_str: str) -> str:
        """Parse and format match time to GMT"""
        if not time_str:
            return "TBD"

        try:
            dt = datetime.strptime(str(time_str)[:14], "%Y%m%d%H%M%S")
            dt = GMT.localize(dt)
            return dt.strftime("%H:%M GMT")
        except (ValueError, TypeError):
            return "TBD"

    def _is_major_match(self, competition: str) -> bool:
        """Check if match is from a major competition"""
        competition_lower = competition.lower()
        return any(major.lower() in competition_lower for major in MAJOR_COMPETITIONS)


# =============================================================================
# CONTENT GENERATORS
# =============================================================================

class ContentGenerator:
    """Generate formatted content for Telegram and Facebook"""

    @staticmethod
    def generate_prediction(match: Dict) -> str:
        """Generate simple prediction based on available data"""
        home = match['home_team']
        away = match['away_team']

        home_pos = match.get('home_position')
        away_pos = match.get('away_position')

        if home_pos and away_pos:
            if home_pos < away_pos:
                return f"🎯 Prediction: {home} to Win or Draw (Home Advantage)"
            elif away_pos < home_pos:
                return f"🎯 Prediction: {away} to Win (Away Form)"
            else:
                return "🎯 Prediction: Close Match - Draw Possible"

        if match.get('is_major'):
            return "🎯 Prediction: High-Scoring Match Expected!"

        return "🎯 Prediction: Home Team Slight Favorite"

    @staticmethod
    def generate_telegram_match_post(match: Dict, post_type: str = "upcoming") -> str:
        """Generate Telegram message for any match type"""
        
        home = match['home_team']
        away = match['away_team']
        competition = match['competition']
        
        if post_type == "live":
            home_score = match.get('home_score', '0')
            away_score = match.get('away_score', '0')
            minute = match.get('minute', '')
            minute_display = f" ({minute}')" if minute else ""
            
            message = f"""
⚽ *🔴 LIVE{minute_display}* ⚽

🏆 *{competition}*

🔵 *{home}*  *{home_score}*
         🆚
🔴 *{away}*  *{away_score}*

━━━━━━━━━━━━━━━━━━━━━

🔥 *The match is ON! Bet now for best odds!* 🔥

💰 *BET NOW & WIN BIG!* 💰

"""
        elif post_type == "finished":
            home_score = match.get('home_score', '0')
            away_score = match.get('away_score', '0')
            
            message = f"""
⚽ *✅ FULL TIME* ⚽

🏆 *{competition}*

🔵 *{home}*  *{home_score}*
         🆚
🔴 *{away}*  *{away_score}*

━━━━━━━━━━━━━━━━━━━━━

📊 *Check our next predictions!*

💰 *BET ON UPCOMING MATCHES!* 💰

"""
        else:  # upcoming
            prediction = ContentGenerator.generate_prediction(match)
            start_time = match.get('start_time', 'TBD')
            
            message = f"""
⚽ *UPCOMING MATCH ALERT* ⚽

🏆 *{competition}*

🔵 *{home}*
         🆚
🔴 *{away}*

⏰ *Kick-off:* {start_time}

{prediction}

━━━━━━━━━━━━━━━━━━━━━

💰 *BET NOW & WIN BIG!* 💰

Place your bets on these trusted platforms:

"""

        # Add affiliate links
        for name, link in AFFILIATE_LINKS.items():
            message += f"👉 {name}: {link}\n"

        message += """
━━━━━━━━━━━━━━━━━━━━━

🔔 *Turn on notifications!*

#Football #Betting #LiveScore
"""
        return message.strip()

    @staticmethod
    def generate_telegram_daily_summary(matches: List[Dict], live_matches: List[Dict] = None) -> str:
        """Generate comprehensive daily summary for Telegram"""

        now_gmt = datetime.now(GMT)
        today_str = now_gmt.strftime("%A, %B %d, %Y")
        time_str = now_gmt.strftime("%H:%M GMT")

        message = f"""
📅 *FOOTBALL UPDATE* 📅
📆 {today_str}
🕐 {time_str}

━━━━━━━━━━━━━━━━━━━━━
"""

        # Add live matches first if any
        if live_matches:
            message += "\n🔴 *LIVE NOW:*\n"
            for match in live_matches[:5]:
                home = match['home_team']
                away = match['away_team']
                home_score = match.get('home_score', '0')
                away_score = match.get('away_score', '0')
                minute = match.get('minute', '')
                message += f"⚽ {home} {home_score}-{away_score} {away}"
                if minute:
                    message += f" ({minute}')"
                message += "\n"

        # Group upcoming by competition
        upcoming = [m for m in matches if m['status'] == 'Upcoming']
        major_upcoming = [m for m in upcoming if m.get('is_major')][:10]
        
        if major_upcoming:
            message += "\n⏰ *UPCOMING TODAY:*\n"
            
            by_competition = {}
            for match in major_upcoming:
                comp = match['competition']
                if comp not in by_competition:
                    by_competition[comp] = []
                by_competition[comp].append(match)

            for comp, comp_matches in list(by_competition.items())[:5]:
                message += f"\n🏆 *{comp}*\n"
                for match in comp_matches[:3]:
                    start_time = match['start_time']
                    home = match['home_team']
                    away = match['away_team']
                    message += f"  ⏰ {start_time} | {home} vs {away}\n"

        # Add finished results
        finished = [m for m in matches if m.get('is_finished') and m.get('is_major')][:5]
        if finished:
            message += "\n✅ *RECENT RESULTS:*\n"
            for match in finished:
                home = match['home_team']
                away = match['away_team']
                home_score = match.get('home_score', '0')
                away_score = match.get('away_score', '0')
                message += f"⚽ {home} {home_score}-{away_score} {away}\n"

        message += """
━━━━━━━━━━━━━━━━━━━━━

💰 *READY TO WIN BIG?* 💰

Bet on your favorite teams:

"""
        for name, link in AFFILIATE_LINKS.items():
            message += f"👉 {name}: {link}\n"

        message += """
━━━━━━━━━━━━━━━━━━━━━

🔔 *Follow for more updates!*
📲 *Enable notifications!*

#Football #Betting #Predictions #LiveScore
"""
        return message.strip()

    @staticmethod
    def generate_facebook_teaser(matches: List[Dict], live_matches: List[Dict] = None) -> str:
        """Generate Facebook teaser post (NO affiliate links!)"""

        now_gmt = datetime.now(GMT)
        today_str = now_gmt.strftime("%A, %B %d")

        # Prioritize content
        if live_matches:
            # Live match teaser
            match = live_matches[0]
            home = match['home_team']
            away = match['away_team']
            home_score = match.get('home_score', '0')
            away_score = match.get('away_score', '0')
            
            return f"""⚡ LIVE NOW ⚡

⚽ {home} {home_score} - {away_score} {away}

🔥 Get INSTANT live scores & betting tips!

👇 Join our Telegram for FREE! 👇
📲 {TELEGRAM_CHANNEL_LINK}

#Football #LiveScore #MatchDay"""

        # Upcoming matches teaser
        major_upcoming = [m for m in matches if m['status'] == 'Upcoming' and m.get('is_major')]
        
        if major_upcoming:
            match_list = ""
            for match in major_upcoming[:3]:
                home = match['home_team']
                away = match['away_team']
                match_list += f"⚽ {home} vs {away}\n"

            return f"""🔥 TODAY'S BIG MATCHES! 🔥
📅 {today_str}

{match_list}
Want our EXCLUSIVE predictions?

👇 Join our Telegram for FREE tips! 👇
📲 {TELEGRAM_CHANNEL_LINK}

#Football #Predictions #MatchDay #FreeTips"""

        # General teaser
        return f"""⚽ FOOTBALL UPDATE ⚽
📅 {today_str}

🔥 Live scores, predictions & betting tips!

Get EXCLUSIVE insights for FREE!

👇 Join our Telegram NOW! 👇
📲 {TELEGRAM_CHANNEL_LINK}

#Football #Predictions #LiveScore"""


# =============================================================================
# SOCIAL MEDIA CLIENTS
# =============================================================================

class TelegramClient:
    """Client for posting to Telegram"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram channel"""
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                logger.info("✅ Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False


class FacebookClient:
    """Client for posting to Facebook Page"""

    def __init__(self, page_id: str, access_token: str):
        self.page_id = page_id
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/v18.0/{page_id}"

    def post_message(self, message: str) -> bool:
        """Post message to Facebook Page"""
        url = f"{self.base_url}/feed"

        payload = {
            "message": message,
            "access_token": self.access_token
        }

        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            if 'id' in result:
                logger.info(f"✅ Facebook post created: {result['id']}")
                return True
            else:
                logger.error(f"Facebook API error: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post to Facebook: {e}")
            return False


# =============================================================================
# MAIN ORCHESTRATOR - OPTIMIZED FOR 500 REQUESTS/MONTH
# =============================================================================

class FootballBot:
    """Main orchestrator - OPTIMIZED for rate limits"""

    def __init__(self):
        self.api = FootballAPI(config.rapidapi_key)
        self.telegram = TelegramClient(config.telegram_bot_token, config.telegram_chat_id)
        self.facebook = FacebookClient(config.facebook_page_id, config.facebook_page_access_token)
        self.content = ContentGenerator()

    def run(self):
        """Main execution flow - SINGLE API CALL STRATEGY"""
        logger.info("🚀 Starting Football Bot (OPTIMIZED MODE)...")
        logger.info(f"📊 Max API calls this run: {MAX_API_CALLS_PER_RUN}")

        # Get current time in GMT
        now_gmt = datetime.now(GMT)
        today = now_gmt.strftime("%Y%m%d")
        current_hour = now_gmt.hour

        logger.info(f"📅 Current time (GMT): {now_gmt.strftime('%Y-%m-%d %H:%M:%S')}")

        # SINGLE API CALL - Get today's matches (includes live, upcoming, finished)
        matches = self.api.get_matches_by_date(today)
        
        if not matches:
            logger.warning("No matches found for today")
            self._post_no_matches_update()
            return

        logger.info(f"📊 Found {len(matches)} total matches")

        # Categorize matches from single API response
        live_matches = [m for m in matches if m.get('is_live') and m.get('is_major')]
        upcoming_matches = [m for m in matches if m['status'] == 'Upcoming' and m.get('is_major')]
        finished_matches = [m for m in matches if m.get('is_finished') and m.get('is_major')]

        logger.info(f"🔴 Live: {len(live_matches)} | ⏰ Upcoming: {len(upcoming_matches)} | ✅ Finished: {len(finished_matches)}")

        # === SMART POSTING LOGIC ===
        
        # Strategy: Post ONE comprehensive update to each platform
        
        # 1. TELEGRAM - Comprehensive update with all affiliate links
        telegram_msg = self.content.generate_telegram_daily_summary(matches, live_matches)
        self.telegram.send_message(telegram_msg)
        time.sleep(2)

        # 2. If there's a big live match, post it separately to Telegram
        if live_matches:
            top_live = live_matches[0]
            live_msg = self.content.generate_telegram_match_post(top_live, "live")
            self.telegram.send_message(live_msg)
            time.sleep(2)

        # 3. FACEBOOK - Single teaser post (drives traffic to Telegram)
        facebook_msg = self.content.generate_facebook_teaser(matches, live_matches)
        self.facebook.post_message(facebook_msg)

        # Log API usage
        logger.info(f"📡 Total API requests this run: {API_REQUESTS_THIS_RUN}")
        logger.info("✅ Football Bot execution completed!")

    def _post_no_matches_update(self):
        """Post when no matches are found"""
        now_gmt = datetime.now(GMT)
        
        message = f"""
⚽ *FOOTBALL UPDATE* ⚽
📅 {now_gmt.strftime('%A, %B %d, %Y')}

No major matches scheduled right now.

Stay tuned for upcoming fixtures!

━━━━━━━━━━━━━━━━━━━━━

💰 *Check out these platforms:*

"""
        for name, link in AFFILIATE_LINKS.items():
            message += f"👉 {name}: {link}\n"

        self.telegram.send_message(message.strip())


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("⚽ FOOTBALL BOT - OPTIMIZED FOR 500 REQ/MONTH ⚽")
    logger.info("=" * 60)

    if not config.validate():
        logger.error("❌ Configuration validation failed. Exiting.")
        sys.exit(1)

    try:
        bot = FootballBot()
        bot.run()
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info(f"📊 TOTAL API REQUESTS USED: {API_REQUESTS_THIS_RUN}")
    logger.info("✅ Bot execution completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
