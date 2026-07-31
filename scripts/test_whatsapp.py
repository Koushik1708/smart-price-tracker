import sys
import os
from dotenv import load_dotenv

# Load env before importing backend logic
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.notifications import TwilioSandboxProvider

def test_whatsapp(target_number):
    provider = TwilioSandboxProvider()
    print("Testing Twilio with SID:", provider.account_sid)
    
    # Ensure format is correct
    if not target_number.startswith("whatsapp:"):
        target_number = f"whatsapp:{target_number}"
        
    success = provider.send_alert(
        target_number, 
        "🚨 *FAKE DISCOUNT DETECTED* 🚨\n\nThis is a live test from your Antigravity Agent!"
    )
    if success:
        print("✅ Message successfully dispatched to Twilio!")
    else:
        print("❌ Failed to dispatch message.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_whatsapp.py <whatsapp_number>")
        print("Example: python test_whatsapp.py whatsapp:+919876543210")
        sys.exit(1)
        
    test_whatsapp(sys.argv[1])
