#!/usr/bin/env python3
"""
Football Data Automation Bot
Fetches football data from RapidAPI and posts to Telegram & Facebook
Author: Senior Python Automation Engineer
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
# CONFIGURATION & CONSTANTS
# =============================================================================

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Timezone
GMT = pytz.timezone('GMT')

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
    "World Cup", "Euro", "FA Cup", "Copa del Rey"
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
# API CLIENT - RAPIDAPI (LiveScore)
# =============================================================================

class FootballAPI:
    """Client for fetching football data from RapidAPI LiveScore"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request with error handling"""
        url = f"{RAPIDAPI_BASE_URL}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)
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
        Get matches for a specific date
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

    def get_live_matches(self) -> Optional[List[Dict]]:
        """Get currently live matches"""
        endpoint = "/matches/v2/list-live"
        params = {
            "Category": "soccer",
            "Timezone": "0"
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
            competition_id = stage.get('Sid', '')
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
                    'is_live': event.get('Eps', '') in ['HT', '1H', '2H', 'LIVE'],
                    'minute': event.get('Eps', ''),
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
            'POST': 'Postponed',
            'CANC': 'Cancelled',
            'ABD': 'Abandoned',
            'LIVE': 'Live'
        }

        return status_map.get(eps, eps if eps else 'Unknown')

    def _parse_time(self, time_str: str) -> str:
        """Parse and format match time to GMT"""
        if not time_str:
            return "TBD"

        try:
            # Format: YYYYMMDDHHmmss
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

        # Simple prediction logic
        home_pos = match.get('home_position')
        away_pos = match.get('away_position')

        if home_pos and away_pos:
            if home_pos < away_pos:
                return f"🎯 Prediction: {home} to Win or Draw (Home Advantage)"
            elif away_pos < home_pos:
                return f"🎯 Prediction: {away} to Win (Away Form)"
            else:
                return "🎯 Prediction: Close Match - Draw Possible"

        # Default for big matches
        if match.get('is_major'):
            return "🎯 Prediction: High-Scoring Match Expected!"

        return "🎯 Prediction: Home Team Slight Favorite"

    @staticmethod
    def generate_telegram_upcoming_match(match: Dict) -> str:
        """Generate Telegram message for upcoming match"""
        prediction = ContentGenerator.generate_prediction(match)

        message = f"""
⚽ *UPCOMING MATCH ALERT* ⚽

🏆 *{match['competition']}*

🔵 *{match['home_team']}*
         🆚
🔴 *{match['away_team']}*

⏰ *Kick-off:* {match['start_time']}

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

🔔 *Join our channel for more updates!*
📲 Turn on notifications!

#Football #Betting #Prediction #LiveScore
"""
        return message.strip()

    @staticmethod
    def generate_telegram_live_score(match: Dict) -> str:
        """Generate Telegram message for live/finished match"""

        status_emoji = "🔴 LIVE" if match['is_live'] else "✅ FINAL"
        minute_display = ""
        if match['is_live'] and match['minute']:
            minute_display = f" ({match['minute']}')"

        message = f"""
⚽ *{status_emoji}* ⚽{minute_display}

🏆 *{match['competition']}*

🔵 *{match['home_team']}*  *{match['home_score']}*
         🆚
🔴 *{match['away_team']}*  *{match['away_score']}*

━━━━━━━━━━━━━━━━━━━━━

🔥 *Don't miss out on live betting!* 🔥

💰 *BET NOW & WIN BIG!* 💰

"""
        # Add affiliate links
        for name, link in AFFILIATE_LINKS.items():
            message += f"👉 {name}: {link}\n"

        message += """
━━━━━━━━━━━━━━━━━━━━━

📊 Stay updated with all scores!
🔔 Follow for live updates!

#Football #LiveScore #Betting
"""
        return message.strip()

    @staticmethod
    def generate_telegram_daily_summary(matches: List[Dict]) -> str:
        """Generate daily matches summary for Telegram"""

        today_gmt = datetime.now(GMT).strftime("%A, %B %d, %Y")

        message = f"""
📅 *FOOTBALL MATCHES TODAY* 📅
📆 {today_gmt}

━━━━━━━━━━━━━━━━━━━━━

"""
        # Group by competition
        by_competition = {}
        for match in matches[:15]:  # Limit to 15 matches
            comp = match['competition']
            if comp not in by_competition:
                by_competition[comp] = []
            by_competition[comp].append(match)

        for comp, comp_matches in by_competition.items():
            message += f"\n🏆 *{comp}*\n"
            for match in comp_matches:
                time_str = match['start_time']
                home = match['home_team']
                away = match['away_team']
                message += f"⏰ {time_str} | {home} vs {away}\n"

        message += """

━━━━━━━━━━━━━━━━━━━━━

💰 *BET NOW & WIN BIG!* 💰

Ready to place your bets? Use our trusted partners:

"""
        for name, link in AFFILIATE_LINKS.items():
            message += f"👉 {name}: {link}\n"

        message += """
━━━━━━━━━━━━━━━━━━━━━

🔔 Stay tuned for live updates!
📲 Enable notifications!

#Football #DailyMatches #Betting #Predictions
"""
        return message.strip()

    @staticmethod
    def generate_facebook_teaser(match: Dict, post_type: str = "upcoming") -> str:
        """Generate Facebook teaser post (NO affiliate links!)"""

        home = match['home_team']
        away = match['away_team']
        competition = match['competition']
        start_time = match['start_time']
        home_score = match.get('home_score', '-')
        away_score = match.get('away_score', '-')

        if post_type == "upcoming":
            return f"""🔥 BIG MATCH ALERT! 🔥

⚽ {home} 🆚 {away}

🏆 {competition}
⏰ Kick-off: {start_time}

Want our EXCLUSIVE prediction and live score updates?

👇 Join our Telegram for FREE insights! 👇
📲 {TELEGRAM_CHANNEL_LINK}

Don't miss out on this epic clash!

#Football #MatchDay #Prediction #LiveScore"""

        elif post_type == "live":
            return f"""⚡ LIVE NOW! ⚡

⚽ {home} {home_score} - {away_score} {away}

🏆 {competition}

Get INSTANT live updates and exclusive betting tips!

👇 Join our Telegram NOW! 👇
📲 {TELEGRAM_CHANNEL_LINK}

#Football #LiveScore #MatchDay"""

        else:  # finished
            return f"""✅ FULL TIME ✅

⚽ {home} {home_score} - {away_score} {away}

🏆 {competition}

See our next predictions and exclusive analysis!

👇 Join our Telegram for MORE! 👇
📲 {TELEGRAM_CHANNEL_LINK}

#Football #MatchResult #Prediction"""

    @staticmethod
    def generate_facebook_daily_teaser(matches: List[Dict]) -> str:
        """Generate daily summary teaser for Facebook"""

        today_gmt = datetime.now(GMT).strftime("%A, %B %d")
        major_matches = [m for m in matches if m.get('is_major')][:3]

        match_preview = ""
        for match in major_matches:
            home = match['home_team']
            away = match['away_team']
            match_preview += f"⚽ {home} vs {away}\n"

        if not match_preview:
            for match in matches[:3]:
                home = match['home_team']
                away = match['away_team']
                match_preview += f"⚽ {home} vs {away}\n"

        return f"""🔥 TODAY'S HOT MATCHES! 🔥
📅 {today_gmt}

{match_preview}
...and many more!

Want our EXCLUSIVE predictions for ALL matches?

👇 Join our Telegram for FREE tips! 👇
📲 {TELEGRAM_CHANNEL_LINK}

Get live scores, predictions & insider tips!

#Football #MatchDay #Predictions #FreeTips"""


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

    def send_photo(self, photo_url: str, caption: str) -> bool:
        """Send photo with caption to Telegram channel"""
        url = f"{self.base_url}/sendPhoto"

        payload = {
            "chat_id": self.chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get('ok', False)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram photo: {e}")
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
                logger.info(f"✅ Facebook post created successfully: {result['id']}")
                return True
            else:
                logger.error(f"Facebook API error: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post to Facebook: {e}")
            return False

    def post_link(self, message: str, link: str) -> bool:
        """Post message with link to Facebook Page"""
        url = f"{self.base_url}/feed"

        payload = {
            "message": message,
            "link": link,
            "access_token": self.access_token
        }

        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            if 'id' in result:
                logger.info(f"✅ Facebook link post created: {result['id']}")
                return True
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post link to Facebook: {e}")
            return False


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class FootballBot:
    """Main orchestrator for the football automation bot"""

    def __init__(self):
        self.api = FootballAPI(config.rapidapi_key)
        self.telegram = TelegramClient(config.telegram_bot_token, config.telegram_chat_id)
        self.facebook = FacebookClient(config.facebook_page_id, config.facebook_page_access_token)
        self.content = ContentGenerator()
        self.posted_matches = set()  # Track posted matches to avoid duplicates

    def run(self):
        """Main execution flow"""
        logger.info("🚀 Starting Football Bot execution...")

        # Get current time in GMT
        now_gmt = datetime.now(GMT)
        today = now_gmt.strftime("%Y%m%d")
        current_hour = now_gmt.hour

        logger.info(f"📅 Current time (GMT): {now_gmt.strftime('%Y-%m-%d %H:%M:%S')}")

        # Fetch today's matches
        matches = self.api.get_matches_by_date(today)
        if not matches:
            logger.warning("No matches found for today")
            return

        logger.info(f"📊 Found {len(matches)} matches for today")

        # Filter major matches
        major_matches = [m for m in matches if m.get('is_major')]
        logger.info(f"⭐ Found {len(major_matches)} major matches")

        # Fetch live matches
        live_matches = self.api.get_live_matches()
        live_count = len(live_matches) if live_matches else 0
        logger.info(f"🔴 Found {live_count} live matches")

        # === POSTING LOGIC ===

        # 1. Morning summary (8 AM GMT)
        if current_hour == 8:
            summary_matches = major_matches if major_matches else matches[:10]
            self._post_daily_summary(summary_matches)

        # 2. Post upcoming major matches (1-2 hours before kickoff)
        upcoming = self._get_upcoming_matches(major_matches, now_gmt)
        for match in upcoming[:3]:  # Limit to 3 posts per hour
            self._post_upcoming_match(match)
            time.sleep(5)  # Rate limiting

        # 3. Post live score updates
        if live_matches:
            major_live = [m for m in live_matches if m.get('is_major')]
            for match in major_live[:2]:
                self._post_live_score(match)
                time.sleep(5)

        # 4. Post finished match results
        finished = [m for m in matches if m['status'] == 'Finished' and m.get('is_major')]
        for match in finished[:2]:
            self._post_finished_match(match)
            time.sleep(5)

        logger.info("✅ Football Bot execution completed!")

    def _get_upcoming_matches(self, matches: List[Dict], now: datetime) -> List[Dict]:
        """Get matches starting in 1-2 hours"""
        upcoming = []

        for match in matches:
            if match['status'] != 'Upcoming':
                continue

            try:
                # Parse the raw start time
                start_str = str(match['start_time_raw'])[:14]
                if len(start_str) >= 12:
                    start_time = datetime.strptime(start_str, "%Y%m%d%H%M%S")
                    start_time = GMT.localize(start_time)

                    # Check if match is 1-2 hours away
                    time_until = (start_time - now).total_seconds() / 3600
                    if 0.5 <= time_until <= 2:
                        upcoming.append(match)
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse time for match: {e}")
                continue

        return upcoming

    def _post_daily_summary(self, matches: List[Dict]):
        """Post daily summary to both platforms"""
        if not matches:
            return

        # Telegram - Full summary with affiliates
        telegram_msg = self.content.generate_telegram_daily_summary(matches)
        self.telegram.send_message(telegram_msg)

        # Facebook - Teaser only
        facebook_msg = self.content.generate_facebook_daily_teaser(matches)
        self.facebook.post_message(facebook_msg)

        logger.info("📝 Posted daily summary to both platforms")

    def _post_upcoming_match(self, match: Dict):
        """Post upcoming match alert to both platforms"""
        home_team = match['home_team']
        away_team = match['away_team']
        match_id = match.get('id', f"{home_team}-{away_team}")

        if match_id in self.posted_matches:
            logger.debug(f"Skipping already posted match: {match_id}")
            return

        # Telegram - Full details with predictions and affiliates
        telegram_msg = self.content.generate_telegram_upcoming_match(match)
        if self.telegram.send_message(telegram_msg):
            self.posted_matches.add(match_id)

        # Facebook - Teaser only
        facebook_msg = self.content.generate_facebook_teaser(match, "upcoming")
        self.facebook.post_message(facebook_msg)

        logger.info(f"📢 Posted upcoming match: {home_team} vs {away_team}")

    def _post_live_score(self, match: Dict):
        """Post live score update"""
        home_team = match['home_team']
        away_team = match['away_team']
        home_score = match['home_score']
        away_score = match['away_score']

        # Telegram only for live scores (high frequency)
        telegram_msg = self.content.generate_telegram_live_score(match)
        self.telegram.send_message(telegram_msg)

        logger.info(f"🔴 Posted live score: {home_team} {home_score}-{away_score} {away_team}")

    def _post_finished_match(self, match: Dict):
        """Post finished match result"""
        home_team = match['home_team']
        away_team = match['away_team']
        home_score = match['home_score']
        away_score = match['away_score']

        match_id = "finished-" + str(match.get('id', f"{home_team}-{away_team}"))

        if match_id in self.posted_matches:
            return

        # Telegram - Full result with affiliates
        telegram_msg = self.content.generate_telegram_live_score(match)
        if self.telegram.send_message(telegram_msg):
            self.posted_matches.add(match_id)

        # Facebook - Result teaser
        facebook_msg = self.content.generate_facebook_teaser(match, "finished")
        self.facebook.post_message(facebook_msg)

        logger.info(f"✅ Posted finished match: {home_team} {home_score}-{away_score} {away_team}")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("⚽ FOOTBALL AUTOMATION BOT ⚽")
    logger.info("=" * 60)

    # Validate configuration
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
    logger.info("✅ Bot execution completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
