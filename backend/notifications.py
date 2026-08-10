from abc import ABC, abstractmethod
from twilio.rest import Client
import os
import logging
import requests

logger = logging.getLogger(__name__)

class NotificationProvider(ABC):
    @abstractmethod
    def send_alert(self, destination: str, message: str) -> bool:
        pass

class TwilioSandboxProvider(NotificationProvider):
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
        
        if not self.account_sid or not self.auth_token or not self.from_number:
            print("[Twilio Provider] ERROR: Missing Twilio credentials in environment.")
            self.client = None
        else:
            try:
                self.client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                print(f"[Twilio Provider] ERROR initializing client: {e}")
                self.client = None
            
    def send_alert(self, phone_number: str, message: str) -> bool:
        if not self.client:
            print("[Twilio Provider] Cannot send alert: Provider not configured properly.")
            return False
            
        try:
            print(f"[Twilio Provider] Sending WhatsApp to {phone_number}: {message.encode('ascii', 'ignore').decode()}")
        except Exception:
            pass
            
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )
            if msg.sid:
                print(f"[Twilio Provider] Message successfully sent! SID: {msg.sid}")
                return True
            else:
                print("[Twilio Provider] Message creation did not return a valid SID.")
                return False
        except Exception as e:
            print(f"[Twilio Provider] Failed to send Twilio alert: {e}")
            return False

class TelegramProvider(NotificationProvider):
    """Sends notifications via the Telegram Bot API (HTTPS)."""

    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.default_chat_id = os.environ.get('TELEGRAM_DEFAULT_CHAT_ID')
        
        if not self.bot_token:
            logger.warning("[Telegram Provider] TELEGRAM_BOT_TOKEN is not configured.")

    def send_alert(self, chat_id: str, message: str) -> bool:
        if not self.bot_token:
            logger.warning("[Telegram Provider] Cannot send alert: TELEGRAM_BOT_TOKEN not configured.")
            return False
        
        destination = chat_id or self.default_chat_id
        if not destination:
            logger.warning("[Telegram Provider] Cannot send alert: No chat_id provided and no default configured.")
            return False
        
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": destination,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            
            result = resp.json()
            if result.get("ok"):
                logger.info(f"[Telegram Provider] Message sent to chat {destination}.")
                return True
            else:
                error_desc = result.get("description", "Unknown Telegram API error")
                logger.warning(f"[Telegram Provider] Telegram API returned ok=false: {error_desc}")
                return False
        except requests.exceptions.Timeout:
            logger.warning("[Telegram Provider] Request timed out.")
            return False
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[Telegram Provider] HTTP error: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"[Telegram Provider] Request failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"[Telegram Provider] Unexpected error: {e}")
            return False


SUPPORTED_CHANNELS = {"whatsapp", "telegram"}

def get_notifier(channel: str) -> NotificationProvider:
    """Factory function returning the appropriate NotificationProvider for the given channel."""
    if channel == "whatsapp":
        return TwilioSandboxProvider()
    elif channel == "telegram":
        return TelegramProvider()
    else:
        raise ValueError(f"Unsupported notification channel: '{channel}'. Supported: {SUPPORTED_CHANNELS}")

def resolve_alert_destination(db, alert) -> str | None:
    """
    Resolves the current active destination for an alert threshold.
    
    Precedence & Disconnect Rules for Telegram:
    1. CONNECTED: If NotificationPreference exists for alert.user_id and pref.telegram_chat_id is set -> Return pref.telegram_chat_id.
    2. DISCONNECTED: If NotificationPreference exists for alert.user_id but pref.telegram_chat_id is None -> Return None (MUST NOT fall back to historical alert.telegram_chat_id).
    3. LEGACY RECORD: If no NotificationPreference record exists for alert.user_id (or alert.user_id is None) -> Fall back to alert.telegram_chat_id.
    """
    channel = getattr(alert, "notification_channel", "whatsapp") or "whatsapp"
    if channel == "telegram":
        user_id = getattr(alert, "user_id", None)
        if user_id is not None:
            from backend.models import NotificationPreference
            pref = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).first()
            if pref:
                # Explicit preference record exists: return linked chat_id (or None if disconnected)
                return pref.telegram_chat_id
        # Fallback for legacy alerts where no NotificationPreference record exists or user_id is None
        return getattr(alert, "telegram_chat_id", None)
    else:
        return getattr(alert, "phone_number", None)



def build_alert_confirmation_message(
    product_title: str,
    platform: str,
    threshold_price: float,
    current_price: float = None,
    channel: str = "telegram"
) -> str:
    """Builds a centralized alert confirmation message for Telegram or WhatsApp."""
    platform_name = (platform or "Retailer").capitalize()
    if current_price is not None and current_price > 0:
        price_str = f"₹{current_price:,.2f}"
    else:
        price_str = "Not available yet"

    if channel == "telegram":
        import html
        safe_title = html.escape(product_title or "Product")
        safe_platform = html.escape(platform_name)
        return (
            "🔔 <b>Smart Price Tracker</b>\n\n"
            "<b>Alert Created Successfully</b>\n\n"
            f"📦 <b>Product:</b> {safe_title}\n"
            f"🏪 <b>Platform:</b> {safe_platform}\n"
            f"🎯 <b>Target Price:</b> ₹{threshold_price:,.2f}\n\n"
            f"<b>Current Price:</b> {price_str}\n"
            "<b>Status:</b> ✅ Active\n\n"
            "You will receive a Telegram notification when the product price reaches or falls below your target price."
        )
    else:
        return (
            "🔔 *Smart Price Tracker*\n\n"
            "*Alert Created Successfully*\n\n"
            f"📦 *Product:* {product_title}\n"
            f"🏪 *Platform:* {platform_name}\n"
            f"🎯 *Target Price:* ₹{threshold_price:,.2f}\n\n"
            f"*Current Price:* {price_str}\n"
            "*Status:* ✅ Active\n\n"
            "You will receive a WhatsApp notification when the product price reaches or falls below your target price."
        )

def build_direct_test_notification_message(channel: str = "telegram", custom_message: str = None) -> str:
    """Builds default or custom test notification message."""
    if custom_message and str(custom_message).strip():
        return str(custom_message).strip()

    if channel == "telegram":
        return (
            "🔔 <b>Smart Price Tracker</b>\n\n"
            "This is a test notification.\n\n"
            "Telegram notifications are configured correctly."
        )
    else:
        return (
            "🔔 *Smart Price Tracker*\n\n"
            "This is a test notification.\n\n"
            "WhatsApp notifications are configured correctly."
        )


