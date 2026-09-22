"""
Email Integration for Leasing Agent
Handles automated email responses and follow-ups using SMTP
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


class EmailClient:
    """Client for sending automated emails"""
    
    def __init__(self):
        self.enabled = all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD])
        if self.enabled:
            logger.info("Email client initialized")
        else:
            logger.warning("Email credentials not configured, email integration disabled")
    
    def send_email(self, to_email: str, subject: str, body: str, 
                  html_body: Optional[str] = None) -> Dict[str, Any]:
        """Send an email"""
        if not self.enabled:
            return {"success": False, "error": "Email client not configured"}
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = SMTP_FROM
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML version if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return {"success": True, "message": "Email sent successfully"}
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}
    
    def send_tour_confirmation(self, prospect_email: str, prospect_name: str, 
                             property_name: str, address: str, tour_time: datetime) -> Dict[str, Any]:
        """Send tour confirmation email"""
        subject = f"Tour Confirmation: {property_name}"
        
        body = f"""
Dear {prospect_name},

Your property tour has been confirmed!

Property: {property_name}
Address: {address}
Date & Time: {tour_time.strftime('%A, %B %d, %Y at %I:%M %p')}

Please remember to bring:
- Valid ID
- Proof of income for qualification
- Any questions you have about the property

If you need to reschedule, please reply to this email or call our office.

We look forward to meeting you!

Best regards,
AI Leasing Team
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #0f766e; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .details {{ background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #0f766e; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Tour Confirmed! 🏠</h1>
        </div>
        <div class="content">
            <p>Dear {prospect_name},</p>
            <p>Your property tour has been confirmed! We're excited to show you your potential new home.</p>
            
            <div class="details">
                <h3>Tour Details</h3>
                <p><strong>Property:</strong> {property_name}</p>
                <p><strong>Address:</strong> {address}</p>
                <p><strong>Date & Time:</strong> {tour_time.strftime('%A, %B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <h3>What to Bring</h3>
            <ul>
                <li>Valid ID</li>
                <li>Proof of income for qualification</li>
                <li>Any questions about the property</li>
            </ul>
            
            <p>If you need to reschedule, please reply to this email or call our office.</p>
            
            <p>We look forward to meeting you!</p>
            
            <p>Best regards,<br>AI Leasing Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply directly to this email.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return self.send_email(prospect_email, subject, body, html_body)
    
    def send_ai_response(self, prospect_email: str, prospect_name: str, 
                       ai_message: str, conversation_context: str) -> Dict[str, Any]:
        """Send AI response via email"""
        subject = "Response from AI Leasing Assistant"
        
        body = f"""
Dear {prospect_name},

Thank you for your inquiry about our properties.

{ai_message}

{conversation_context}

If you have any other questions or would like to speak with a human agent, please reply to this email or call our office.

Best regards,
AI Leasing Team
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #0f766e; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .message {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Leasing Assistant 🤖</h1>
        </div>
        <div class="content">
            <p>Dear {prospect_name},</p>
            <p>Thank you for your inquiry about our properties.</p>
            
            <div class="message">
                <h3>Response</h3>
                <p>{ai_message}</p>
            </div>
            
            <p>{conversation_context}</p>
            
            <p>If you have any other questions or would like to speak with a human agent, please reply to this email or call our office.</p>
            
            <p>Best regards,<br>AI Leasing Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply directly to this email.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return self.send_email(prospect_email, subject, body, html_body)
    
    def send_human_handoff_notification(self, staff_email: str, prospect_name: str, 
                                       prospect_email: str, reason: str, 
                                       conversation_summary: str) -> Dict[str, Any]:
        """Send notification to staff about human handoff"""
        subject = f"Human Handoff Required: {prospect_name}"
        
        body = f"""
A prospect has requested human assistance.

Prospect: {prospect_name} ({prospect_email})
Reason: {reason}

Conversation Summary:
{conversation_summary}

Please follow up with this prospect as soon as possible.
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .alert {{ background-color: #fee2e2; padding: 15px; margin: 10px 0; border-left: 4px solid #dc2626; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Human Handoff Required</h1>
        </div>
        <div class="content">
            <div class="alert">
                <h3>Potential Customer Needs Assistance</h3>
                <p><strong>Prospect:</strong> {prospect_name} ({prospect_email})</p>
                <p><strong>Reason:</strong> {reason}</p>
            </div>
            
            <h3>Conversation Summary</h3>
            <p>{conversation_summary}</p>
            
            <p>Please follow up with this prospect as soon as possible.</p>
        </div>
        <div class="footer">
            <p>This is an automated notification from the AI Leasing System.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return self.send_email(staff_email, subject, body, html_body)


# Global email client instance
email_client = EmailClient()


def send_tour_confirmation_email(prospect_email: str, prospect_name: str, 
                                property_name: str, address: str, tour_time: datetime) -> Dict[str, Any]:
    """Send tour confirmation email"""
    return email_client.send_tour_confirmation(prospect_email, prospect_name, property_name, address, tour_time)


def send_ai_response_email(prospect_email: str, prospect_name: str, 
                          ai_message: str, conversation_context: str) -> Dict[str, Any]:
    """Send AI response via email"""
    return email_client.send_ai_response(prospect_email, prospect_name, ai_message, conversation_context)


def send_handoff_notification(staff_email: str, prospect_name: str, prospect_email: str, 
                            reason: str, conversation_summary: str) -> Dict[str, Any]:
    """Send human handoff notification to staff"""
    return email_client.send_human_handoff_notification(staff_email, prospect_name, prospect_email, reason, conversation_summary)