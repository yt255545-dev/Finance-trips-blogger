import os
import random
import json
import time
import requests
import base64
from google import genai
from google.genai import types
import google.oauth2.credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# GitHub Secrets থেকে ডেটা সংগ্রহ
BLOG_ID = os.environ.get("BLOG_ID")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GEMINI_KEYS = [k.strip() for k in os.environ.get("GEMINI_KEYS", "").split(",") if k.strip()]
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
    
    host = "openrouter.ai"
    endpoint = "/api/v1/chat/completions"
    url = "https://" + host + endpoint
    
    api_key = OPENROUTER_API_KEY.strip() if OPENROUTER_API_KEY else ""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://" + "github.com",
        "X-Title": "Blogger Auto Poster"
    }
    
    # ওপেন রাউটারের ১০০% ভ্যালিড এবং কার্যকরী ফ্রি মডেল
    payload = {
        "model": "google/gemini-2.5-flash:free", 
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
    # জেমিনির Imagen 3 মডেল দিয়ে সরাসরি ছবি তৈরি করা হচ্ছে
    if not GEMINI_KEYS:
        print("No Gemini API keys found, using fallback URL.")
        safe_kw = keyword.replace(' ', '%20')
        return f"[https://image.pollinations.ai/prompt/professional%20](https://image.pollinations.ai/prompt/professional%20){safe_kw}?width=800&height=400&nologo=true", f"[https://image.pollinations.ai/prompt/creative%20](https://image.pollinations.ai/prompt/creative%20){safe_kw}?width=800&height=400&nologo=true"
    
    api_key = random.choice(GEMINI_KEYS)
    
    try:
        client = genai.Client(api_key=api_key)
        print("Generating images directly via Gemini (Imagen 3)...")
        
        # প্রথম ছবি জেনারেট
        prompt1 = f"A professional, highly detailed, photorealistic wide image representing: {keyword}. High quality, no text, no watermarks."
        result1 = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=prompt1,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9"
            )
        )
        img1_bytes = result1.generated_images[0].image.image_bytes
        img1_b64 = base64.b64encode(img1_bytes).decode('utf-8')
        img_src_1 = f"data:image/jpeg;base64,{img1_b64}"
        
        # দ্বিতীয় ছবি জেনারেট
        prompt2 = f"A creative, modern, cinematic lighting concept art representing: {keyword}. High quality, no text, no watermarks."
        result2 = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=prompt2,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9"
            )
        )
        img2_bytes = result2.generated_images[0].image.image_bytes
        img2_b64 = base64.b64encode(img2_bytes).decode('utf-8')
        img_src_2 = f"data:image/jpeg;base64,{img2_b64}"
        
        print("Images generated successfully by Gemini!")
        return img_src_1, img_src_2
        
    except Exception as e:
        print(f"Gemini direct image generation failed: {e}. Falling back to URL generation.")
        safe_kw = keyword.replace(' ', '%20')
        img1 = "https://" + f"image.pollinations.ai/prompt/photorealistic%20{safe_kw}?width=800&height=400&nologo=true"
        img2 = "https://" + f"image.pollinations.ai/prompt/cinematic%20lighting%20{safe_kw}?width=800&height=400&nologo=true"
        return img1, img2

def publish_to_blogger(title, content, tags):
    token_data = json.loads(TOKEN_JSON)
    token_uri = token_data.get('token_uri', "https://" + '[oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)')
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
            scopes=["https://" + '[www.googleapis.com/auth/indexing](https://www.googleapis.com/auth/indexing)']
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
    
    article_data = generate_seo_content_via_openrouter(CATEGORY)
    
    img_url_1, img_url_2 = generate_images_via_gemini(article_data['keyword'])
    
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
        
