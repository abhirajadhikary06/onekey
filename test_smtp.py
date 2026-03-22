import asyncio
import os
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

# We need to set the PYTHONPATH so it can find the backend module
import sys
sys.path.append(os.getcwd())

from backend.mailer import send_api_alert_email

async def test_email():
    print("--- Onekey SMTP Test ---")
    recipient = os.getenv("MAIL_USERNAME")
    
    if not recipient:
        print("Error: MAIL_USERNAME not found in .env!")
        return

    print(f"Sending test alert to: {recipient}...")
    
    # We'll simulate a 'Success' alert for testing
    status_code = 200
    provider = "Manual-Test-System"
    
    success = await send_api_alert_email(
        email=recipient,
        provider=provider,
        status_code=status_code,
        response_text="This is a manual test of the Onekey SMTP integration."
    )
    
    if success:
        print("\n✅ SUCCESS! Check your email inbox (and spam folder).")
    else:
        print("\n❌ FAILED. Check your .env credentials and terminal logs for errors.")

if __name__ == "__main__":
    asyncio.run(test_email())
