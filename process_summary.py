import os
import json
from groq import Groq
from apify_client import ApifyClient
import uuid
import time
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set the API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Check if API keys are set
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the .env file")
if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN is not set in the .env file")

# Create the Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

# Create the Apify client
apify_client = ApifyClient(APIFY_API_TOKEN)

def main():
    # Load the summary from the file
    with open("summary.json", "r") as f:
        data = json.load(f)
    prompt = data.get("prompt", "")

    # Generate keywords using Groq API
    keywords = generate_keywords(prompt)

    if keywords:
        print("Extracted Keywords:", keywords)
        # Scrape TikTok data using Apify
        tiktok_data = scrape_tiktok(keywords)
        if tiktok_data:
            # Save the data to CSV
            save_to_csv(tiktok_data, "tiktok_results.csv")
            print("Data saved to tiktok_results.csv")
        else:
            print("No TikTok data found.")
    else:
        print("No keywords extracted.")

def generate_keywords(prompt):
    # Define the LLM prompt
    llm_prompt5 = """
    You are an expert in identifying keywords for influencer discovery through web scraping. Your job is to analyze the provided text and extract unique keywords or phrases that can be effectively used to scrape data from websites.

    Focus on terms that are:
    - Highly relevant to influencer profiles, such as names, niches, platforms, hashtags, or specific identifiers mentioned in the text.
    - Include any mentioned age or age range explicitly as a keyword (e.g., "20-25 years").
    - Unique, avoiding duplicate or similar keywords. For example, if "UK" is already included, exclude phrases like "The UK" or "UK influencers."

    TEXT: {prompt1}

    Output format (JSON): 
    {{
        "keywords": ["keyword1", "keyword2", "keyword3", ...]
    }}

    CRITICAL: Ensure the following:
    1. Include any age or age range exactly as mentioned in the text.
    2. Do not include redundant or overlapping phrases (e.g., exclude geographic locations if occurring multiple times).
    3. The extracted keywords should be concise, highly relevant, and non-redundant.
    4. Prioritize unique and actionable terms suitable for web scraping.
    """

    # Format the prompt
    formatted_prompt = llm_prompt5.format(prompt1=str(prompt))

    # Define the messages for the API call
    messages = [{"role": "user", "content": formatted_prompt}]

    # Call the Groq API
    response = groq_client.chat.completions.create(
        model='llama3-8b-8192',
        response_format={"type": "json_object"},
        messages=messages
    )

    # Extract the keywords from the response
    response_content = response.choices[0].message.content  # Raw response content
    try:
        keywords = json.loads(response_content).get("keywords", [])  # Extract keywords list
        return keywords
    except json.JSONDecodeError:
        print("Failed to parse JSON response.")
        return []

def scrape_tiktok(keywords):
    # Prepare the run input for the Apify actor
    run_input = {
        "excludePinnedPosts": False,
        "maxProfilesPerQuery": 1,
        "resultsPerPage": 5,
        "searchQueries": keywords,
        "shouldDownloadCovers": False,
        "shouldDownloadSlideshowImages": False,
        "shouldDownloadSubtitles": True,
        "shouldDownloadVideos": False
    }

    try:
        run = apify_client.actor("clockworks/free-tiktok-scraper").call(run_input=run_input)
        if not run:
            return None

        items = apify_client.dataset(run["defaultDatasetId"]).list_items().items
        return items

    except Exception as e:
        print(f"Error during TikTok scraping: {e}")
        return None

def save_to_csv(tiktok_data, filename):
    """
    Save TikTok data to a CSV file using pandas.
    Args:
        tiktok_data: List of TikTok video data
        filename: The name of the CSV file to save the data
    """
    # Prepare the data to be saved
    rows = []

    for video in tiktok_data:
        # Extract author metadata
        author_meta = video.get('authorMeta', {})

        # Create the data row
        row = {
            "request_id": str(uuid.uuid4()),  # Generate a unique request_id for this batch
            "creator_name": author_meta.get('name', ''),
            "creator_followers": author_meta.get('fans', ''),
            "nb_views": video.get('playCount', ''),
            "nb_likes": video.get('diggCount', 0),
            "nb_comments": video.get('commentCount', 0),
            "nb_shares": video.get('shareCount', 0),
            "nb_bookmarks": video.get('collectCount', 0),
            "language": video.get('language', ''),
            "creator_bio": author_meta.get('signature', ''),
            "creator_private": author_meta.get('privateAccount', False),
            "creator_total_nb_likes": author_meta.get('heart', ''),
            "creator_id": author_meta.get('id', ''),
            "creator_profile_url": author_meta.get('profileUrl', ''),
            "creator_verified": author_meta.get('verified', False),
            "creator_total_posts": author_meta.get('video', 0)
        }
        rows.append(row)

    # Convert the rows into a pandas DataFrame
    df = pd.DataFrame(rows)

    # Save the DataFrame to a CSV file
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    main()
