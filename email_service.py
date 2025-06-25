import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@painradar.ai")
        self.enabled = bool(self.smtp_username and self.smtp_password)
    
    def send_email(self, to_email, subject, html_content, text_content=None):
        """Send an email with HTML and optional plain text content"""
        if not self.enabled:
            print(f"Email sending disabled. Would have sent to {to_email}: {subject}")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            
            # Add plain text version
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            else:
                # Create plain text from HTML (simplified)
                text = html_content.replace("<br>", "\n").replace("<p>", "").replace("</p>", "\n\n")
                msg.attach(MIMEText(text, "plain"))
            
            # Add HTML version
            msg.attach(MIMEText(html_content, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())
                
            print(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            print(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def send_team_invitation(self, to_email, team_name, inviter_name, invitation_link):
        """Send a team invitation email"""
        subject = f"You've been invited to join {team_name} on PainRadar"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #00fff7; text-align: center;">Team Invitation</h2>
                <p>Hello,</p>
                <p><strong>{inviter_name}</strong> has invited you to join the team <strong>{team_name}</strong> on PainRadar.</p>
                <p>PainRadar helps teams identify customer pain points and market opportunities.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_link}" style="background: #00fff7; color: #001f2f; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-weight: bold;">Accept Invitation</a>
                </div>
                <p>If you don't have a PainRadar account yet, you'll be able to create one when accepting the invitation.</p>
                <p>If you have any questions, please contact {inviter_name}.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #777; text-align: center;">PainRadar - See the Trouble, Burst the Bubble</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_content_shared_notification(self, to_email, sharer_name, team_name, content_type, content_title, content_link):
        """Send a notification when content is shared with a team"""
        subject = f"{sharer_name} shared {content_type} with {team_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #00fff7; text-align: center;">New Shared Content</h2>
                <p>Hello,</p>
                <p><strong>{sharer_name}</strong> has shared {content_type} with your team <strong>{team_name}</strong>.</p>
                <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #00fff7; margin: 20px 0;">
                    <h3 style="margin-top: 0;">{content_title}</h3>
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{content_link}" style="background: #00fff7; color: #001f2f; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-weight: bold;">View Content</a>
                </div>
                <p>Log in to PainRadar to view the shared content and collaborate with your team.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #777; text-align: center;">PainRadar - See the Trouble, Burst the Bubble</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)