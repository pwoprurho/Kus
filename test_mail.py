import os
from dotenv import load_dotenv
from services.mailer import send_verification_email, send_notification_email

# Load env
load_dotenv(override=True)

def test_mail():
    print("--- Testing Zoho Mail Integration ---")
    
    user = os.getenv("MAIL_USERNAME")
    pwd = os.getenv("MAIL_PASSWORD")
    
    print(f"Username: {user}")
    print(f"Password: {'*' * len(pwd) if pwd else 'None'}")
    
    if not user or "kusmus.ai" in user and "password" in pwd:
        print("⚠️  WARNING: It looks like you are using placeholder credentials.")
        print("   Please update MAIL_USERNAME and MAIL_PASSWORD in .env with real Zoho credentials.")
        return

    recipient = input("Enter recipient email for test: ")
    if not recipient:
        print("Test cancelled.")
        return

    print(f"Sending Verification email to {recipient}...")
    success = send_verification_email(recipient, "https://kusmus.ai/verify/test-link")
    
    if success:
        print("✅ Verification Email sent successfully!")
    else:
        print("❌ Verification Email failed.")

    print(f"Sending Notification email to {recipient}...")
    # This is async, so it returns None immediately usually, but let's just call it
    send_notification_email(recipient, "Test Notification", "This is a test of the async notification system.", "https://kusmus.ai", "Click Me")
    print("✅ Notification Email queued (Async). Check inbox.")

if __name__ == "__main__":
    test_mail()