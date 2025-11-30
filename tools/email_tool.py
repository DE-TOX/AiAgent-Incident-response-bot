"""
Email Notification Tool - Send incident alerts via email

Supports:
- Gmail SMTP
- SendGrid API (optional)
- Mock mode for testing
"""

import structlog
from typing import Dict, Any, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = structlog.get_logger()


class EmailTool:
    """
    Tool for sending incident notifications via email.
    """

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        mock_mode: bool = False
    ):
        """
        Initialize email tool.

        Args:
            smtp_server: SMTP server address (default: Gmail)
            smtp_port: SMTP port (default: 587 for TLS)
            sender_email: Sender email address
            sender_password: App password (for Gmail) or regular password
            mock_mode: If True, print emails instead of sending
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.mock_mode = mock_mode

        logger.info("email_tool_initialized", mock_mode=mock_mode)

    async def send_incident_notification(
        self,
        recipient: str,
        incident_id: str,
        severity: str,
        title: str,
        summary: Optional[str] = None,
        report_url: Optional[str] = None
    ) -> bool:
        """
        Send incident notification email.

        Args:
            recipient: Recipient email address
            incident_id: Incident identifier
            severity: Incident severity (SEV1-SEV4)
            title: Incident title
            summary: Brief summary (optional)
            report_url: Link to full report (optional)

        Returns:
            Success status
        """
        subject = f"🚨 [{severity}] {title}"

        # Create HTML email body
        html_body = self._create_incident_email_html(
            incident_id, severity, title, summary, report_url
        )

        return await self.send_email(recipient, subject, html_body, is_html=True)

    async def send_postmortem_notification(
        self,
        recipient: str,
        incident_id: str,
        title: str,
        action_items_count: int,
        lessons_count: int,
        postmortem_url: Optional[str] = None
    ) -> bool:
        """
        Send postmortem completion notification.

        Args:
            recipient: Recipient email address
            incident_id: Incident identifier
            title: Incident title
            action_items_count: Number of action items created
            lessons_count: Number of lessons learned
            postmortem_url: Link to postmortem (optional)

        Returns:
            Success status
        """
        subject = f"✅ Postmortem Complete: {incident_id}"

        html_body = self._create_postmortem_email_html(
            incident_id, title, action_items_count, lessons_count, postmortem_url
        )

        return await self.send_email(recipient, subject, html_body, is_html=True)

    async def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> bool:
        """
        Send a generic email.

        Args:
            recipient: Recipient email address
            subject: Email subject
            body: Email body (text or HTML)
            is_html: Whether body is HTML

        Returns:
            Success status
        """
        if self.mock_mode:
            return self._send_mock_email(recipient, subject, body, is_html)

        if not self.sender_email or not self.sender_password:
            logger.error("email_credentials_missing")
            print("\n⚠️  Email credentials not configured. Set SENDER_EMAIL and SENDER_PASSWORD in .env")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject

            # Attach body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info("email_sent", recipient=recipient, subject=subject)
            print(f"\n✅ Email sent to {recipient}")
            print(f"   Subject: {subject}")
            return True

        except Exception as e:
            logger.error("email_send_failed", error=str(e), recipient=recipient)
            print(f"\n❌ Failed to send email: {str(e)}")
            return False

    def _send_mock_email(self, recipient: str, subject: str, body: str, is_html: bool) -> bool:
        """Send mock email (print to console)."""
        print("\n" + "="*80)
        print("  📧 MOCK EMAIL NOTIFICATION")
        print("="*80)
        print(f"  To: {recipient}")
        print(f"  From: {self.sender_email or 'incident-bot@example.com'}")
        print(f"  Subject: {subject}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*80)
        if is_html:
            # Strip HTML tags for console display
            import re
            text_body = re.sub('<[^<]+?>', '', body)
            print(text_body[:500])
        else:
            print(body[:500])
        print("="*80 + "\n")

        logger.info("mock_email_sent", recipient=recipient)
        return True

    def _create_incident_email_html(
        self,
        incident_id: str,
        severity: str,
        title: str,
        summary: Optional[str],
        report_url: Optional[str]
    ) -> str:
        """Create HTML email for incident notification."""

        severity_colors = {
            "SEV1": "#d9534f",  # Red
            "SEV2": "#f0ad4e",  # Orange
            "SEV3": "#5bc0de",  # Blue
            "SEV4": "#5cb85c",  # Green
        }
        color = severity_colors.get(severity, "#777777")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px; }}
        .content {{ background-color: #f9f9f9; padding: 20px; margin-top: 20px; border-radius: 5px; }}
        .footer {{ margin-top: 20px; padding: 10px; text-align: center; color: #777; font-size: 12px; }}
        .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Incident Alert: {severity}</h1>
            <p><strong>{incident_id}</strong></p>
        </div>

        <div class="content">
            <h2>{title}</h2>
            {f'<p>{summary}</p>' if summary else ''}

            <p><strong>Status:</strong> Active - Investigation in progress</p>
            <p><strong>Time Detected:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            {f'<a href="{report_url}" class="button">View Full Report</a>' if report_url else ''}
        </div>

        <div class="footer">
            <p>This is an automated notification from Incident Response Bot</p>
            <p>Powered by AI • Built with Google Gemini</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _create_postmortem_email_html(
        self,
        incident_id: str,
        title: str,
        action_items_count: int,
        lessons_count: int,
        postmortem_url: Optional[str]
    ) -> str:
        """Create HTML email for postmortem notification."""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #5cb85c; color: white; padding: 20px; border-radius: 5px; }}
        .content {{ background-color: #f9f9f9; padding: 20px; margin-top: 20px; border-radius: 5px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat {{ text-align: center; }}
        .stat-number {{ font-size: 32px; font-weight: bold; color: #007bff; }}
        .footer {{ margin-top: 20px; padding: 10px; text-align: center; color: #777; font-size: 12px; }}
        .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Postmortem Complete</h1>
            <p><strong>{incident_id}</strong></p>
        </div>

        <div class="content">
            <h2>{title}</h2>

            <p>The incident postmortem has been completed with AI-powered root cause analysis.</p>

            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{action_items_count}</div>
                    <div>Action Items</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{lessons_count}</div>
                    <div>Lessons Learned</div>
                </div>
            </div>

            <p><strong>Status:</strong> Closed - Postmortem documented</p>
            <p><strong>Completed:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            {f'<a href="{postmortem_url}" class="button">View Postmortem</a>' if postmortem_url else ''}
        </div>

        <div class="footer">
            <p>This is an automated notification from Incident Response Bot</p>
            <p>Powered by AI • Built with Google Gemini</p>
        </div>
    </div>
</body>
</html>
"""
        return html