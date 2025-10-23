import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from datetime import datetime, timedelta
from src.utils.config_loader import settings
from src.utils.logger import setup_logger

logger = setup_logger("alerting")


class AlertManager:
    def __init__(self):
        self.last_alert_time = {}
        self.cooldown_minutes = 5

    def send_alert(self, anomaly: Dict):
        alert_key = f"{anomaly['symbol']}:{anomaly['anomaly_type']}"

        if self._is_in_cooldown(alert_key):
            logger.debug(f"Alert {alert_key} in cooldown period, skipping")
            return

        if anomaly['severity'] in ['critical', 'high']:
            self._send_slack_alert(anomaly)

            if settings.alert_email:
                self._send_email_alert(anomaly)

        self.last_alert_time[alert_key] = datetime.now()

    def _is_in_cooldown(self, alert_key: str) -> bool:
        if alert_key not in self.last_alert_time:
            return False

        time_since_last = datetime.now() - self.last_alert_time[alert_key]
        return time_since_last < timedelta(minutes=self.cooldown_minutes)

    def _send_slack_alert(self, anomaly: Dict):
        if not settings.slack_webhook_url or settings.slack_webhook_url.startswith("https://hooks.slack.com"):
            logger.debug("Slack webhook URL not configured properly")
            return

        try:
            severity_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }

            message = {
                "text": f"{severity_emoji.get(anomaly['severity'], '⚠️')} Market Anomaly Detected",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{severity_emoji.get(anomaly['severity'], '⚠️')} {anomaly['anomaly_type'].replace('_', ' ').title()}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Symbol:*\n{anomaly['symbol']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:*\n{anomaly['severity'].upper()}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Current Value:*\n{anomaly['current_value']:.2f}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Threshold:*\n{anomaly.get('threshold', 'N/A')}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Description:*\n{anomaly['description']}"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Time: {anomaly['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }

            response = requests.post(
                settings.slack_webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )

            if response.status_code == 200:
                logger.info(f"Slack alert sent for {anomaly['symbol']} - {anomaly['anomaly_type']}")
            else:
                logger.error(f"Failed to send Slack alert: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}", exc_info=True)

    def _send_email_alert(self, anomaly: Dict):
        try:
            msg = MIMEMultipart()
            msg['From'] = "market-alerts@system.local"
            msg['To'] = settings.alert_email
            msg['Subject'] = f"[{anomaly['severity'].upper()}] Market Anomaly: {anomaly['symbol']} - {anomaly['anomaly_type']}"

            body = f"""
            Market Anomaly Detected

            Symbol: {anomaly['symbol']}
            Type: {anomaly['anomaly_type'].replace('_', ' ').title()}
            Severity: {anomaly['severity'].upper()}

            Description: {anomaly['description']}

            Current Value: {anomaly['current_value']:.2f}
            Threshold: {anomaly.get('threshold', 'N/A')}

            Timestamp: {anomaly['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

            ---
            This is an automated alert from the Market Data Streaming System
            """

            msg.attach(MIMEText(body, 'plain'))

            logger.info(f"Email alert prepared for {anomaly['symbol']} - {anomaly['anomaly_type']}")

        except Exception as e:
            logger.error(f"Error sending email alert: {e}", exc_info=True)
