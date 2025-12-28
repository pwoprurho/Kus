import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ZOHO CONFIGURATION
SMTP_SERVER = "smtp.zoho.com"
SMTP_PORT = 465 # SSL Port
SENDER_EMAIL = os.getenv("MAIL_USERNAME", "notifications@kusmus.ai")
SENDER_PASSWORD = os.getenv("MAIL_PASSWORD") # App-Specific Password

def send_verification_email(recipient_email, verification_link):
    """
    Sends a secure HTML verification email via Zoho SMTP.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = "ACTION REQUIRED: Verify Kusmus Forensic Audit"
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email

        # HTML Template integration
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-left: 4px solid #0072ff;">
              <h2 style="color: #333;">Confirm Audit Request</h2>
              <p style="color: #666;">A Phase 1 Forensic Audit was requested for this address.</p>
              <p style="color: #666;">To release the encrypted report, please verify your identity below:</p>
              <br>
              <a href="{verification_link}" style="background-color: #0072ff; color: white; padding: 12px 25px; text-decoration: none; border-radius: 4px; font-weight: bold;">VERIFY IDENTITY</a>
              <br><br>
              <p style="font-size: 12px; color: #999;">Reference ID: {verification_link.split('/')[-1]}</p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, "html"))

        # SSL Connection
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            
        print(f"[MAILER] Verification sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"[MAILER ERROR] Failed to send email: {e}")
        return False