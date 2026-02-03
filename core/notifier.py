"""
Notification system - sends updates via Telegram.
Integrates with OpenClaw's message tool.
"""

import json
import os
import subprocess
from typing import Optional


def send_telegram_update(message: str, group_id: Optional[str] = None) -> bool:
    """
    Send update to Telegram group via OpenClaw.
    
    If running outside OpenClaw, falls back to direct API call.
    """
    # Try OpenClaw CLI first
    try:
        result = subprocess.run(
            [
                "openclaw", "message", "send",
                "--channel", "telegram",
                "--target", group_id or os.getenv("TELEGRAM_GROUP_ID", ""),
                "--message", message,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"OpenClaw message failed: {result.stderr}")
            
    except FileNotFoundError:
        print("OpenClaw CLI not found, trying direct API...")
    except Exception as e:
        print(f"Error sending via OpenClaw: {e}")
    
    # Fallback to direct Telegram API
    return _send_telegram_direct(message, group_id)


def _send_telegram_direct(message: str, chat_id: Optional[str] = None) -> bool:
    """Send directly via Telegram Bot API."""
    import httpx
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_GROUP_ID")
    
    if not bot_token or not chat_id:
        print("Telegram credentials not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=30,
        )
        response.raise_for_status()
        return True
        
    except Exception as e:
        print(f"Direct Telegram send failed: {e}")
        return False


def send_daily_summary(explored_today: list, stats: dict) -> bool:
    """Send end-of-day summary."""
    if not explored_today:
        return True  # Nothing to report
    
    message = "📊 *Home Finder Daily Summary*\n\n"
    
    for area in explored_today:
        message += f"• {area['name']}: {area['score']}/100\n"
    
    message += f"\n*Progress:* {stats['explored']}/{stats['total']} areas explored"
    
    return send_telegram_update(message)
