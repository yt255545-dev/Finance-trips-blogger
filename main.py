import os
import random
import json
import time
import requests
import google.oauth2.credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google import genai

# GitHub Secrets থেকে ডেটা সংগ্রহ
BLOG_ID = os.environ.get("BLOG_ID")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GEMINI_KEYS = [k.strip() for k in os.environ.get("GEMINI_KEYS", "").split(",") if k.strip()]
TOKEN_JSON = os.environ.get("BLOGGER_TOKEN_JSON") 
INDEXING_JSON = os.environ.get("INDEXING_JSON")
CATEGORY = os.environ.get("CATEGORY", "Personal Finance")

def clean_and_parse_json(text):
    try:
        text = text.replace('```json', '').replace('```', '').strip()
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]
        return json.loads(text, strict=False)
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        raise e

def generate_seo_content(category):
    prompt = f"""
    Act as an expert SEO blog writer. Write a detailed, long, and fully SEO-optimized blog post in English about a trending topic in this category: '{category}'.
    Include a catchy Title, Meta Description, and Focus Keyword.
    Use rich HTML formatting for the content (use multiple <h2>, <h3>, <p>, <ul>, <li>, etc.) to make it a comprehensive long-form article. Do not include ```html or markdown blocks, just raw HTML.
    Return the result EXACTLY in this JSON format without any extra text:
    {{
        "title": "Post Title",
        "keyword": "focus keyword",
        "tags": ["{category}", "Trending"],
        "content": "HTML content here"
    }}
    """
    
    # পদ্ধতি ১: OpenRouter দিয়ে চেষ্টা করা
    if OPENROUTER_API_KEY:
        try:
            print(f"Trying to generate blog via OpenRouter (Primary)...")
            host = "openrouter.ai"
            endpoint = "/api/v1/chat/completions"
            url = "https://" + host + endpoint
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://" + "github.com",
                "X-Title": "Blogger Auto Poster"
            }
            
            payload = {
                "model": "openrouter/free", 
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            if "choices" in response_data:
                content_text = response_data["choices"][0]["message"]["content"]
                print("Successfully generated content via OpenRouter!")
                return clean_and_parse_json(content_text)
            else:
                print(f"OpenRouter returned unexpected response: {response_data}")
        except Exception as e:
            print(f"OpenRouter failed: {e}. Switching to Gemini backup...")

    # পদ্ধতি ২: Gemini ব্যাকআপ
    if GEMINI_KEYS:
        try:
            print("Switching to Gemini API for blog generation (Backup)...")
            api_key = random.choice(GEMINI_KEYS)
            client = genai.Client(api_key=api_key)
            
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
            )
            print("Successfully generated content via Gemini Backup!")
            return clean_and_parse_json(response.text)
        except Exception as e:
            print(f"Gemini generation also failed: {e}")
            
    print("All content generation methods failed!")
    exit(1)

def generate_images(keyword):
    safe_kw = keyword.replace(' ', '%20')
    img1 = f"[https://image.pollinations.ai/prompt/professional%20photorealistic%20](https://image.pollinations.ai/prompt/professional%20photorealistic%20){safe_kw}?width=800&height=400&nologo=true"
    img2 = f"[https://image.pollinations.ai/prompt/modern%20cinematic%20concept%20](https://image.pollinations.ai/prompt/modern%20cinematic%20concept%20){safe_kw}?width=800&height=400&nologo=true"
    return img1, img2

def publish_to_blogger(title, content, tags):
    try:
        token_data = json.loads(TOKEN_JSON)
    except Exception as e:
        print(f"Error parsing BLOGGER_TOKEN_JSON: {e}")
        exit(1)
    
    # টোকেন ইউআরআই থেকে সব ধরনের ব্র্যাকেট বা ভুল ক্যারেক্টার জোরপূর্বক পরিষ্কার করা হলো
    raw_uri = str(token_data.get('token_uri', '[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)'))
    token_uri = raw_uri.replace('[', '').replace(']', '').replace("'", "").replace('"', "").strip()
    if not token_uri.startswith('http'):
        token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"

    creds = google.oauth2.credentials.Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_uri,
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret')
    )
    
    service = build('blogger', 'v3', credentials=creds)
    
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": tags
    }
    
    request = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=False)
    response = request.execute()
    post_url = response.get('url')
    print(f"Successfully posted 1 article! URL: {post_url}")
    return post_url

def notify_google_indexing(url):
    try:
        indexing_credentials = service_account.Credentials.from_service_account_info(
            json.loads(INDEXING_JSON),
            scopes=["[https://www.googleapis.com/auth/indexing](https://www.googleapis.com/auth/indexing)"]
        )
        service = build('indexing', 'v3', credentials=indexing_credentials)
        
        body = {
            "url": url,
            "type": "URL_UPDATED"
        }
        
        response = service.urlNotifications().publish(body=body).execute()
        print(f"Google Indexing API Notified Successfully! Response: {response}")
    except Exception as e:
        print(f"Error Indexing URL: {e}")

if __name__ == "__main__":
    print(f"Working on category: {CATEGORY}")
    
    article_data = generate_seo_content(CATEGORY)
    
    img_url_1, img_url_2 = generate_images(article_data['keyword'])
    
    final_html_content = f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="{img_url_1}" alt="{article_data['keyword']} - Main Image" style="max-width:100%; height:auto; border-radius:8px;"/>
    </div>
    <br>
    {article_data['content']}
    <br>
    <div style="text-align: center; margin-top: 20px;">
        <img src="{img_url_2}" alt="{article_data['keyword']} - Secondary Image" style="max-width:100%; height:auto; border-radius:8px;"/>
    </div>
    """
    
    published_url = publish_to_blogger(article_data['title'], final_html_content, article_data['tags'])
    
    if published_url:
        notify_google_indexing(published_url)
    

