from abc import ABC, abstractmethod
from twilio.rest import Client
import os

class NotificationProvider(ABC):
    @abstractmethod
    def send_alert(self, phone_number: str, message: str) -> bool:
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
