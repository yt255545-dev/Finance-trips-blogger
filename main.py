import os
import random
import json
import time
import requests
from google import genai
import google.oauth2.credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# GitHub Secrets থেকে প্রয়োজনীয় তথ্য সংগ্রহ
BLOG_ID = os.environ.get("BLOG_ID")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") # OpenRouter API Key
GEMINI_KEYS = [k.strip() for k in os.environ.get("GEMINI_KEYS", "").split(",") if k.strip()] # Gemini API Key
TOKEN_JSON = os.environ.get("BLOGGER_TOKEN_JSON") 
INDEXING_JSON = os.environ.get("INDEXING_JSON")
CATEGORY = os.environ.get("CATEGORY", "Personal Finance")

def generate_seo_content_via_openrouter(category):
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
    
    # URL একদম নিখুঁতভাবে দেওয়া হলো (কোনো ব্র্যাকেট ছাড়া)
    url = "[https://openrouter.ai/api/v1/chat/completions](https://openrouter.ai/api/v1/chat/completions)"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY.strip() if OPENROUTER_API_KEY else ''}",
        "Content-Type": "application/json",
        "HTTP-Referer": "[https://github.com](https://github.com)",
        "X-Title": "Blogger Auto Poster"
    }
    
    payload = {
        "model": "openai/gpt-5.6-sol", 
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        print(f"Generating SEO blog via OpenRouter for category: {category}...")
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        
        if "choices" in response_data:
            content_text = response_data["choices"][0]["message"]["content"]
            text = content_text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        else:
            print(f"OpenRouter Response Error: {response_data}")
            exit(1)
    except Exception as e:
        print(f"Failed to generate content: {e}")
        exit(1)

def generate_images_via_gemini(keyword):
    if not GEMINI_KEYS:
        print("No Gemini API keys found, using default fallback.")
        safe_kw = keyword.replace(' ', '%20')
        return f"[https://image.pollinations.ai/prompt/professional%20](https://image.pollinations.ai/prompt/professional%20){safe_kw}?width=800&height=400&nologo=true", \
               f"[https://image.pollinations.ai/prompt/creative%20concept%20](https://image.pollinations.ai/prompt/creative%20concept%20){safe_kw}?width=800&height=400&nologo=true"
    
    api_key = random.choice(GEMINI_KEYS)
    
    try:
        client = genai.Client(api_key=api_key)
        prompt_desc = f"Create two distinct, highly descriptive image generation prompts for an article about: {keyword}. Return them as JSON list."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_desc,
        )
        
        safe_kw = keyword.replace(' ', '%20')
        img1 = f"[https://image.pollinations.ai/prompt/photorealistic%20](https://image.pollinations.ai/prompt/photorealistic%20){safe_kw}?width=800&height=400&nologo=true"
        img2 = f"[https://image.pollinations.ai/prompt/cinematic%20lighting%20](https://image.pollinations.ai/prompt/cinematic%20lighting%20){safe_kw}?width=800&height=400&nologo=true"
        return img1, img2
    except Exception as e:
        print(f"Gemini image generation warning: {e}, using default fallback.")
        safe_kw = keyword.replace(' ', '%20')
        return f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){safe_kw}?width=800&height=400&nologo=true", \
               f"[https://image.pollinations.ai/prompt/abstract%20](https://image.pollinations.ai/prompt/abstract%20){safe_kw}?width=800&height=400&nologo=true"

def publish_to_blogger(title, content, tags):
    token_data = json.loads(TOKEN_JSON)
    token_uri = token_data.get('token_uri', '[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)')
    token_uri = token_uri.replace('[', '').replace(']', '').strip()
    
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
            scopes=['[https://www.googleapis.com/auth/indexing](https://www.googleapis.com/auth/indexing)']
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
    
    # ১. OpenRouter দিয়ে এসইও ব্লগ তৈরি
    article_data = generate_seo_content_via_openrouter(CATEGORY)
    
    # ২. ছবি তৈরি করা
    img_url_1, img_url_2 = generate_images_via_gemini(article_data['keyword'])
    
    # ৩. কন্টেন্টের ভেতর দুটি ছবি বসানো
    final_html_content = f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="{img_url_1}" alt="{article_data['keyword']} - Main" style="max-width:100%; height:auto; border-radius:8px;"/>
    </div>
    <br>
    {article_data['content']}
    <br>
    <div style="text-align: center; margin-top: 20px;">
        <img src="{img_url_2}" alt="{article_data['keyword']} - Secondary" style="max-width:100%; height:auto; border-radius:8px;"/>
    </div>
    """
    
    # ৪. ব্লগারে পোস্ট পাবলিশ করা
    published_url = publish_to_blogger(article_data['title'], final_html_content, article_data['tags'])
    
    # ৫. গুগল ইনডেক্সিং পাঠানো
    if published_url:
        notify_google_indexing(published_url)
    
