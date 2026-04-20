import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

RSS_FEED_URL = "http://feeds.bbci.co.uk/news/rss.xml"
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

def get_top_news(limit=20):
    feed = feedparser.parse(RSS_FEED_URL)
    headlines = []
    for entry in feed.entries[:limit]:
        headlines.append(f'<li><a href="{entry.link}">{entry.title}</a></li>')
    return headlines

def send_email(headlines):
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("Email credentials are not set properly.")
        return

    subject = "Your Daily Top 20 News Headlines"
    body = f"<h3>Here are your top news headlines for today:</h3><ul>{''.join(headlines)}</ul>"

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    headlines = get_top_news()
    send_email(headlines)