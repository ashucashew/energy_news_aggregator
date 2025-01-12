import feedparser
import sqlite3
from datetime import datetime, timedelta
import requests  # For making HTTP requests to Claude API
import pytz  # Import pytz for timezone handling
import anthropic

# Set up your Claude API key
claude_api_key = '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'

# List of RSS feeds
feeds = [
    "https://www.reutersagency.com/feed/?best-topics=energy",
    "https://energynews.us/feed/",
    "https://www.renewableenergyworld.com/feed/",
    "https://www.utilitydive.com/feeds/news/",
    "https://www.powermag.com/feed/"
]

# Connect to SQLite database
conn = sqlite3.connect('energy_news.db')
c = conn.cursor()

# Create table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS articles
             (title TEXT, content TEXT, published DATE, source TEXT)''')

# Parse feeds and store articles from the last 2 days
two_days_ago = datetime.now(pytz.utc) - timedelta(days=2)  # Make it offset-aware

for feed_url in feeds:
    try:
        # Set a user-agent header
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(feed_url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)

        # Parse the feed
        feed = feedparser.parse(response.content)

        # Validate the feed structure
        if not hasattr(feed, 'feed') or 'title' not in feed.feed:
            print(f"Invalid feed structure for URL: {feed_url}")
            continue  # Skip this feed if it's invalid

        source = feed.feed.get('title', 'Unknown Source')  # Use 'Unknown Source' if title is not available

        for entry in feed.entries:
            title = entry.title
            content = entry.summary
            published = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')

            if published > two_days_ago:
                c.execute("INSERT INTO articles VALUES (?, ?, ?, ?)",
                          (title, content, published, source))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching feed from {feed_url}: {e}")
    except Exception as e:
        print(f"An error occurred while processing the feed from {feed_url}: {e}")

conn.commit()

# Fetch all articles from the last 2 days
c.execute("SELECT title, content FROM articles WHERE published > ?", (two_days_ago,))
articles = c.fetchall()

# Prepare the content for Claude
content_for_claude = "\n\n".join([f"Title: {article[0]}\nContent: {article[1]}" for article in articles])

# Initialize the Anthropic client with your API key
client = anthropic.Anthropic(api_key=claude_api_key)

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000,
    temperature=0,
    system="You are a journalist. Keep an eye out for important stories.",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please provide a detailed summary of the main energy news stories from the past 2 days, based on the following articles:\n\n"
                    f"{content_for_claude}"
                }
            ]
        }
    ]
)


# Print the response
print(message.content)

conn.close()





