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
    html_content = ""
    
    for entry in feed.entries[:limit]:
        title = entry.title
        link = entry.link
        # Grab the short description, default to empty if the feed doesn't have one
        description = getattr(entry, 'description', 'No description available.')
        
        # Build a styled HTML "card" for each news item
        html_content += f"""
        <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #fafafa;">
            <h3 style="margin-top: 0; margin-bottom: 10px; font-size: 18px;">
                <a href="{link}" style="text-decoration: none; color: #0056b3;">{title}</a>
            </h3>
            <p style="margin: 0; color: #555; line-height: 1.5; font-size: 14px;">
                {description}
            </p>
        </div>
        """
    return html_content

def send_email(news_html):
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("Email credentials are not set properly.")
        return

    subject = "Your Daily Top 20 News Headlines"
    
    # Wrap all the news items in a nice main container
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; margin: 0;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
                <h2 style="text-align: center; color: #333; border-bottom: 2px solid #0056b3; padding-bottom: 15px; margin-top: 0;">
                    📰 Daily News Briefing
                </h2>
                <p style="color: #666; text-align: center; margin-bottom: 30px; font-size: 16px;">
                    Here are your top headlines for today:
                </p>
                
                {news_html}
                
                <p style="text-align: center; color: #999; font-size: 12px; margin-top: 40px; border-top: 1px solid #eee; padding-top: 20px;">
                    Sent automatically via GitHub Actions
                </p>
            </div>
        </body>
    </html>
    """

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
    news_html = get_top_news()
    send_email(news_html)
