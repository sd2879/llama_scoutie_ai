import os
from apify_client import ApifyClient
from dotenv import load_dotenv
import sys
import json
import requests
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

def force_print(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


    # =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import re

import pytest

from camel.configs import GroqConfig
from camel.models import GroqModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GROQ_LLAMA_3_8B,
        ModelType.GROQ_LLAMA_3_70B,
    ],
)
def test_groq_llama3_model(model_type: ModelType):
    model_config_dict = GroqConfig().as_dict()
    model = GroqModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    # LLM served by Groq does not support token counter, so Camel uses
    # OpenAITokenCounter as a placeholder.
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_groq_llama3_model_unexpected_argument():
    model_type = ModelType.GROQ_LLAMA_3_70B
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into Groq model backend."
            )
        ),
    ):
        _ = GroqModel(model_type, model_config_dict)

class TikTokScraper:
    def __init__(self):
        load_dotenv()
        self.apify_token = os.environ.get("APIFY_API_TOKEN")
        if not self.apify_token or not self.apify_token.startswith("apify_api_"):
            raise ValueError("Error: APIFY_API_TOKEN is not set correctly in the environment variables")
        self.client = ApifyClient(self.apify_token)

    def scrape_by_username(self, username, max_videos=5):
        force_print(f"Scraping data for username: {username}")
        
        run_input = {
            "excludePinnedPosts": False,
            "maxProfilesPerQuery": 1,
            "resultsPerPage": 5,
            "searchQueries": [
                "emo, streetwear"
            ],
            "shouldDownloadCovers": False,
            "shouldDownloadSlideshowImages": False,
            "shouldDownloadSubtitles": True,
            "shouldDownloadVideos": False
        }
        
        return self._execute_scrape(run_input)

    def scrape_by_search(self, search_query, max_videos=5):
        force_print(f"Scraping data for search query: {search_query}")
        
        run_input = {
            "searchQuery": search_query,
            "maxVideos": max_videos,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "proxyConfiguration": {
                "useApifyProxy": True
            }
        }
        
        return self._execute_scrape(run_input)

    def _execute_scrape(self, run_input):
        try:
            force_print("Starting Apify actor run...")
            run = self.client.actor("clockworks/free-tiktok-scraper").call(run_input=run_input)
            
            if not run:
                force_print("No run data returned from Apify")
                return None
            
            force_print(f"Apify actor run finished. Run ID: {run['id']}")
            force_print("Fetching results from Apify...")
            
            items = self.client.dataset(run["defaultDatasetId"]).list_items().items
            force_print(f"Fetched {len(items)} items from Apify")
            
            return items

        except Exception as e:
            force_print(f"Error during scraping: {str(e)}")
            return None

def create_demographic_agent():
    """Create a CAMEL agent for analyzing creator demographics and NSFW content"""
    
    assistant_sys_msg = """You are an expert at analyzing TikTok creator profiles and images.
    Given a creator's profile image and basic information, analyze and estimate:
    1. Approximate age (e.g., "18-24", "25-34", etc.)
    2. Gender (e.g., "male", "female", "unknown")
    3. NSFW Risk Assessment (e.g., "safe", "questionable", "nsfw")
    
    For NSFW assessment, consider:
    - Profile image content
    - Username and bio text for suggestive content
    - Any explicit or adult-themed references
    
    Be objective and professional in your analysis. If you cannot determine something with reasonable confidence, indicate 'unknown'.
    Output this and nothing else.
    """
    
    assistant_model_config = ChatGPTConfig(
        temperature=0.2,
    )
    
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=assistant_model_config.as_dict(),
    )
    
    return ChatAgent(
        system_message=assistant_sys_msg,
        model=model
    )

def analyze_creator_demographics(agent, creator_data):
    """Analyze creator demographics and NSFW content using CAMEL agent"""
    
    prompt = f"""
    Analyze this TikTok creator based on their profile:
    
    Profile Image URL: {creator_data.get('authorMeta', {}).get('avatar', '')}
    Username: {creator_data.get('authorMeta', {}).get('name', '')}
    Bio: {creator_data.get('authorMeta', {}).get('signature', '')}
    
    Please provide:
    - Age range:
    - Gender:
    - NSFW Risk:
    """
    
    try:
        force_print("\n--- CAMEL Agent Analysis ---")
        force_print(f"Analyzing creator: {creator_data.get('authorMeta', {}).get('name', '')}")
        
        response = agent.step(prompt)
        content = response.msgs[0].content.lower()
        
        force_print("CAMEL Response:")
        force_print(response.msgs[0].content)
        force_print("------------------------\n")
        
        age_range = "unknown"
        gender = "unknown"
        nsfw_risk = "unknown"
        
        if "age range:" in content:
            age_range = content.split("age range:")[1].split("\n")[0].strip()
        if "gender:" in content:
            gender = content.split("gender:")[1].split("\n")[0].strip()
        if "nsfw risk:" in content:
            nsfw_risk = content.split("nsfw risk:")[1].split("\n")[0].strip()
            
        demographics = {
            "creator_age": age_range,
            "gender_age": gender,
            "nsfw_risk": nsfw_risk
        }
        
        force_print("Extracted Demographics:")
        force_print(json.dumps(demographics, indent=2))
        force_print("------------------------\n")
        
        return demographics
        
    except Exception as e:
        force_print(f"Error analyzing demographics: {str(e)}")
        return {
            "creator_age": "unknown",
            "gender_age": "unknown",
            "nsfw_risk": "unknown"
        }

def send_to_xano(tiktok_data):
    """
    Send TikTok data to Xano database with demographic information
    """
    XANO_ENDPOINT = "https://x4ns-oeir-6vhp.n7d.xano.io/api:tV0AYV79/ugc_content_metrics"
    
    # Create demographic analysis agent
    demo_agent = create_demographic_agent()
    
    for video in tiktok_data:
        # Get demographic analysis
        force_print("\nProcessing video ID:", video.get('id', ''))
        demographics = analyze_creator_demographics(demo_agent, video)
        
        # Extract author metadata
        author_meta = video.get('authorMeta', {})
        
        payload = {
            "request_id": str(video.get('id', '')),
            "creator_name": author_meta.get('name', ''),
            "creator_followers": author_meta.get('fans', ''),
            "nb_views": video.get('playCount', ''),
            "nb_likes": video.get('diggCount', 0),
            "nb_comments": video.get('commentCount', 0),
            "nb_shares": video.get('shareCount', 0),
            "nb_bookmarks": video.get('collectCount', 0),  # TikTok's term for bookmarks
            "language": video.get('language', ''),
            "creator_age": demographics['creator_age'],
            "creator_bio": author_meta.get('signature', ''),
            "creator_gender": demographics['gender_age'],
            "creator_private": author_meta.get('privateAccount', False),
            "creator_total_nb_likes": author_meta.get('heart', ''),  # Total likes received
            "creator_id": author_meta.get('id', ''),
            "creator_proflie_url": author_meta.get('profileUrl', ''),
            "creator_verified": author_meta.get('verified', False)
        }
        
        force_print("\nSending payload to Xano:")
        force_print(json.dumps(payload, indent=2))
        
        try:
            response = requests.post(XANO_ENDPOINT, json=payload)
            response.raise_for_status()
            force_print(f"Successfully sent data for video {payload['request_id']}")
        except requests.exceptions.RequestException as e:
            force_print(f"Error sending data to Xano: {e}")

def main():
    try:
        scraper = TikTokScraper()
        
        # Example usage
        # By username
        username_results = scraper.scrape_by_username("example_user", max_videos=5)
        if username_results:
            force_print("\nResults by username:")
            force_print(json.dumps(username_results[0], indent=2))  # Print first result as example
        
        # By search query
        search_results = scraper.scrape_by_search("example search", max_videos=5)
        if search_results:
            force_print("\nResults by search:")
            force_print(json.dumps(search_results[0], indent=2))  # Print first result as example
        
        # Send data to Xano
        send_to_xano(username_results)
        send_to_xano(search_results)

    except Exception as e:
        force_print(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
