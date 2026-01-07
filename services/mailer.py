import smtplib
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ZOHO CONFIGURATION
SMTP_SERVER = "smtp.zoho.com"
SMTP_PORT = 465 # SSL Port
SENDER_EMAIL = os.getenv("MAIL_USERNAME", "notifications@kusmus.ai")
SENDER_PASSWORD = os.getenv("MAIL_PASSWORD") # App-Specific Password

def send_email(recipient_email, subject, html_content):
    """
    Generic function to send an HTML email via Zoho SMTP.
    """
    if not SENDER_PASSWORD or "your-app-specific-password" in SENDER_PASSWORD:
        print(f"[MAILER WARNING] Email to {recipient_email} skipped. Credentials not configured.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        
        msg.attach(MIMEText(html_content, "html"))

        # SSL Connection
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            
        print(f"[MAILER] Email '{subject}' sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"[MAILER ERROR] Failed to send email: {e}")
        return False

def send_async_email(recipient_email, subject, html_content):
    """
    Sends an email in a background thread to avoid blocking the main application.
    """
    thread = threading.Thread(target=send_email, args=(recipient_email, subject, html_content))
    thread.daemon = True # Daemon threads exit when the main program exits
    thread.start()

def send_verification_email(recipient_email, verification_link):
    """
    Sends a secure HTML verification email via Zoho SMTP.
    """
    subject = "ACTION REQUIRED: Verify Kusmus Forensic Audit"
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
    return send_email(recipient_email, subject, html_content)

def send_recovery_otp(recipient_email, otp_code):
    """
    Sends a 6-digit recovery OTP via Zoho SMTP.
    """
    subject = "SECURE: Your Recovery Access Code"
    html_content = f"""
    <html>
      <body style="font-family: 'Courier New', monospace; background-color: #111; padding: 20px; color: #ddd;">
        <div style="max-width: 500px; margin: 0 auto; background: #000; border: 1px solid #333; padding: 30px; border-top: 4px solid #00ff88;">
          <h2 style="color: #fff; margin-top: 0;">IDENTITY VERIFICATION</h2>
          <p>A recovery protocol was initiated for this account.</p>
          <p>Use the following secure token to complete authentication:</p>
          <div style="background: #222; color: #00ff88; font-size: 32px; font-weight: bold; text-align: center; padding: 20px; margin: 20px 0; letter-spacing: 5px; border: 1px dashed #00ff88;">
            {otp_code}
          </div>
          <p style="font-size: 12px; color: #666;">If you did not request this code, ignore this message. The code expires in 10 minutes.</p>
          <p style="font-size: 12px; color: #666;">Kusmus AI Security</p>
        </div>
      </body>
    </html>
    """
    return send_async_email(recipient_email, subject, html_content)
def send_notification_email(recipient_email, title, message, action_link=None, action_text="View Details"):
    """
    Sends a generic notification email.
    """
    subject = f"Notification: {title}"
    
    button_html = ""
    if action_link:
        button_html = f"""
        <br>
        <a href="{action_link}" style="background-color: #0072ff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">{action_text}</a>
        <br><br>
        """

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-top: 4px solid #0072ff;">
          <h3 style="color: #333;">{title}</h3>
          <p style="color: #555; font-size: 16px; line-height: 1.5;">{message}</p>
          {button_html}
          <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="font-size: 12px; color: #999;">Kusmus AI Forensic Systems</p>
        </div>
      </body>
    </html>
    """
    send_async_email(recipient_email, subject, html_content)