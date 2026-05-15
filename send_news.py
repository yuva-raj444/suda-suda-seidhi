import base64
import os
import smtplib
import subprocess
import tempfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser

# The Hindu RSS feeds
INTERNATIONAL_RSS = "https://www.thehindu.com/news/international/feeder/default.rss"
NATIONAL_RSS = "https://www.thehindu.com/news/national/feeder/default.rss"

# Email config
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

# TTS config (Microsoft Edge TTS)
EDGE_TTS_VOICE = "en-US-EmmaMultilingualNeural"
AUDIO_FILENAME = "daily_news.mp3"


def _safe_text(s: str) -> str:
    return (s or "").strip()


def build_news_items():
    """Return a dict with both HTML and a plain-text script for TTS."""
    greeting_before = "Good morning. Here is your news briefing for today."
    greeting_after = "That’s all for now. Have a great day."

    # HTML header greeting
    html = ""
    html += '<p style="color:#666; text-align:center; margin-bottom:20px; font-size:16px;">Good morning! Here is your news briefing for today.</p>'

    # TTS script greeting
    script_lines = [greeting_before, ""]

    def add_section(title: str, entries, limit: int):
        nonlocal html
        html += f'<h2 style="color:#0056b3; border-bottom:1px solid #e0e0e0;">{title}</h2>'
        script_lines.append(title)

        for entry in (entries or [])[:limit]:
            etitle = _safe_text(getattr(entry, "title", ""))
            desc = _safe_text(getattr(entry, "description", "No description available."))
            link = _safe_text(getattr(entry, "link", ""))

            # HTML card
            html += f"""
            <div style=\"margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #fafafa;\">
                <h3 style=\"margin-top: 0; margin-bottom: 10px; font-size: 18px;\">
                    <a href=\"{link}\" style=\"text-decoration: none; color: #0056b3;\">{etitle}</a>
                </h3>
                <p style=\"margin: 0; color: #555; line-height: 1.5; font-size: 14px;\">{desc}</p>
            </div>
            """

            # TTS lines (no links)
            script_lines.append(etitle)
            if desc:
                script_lines.append(desc)
            script_lines.append("")

        script_lines.append("")

    intl_feed = feedparser.parse(INTERNATIONAL_RSS)
    add_section("International", getattr(intl_feed, "entries", []), 5)

    nat_feed = feedparser.parse(NATIONAL_RSS)
    add_section("National", getattr(nat_feed, "entries", []), 15)

    # closing greetings
    html += '<p style="color:#666; text-align:center; margin-top:25px; font-size:14px;">That’s all for now — have a great day.</p>'
    script_lines.append(greeting_after)

    return {
        "html": html,
        "script": "\n".join(script_lines).strip() + "\n",
    }


def synthesize_mp3_with_edge_tts(text: str) -> bytes:
    """Generate MP3 audio bytes using the `edge-tts` CLI.

    Notes:
    - This depends on GitHub Actions having the `edge-tts` package installed.
    - Voice requested: Microsoft Emma Multilingual Online (Natural) (en-US Emma Multilingual Neural).
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, AUDIO_FILENAME)

        # Use CLI to avoid extra Python deps / event loop handling.
        # Command: edge-tts --voice <voice> --text <text> --write-media <file>
        cmd = [
            "edge-tts",
            "--voice",
            EDGE_TTS_VOICE,
            "--text",
            text,
            "--write-media",
            out_path,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as e:
            raise RuntimeError(
                "edge-tts CLI not found. Ensure `edge-tts` is installed in the workflow (requirements.txt)."
            ) from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"edge-tts failed (exit {e.returncode}). stderr: {e.stderr.strip()}"
            ) from e

        with open(out_path, "rb") as f:
            return f.read()


def send_email(news_html: str, audio_mp3_bytes: bytes | None = None):
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("Email credentials are not set properly.")
        return

    subject = "Your Daily International & National News Headlines"

    body = f"""
    <html>
        <body style=\"font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; margin: 0;\">
            <div style=\"max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);\">
                <h2 style=\"text-align: center; color: #333; border-bottom: 2px solid #0056b3; padding-bottom: 15px; margin-top: 0;\">
                    📰 Daily News Briefing
                </h2>
                {news_html}
                <p style=\"text-align: center; color: #999; font-size: 12px; margin-top: 40px; border-top: 1px solid #eee; padding-top: 20px;\">
                    Sent automatically via GitHub Actions
                </p>
            </div>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject

    # HTML part
    msg.attach(MIMEText(body, "html"))

    # Attach MP3 (optional)
    if audio_mp3_bytes:
        attachment = MIMEApplication(audio_mp3_bytes, _subtype="mpeg")
        attachment.add_header("Content-Disposition", "attachment", filename=AUDIO_FILENAME)
        msg.attach(attachment)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
    news = build_news_items()

    audio: bytes | None = None
    try:
        audio = synthesize_mp3_with_edge_tts(news["script"])
    except RuntimeError as e:
        # Avoid failing the whole workflow if TTS isn't available for any reason.
        print(f"TTS generation failed; sending email without audio. Reason: {e}")

    send_email(news["html"], audio)
