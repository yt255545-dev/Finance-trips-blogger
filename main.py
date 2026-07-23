import os
import random
import json
import time
import requests
from google import genai
import google.oauth2.credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# GitHub Secrets থেকে ডেটা সংগ্রহ
BLOG_ID = os.environ.get("BLOG_ID")
GEMINI_KEYS = [k.strip() for k in os.environ.get("GEMINI_KEYS").split(",") if k.strip()]
TOKEN_JSON = os.environ.get("BLOGGER_TOKEN_JSON") 
INDEXING_JSON = os.environ.get("INDEXING_JSON")
CATEGORY = os.environ.get("CATEGORY", "Personal Finance")

def generate_seo_content(category):
    prompt = f"""
    Act as an expert SEO blog writer. Write a highly engaging, fully SEO-optimized blog post in English about a trending topic in this category: '{category}'.
    Include a catchy Title, Meta Description, and Focus Keyword.
    Use HTML formatting for the content (use <h2>, <h3>, <p>, <ul>, etc.). Do not include ```html or markdown blocks, just raw HTML.
    Return the result EXACTLY in this JSON format without any extra text:
    {{
        "title": "Post Title",
        "keyword": "focus keyword",
        "tags": ["{category}", "Trending"],
        "content": "HTML content here"
    }}
    """
    
    # ফ্রি API এর জন্য পরীক্ষিত ও রিলায়েবল মডেলসমূহ
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash']
    
    random.shuffle(GEMINI_KEYS)
    for api_key in GEMINI_KEYS:
        try:
            client = genai.Client(api_key=api_key)
            for model_name in models_to_try:
                try:
                    print(f"Trying model {model_name}...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    text = response.text.replace('```json', '').replace('```', '').strip()
                    return json.loads(text)
                except Exception as model_err:
                    print(f"Model {model_name} failed: {model_err}")
                    time.sleep(1)
                    continue
        except Exception as key_err:
            print(f"API Key error: {key_err}")
            continue
            
    print("All Gemini API keys and models failed.")
    exit(1)

def publish_to_blogger(title, content, tags):
    token_data = json.loads(TOKEN_JSON)
    
    # ইউআরএল থেকে ভুল ব্র্যাকেট বা স্পেস পরিষ্কার করার লজিক
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
    print(f"Successfully posted to Blogger! URL: {post_url}")
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
    
    # 1. Gemini থেকে কন্টেন্ট তৈরি
    article_data = generate_seo_content(CATEGORY)
    
    # 2. Pollinations AI থেকে ছবি তৈরি
    safe_keyword = article_data['keyword'].replace(' ', '%20')
    image_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){safe_keyword}?width=800&height=400&nologo=true"
    
    # 3. ছবি এবং টেক্সট যুক্ত করা
    final_html_content = f"""
    <div style="text-align: center;">
        <img src="{image_url}" alt="{article_data['keyword']}" style="max-width:100%; height:auto; border-radius:8px;"/>
    </div>
    <br><br>
    {article_data['content']}
    """
    
    # 4. ব্লগারে পাবলিশ করা
    published_url = publish_to_blogger(article_data['title'], final_html_content, article_data['tags'])
    
    # 5. গুগলে ইন্ডেক্সিং এর জন্য পাঠানো
    if published_url:
        notify_google_indexing(published_url)
