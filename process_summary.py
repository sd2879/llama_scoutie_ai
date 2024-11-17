import os
import json
from groq import Groq
from apify_client import ApifyClient
import uuid
import pandas as pd
import yaml  # Added for YAML processing
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
            csv_filename = "tiktok_results.csv"
            save_to_csv(tiktok_data, csv_filename)
            print(f"Data saved to {csv_filename}")
            
            # Convert CSV to YAML and count tokens
            yaml_string, token_count = csv_to_yaml_and_count_tokens(csv_filename)
            # print(f"YAML String:\n{yaml_string}")
            # print(f"Token Count: {token_count}")
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
        "resultsPerPage": 3,
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
    Save the entire raw TikTok data to a CSV file using pandas.
    Args:
        tiktok_data: List of raw TikTok video data
        filename: The name of the CSV file to save the raw data
    """
    # Convert the raw data into a pandas DataFrame
    df = pd.DataFrame(tiktok_data)

    # Rename 'id' to 'post_id'
    if 'id' in df.columns:
        df.rename(columns={'id': 'post_id'}, inplace=True)

    # Columns to drop
    columns_to_drop = ['createTime', 'createTimeISO', 'isAd', 'isMuted', 'musicMeta', 'isSlideshow', 'isPinned', 'mediaUrls', 'mentions', 'effectStickers']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')

    # Extract and rename keys from 'authorMeta'
    if 'authorMeta' in df.columns:
        renamed_columns = {
            'id': 'user_id',
            'profileUrl': 'user_profileurl',
            'signature': 'user_signature',
            'bioLink': 'user_biolink',
            'fans': 'user_fans',
            'heart': 'user_heart',
            'video': 'user_video',
            'digg': 'user_digg'
        }

        for key, renamed_key in renamed_columns.items():
            df[renamed_key] = df['authorMeta'].apply(lambda x: x.get(key) if isinstance(x, dict) else None)
        
        # Drop the 'authorMeta' column after extraction
        df.drop(columns=['authorMeta'], inplace=True)

    # Extract 'coverUrl' from 'videoMeta'
    if 'videoMeta' in df.columns:
        df['coverUrl'] = df['videoMeta'].apply(lambda x: x.get('coverUrl') if isinstance(x, dict) else None)
        df.drop(columns=['videoMeta'], inplace=True)

    # Extract and process hashtags
    if 'hashtags' in df.columns:
        df['hashtags_post'] = df['hashtags'].apply(
            lambda x: ', '.join([tag['name'] for tag in x if isinstance(tag, dict)]) if isinstance(x, list) else ''
        )
        df.drop(columns=['hashtags'], inplace=True)

    # Fill NaN values with an empty string
    df.fillna('', inplace=True)

    # Save the DataFrame to a CSV file
    df.to_csv(filename, index=False)
    
def csv_to_yaml_and_count_tokens(csv_file):
    """
    Convert a CSV file to YAML format and count tokens in the YAML string.
    Args:
        csv_file: The CSV file to convert
    Returns:
        yaml_multiline_string: The YAML string wrapped in triple quotes
        token_count: The total number of tokens
    """
    try:
        # Read the CSV file into a DataFrame
        df = pd.read_csv(csv_file)
        
        # Convert DataFrame to a list of dictionaries
        data = df.to_dict(orient='records')
        
        # Convert the data to a YAML string
        yaml_string = yaml.dump(data, default_flow_style=False, sort_keys=False)
        
        # Wrap it in triple quotes
        yaml_multiline_string = f"""\"\"\"\n{yaml_string}\"\"\""""

        with open("output.yaml", 'w') as yaml_file:
            yaml_file.write(yaml_string)
        
        # Count tokens by splitting on whitespace and other delimiters
        tokens = yaml_string.split()
        token_count = len(tokens)
        
        return yaml_multiline_string, token_count
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()