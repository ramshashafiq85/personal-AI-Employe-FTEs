import os
import json
import requests
from datetime import datetime
from pathlib import Path

# --- CONFIGURATION ---
# Get these from your social media developer accounts
# Facebook: developers.facebook.com
# Instagram: developers.facebook.com (same app, add Instagram product)
# Twitter/X: developer.twitter.com

FACEBOOK_PAGE_ID = os.getenv("FB_PAGE_ID", "your_page_id")
FACEBOOK_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "your_access_token")

INSTAGRAM_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID", "your_ig_account_id")
INSTAGRAM_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "your_ig_access_token")

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "your_twitter_bearer_token")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "your_api_key")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "your_api_secret")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "your_access_token")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "your_access_secret")


class FacebookClient:
    """Facebook Page posting via Graph API"""
    
    def __init__(self, page_id=None, access_token=None):
        self.page_id = page_id or FACEBOOK_PAGE_ID
        self.access_token = access_token or FACEBOOK_ACCESS_TOKEN
        self.base_url = "https://graph.facebook.com/v19.0"
    
    def post_to_page(self, message, link=None, image_url=None):
        """Post a message to Facebook Page"""
        url = f"{self.base_url}/{self.page_id}/feed"
        data = {
            "message": message,
            "access_token": self.access_token
        }
        if link:
            data["link"] = link
        if image_url:
            data["url"] = image_url
        
        try:
            response = requests.post(url, data=data)
            result = response.json()
            if "id" in result:
                return {"success": True, "post_id": result["id"]}
            else:
                return {"success": False, "error": result.get("error", {}).get("message", "Unknown error")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_page_insights(self, metric="page_posts"):
        """Get Facebook Page insights"""
        url = f"{self.base_url}/{self.page_id}/insights"
        params = {
            "metric": metric,
            "access_token": self.access_token
        }
        
        try:
            response = requests.get(url, params=params)
            result = response.json()
            return result.get("data", [])
        except Exception as e:
            return {"error": str(e)}
    
    def get_recent_posts(self, limit=10):
        """Get recent posts from Facebook Page"""
        url = f"{self.base_url}/{self.page_id}/posts"
        params = {
            "limit": limit,
            "access_token": self.access_token,
            "fields": "message,created_time,likes.summary(true),comments.summary(true)"
        }
        
        try:
            response = requests.get(url, params=params)
            result = response.json()
            return result.get("data", [])
        except Exception as e:
            return {"error": str(e)}


class InstagramClient:
    """Instagram Business posting via Graph API"""
    
    def __init__(self, account_id=None, access_token=None):
        self.account_id = account_id or INSTAGRAM_ACCOUNT_ID
        self.access_token = access_token or INSTAGRAM_ACCESS_TOKEN
        self.base_url = "https://graph.facebook.com/v19.0"
    
    def post_image(self, image_url, caption=""):
        """Post an image to Instagram (2-step process)"""
        # Step 1: Create media
        create_url = f"{self.base_url}/{self.account_id}/media"
        create_data = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(create_url, data=create_data)
            create_result = response.json()
            
            if "id" not in create_result:
                return {"success": False, "error": create_result.get("error", {}).get("message", "Failed to create media")}
            
            creation_id = create_result["id"]
            
            # Step 2: Publish media
            publish_url = f"{self.base_url}/{self.account_id}/media_publish"
            publish_data = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            response = requests.post(publish_url, data=publish_data)
            publish_result = response.json()
            
            if "id" in publish_result:
                return {"success": True, "post_id": publish_result["id"]}
            else:
                return {"success": False, "error": publish_result.get("error", {}).get("message", "Failed to publish")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def post_reel(self, video_url, caption="", thumb_offset=0):
        """Post a reel to Instagram"""
        # Step 1: Create reel
        create_url = f"{self.base_url}/{self.account_id}/media"
        create_data = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "thumb_offset": thumb_offset,
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(create_url, data=create_data)
            create_result = response.json()
            
            if "id" not in create_result:
                return {"success": False, "error": create_result.get("error", {}).get("message", "Failed to create reel")}
            
            creation_id = create_result["id"]
            
            # Step 2: Publish reel
            publish_url = f"{self.base_url}/{self.account_id}/media_publish"
            publish_data = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            response = requests.post(publish_url, data=publish_data)
            publish_result = response.json()
            
            if "id" in publish_result:
                return {"success": True, "post_id": publish_result["id"]}
            else:
                return {"success": False, "error": publish_result.get("error", {}).get("message", "Failed to publish")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_insights(self):
        """Get Instagram account insights"""
        url = f"{self.base_url}/{self.account_id}/insights"
        params = {
            "metric": "follower_count,impressions,reach,profile_views",
            "access_token": self.access_token
        }
        
        try:
            response = requests.get(url, params=params)
            result = response.json()
            return result.get("data", [])
        except Exception as e:
            return {"error": str(e)}


class TwitterClient:
    """Twitter/X posting via API v2"""
    
    def __init__(self, api_key=None, api_secret=None, access_token=None, access_secret=None):
        self.api_key = api_key or TWITTER_API_KEY
        self.api_secret = api_secret or TWITTER_API_SECRET
        self.access_token = access_token or TWITTER_ACCESS_TOKEN
        self.access_secret = access_secret or TWITTER_ACCESS_SECRET
        self.base_url = "https://api.twitter.com/2"
    
    def _get_oauth_header(self):
        """Generate OAuth 1.0a header (simplified - use tweepy in production)"""
        # For production, use: pip install tweepy
        # This is a placeholder showing the structure
        return {
            "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def post_tweet(self, text):
        """Post a tweet"""
        url = f"{self.base_url}/tweets"
        headers = self._get_oauth_header()
        payload = {"text": text}
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            result = response.json()
            
            if "data" in result:
                return {"success": True, "tweet_id": result["data"]["id"]}
            else:
                return {"success": False, "error": result.get("errors", [{}])[0].get("detail", "Unknown error")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_recent_tweets(self, limit=10):
        """Get recent tweets"""
        # Requires proper OAuth setup - placeholder
        return {"note": "Requires OAuth setup. Use tweepy for production."}


class SocialMediaManager:
    """Unified manager for all social media platforms"""
    
    def __init__(self):
        self.facebook = FacebookClient()
        self.instagram = InstagramClient()
        self.twitter = TwitterClient()
    
    def post_to_all(self, message, image_url=None):
        """Post to all platforms and return results"""
        results = {}
        
        # Facebook
        print("Posting to Facebook...")
        results["facebook"] = self.facebook.post_to_page(message)
        print(f"  Facebook: {results['facebook']}")
        
        # Instagram (requires image)
        if image_url:
            print("Posting to Instagram...")
            results["instagram"] = self.instagram.post_image(image_url, message)
            print(f"  Instagram: {results['instagram']}")
        else:
            results["instagram"] = {"skipped": "No image URL provided"}
        
        # Twitter
        print("Posting to Twitter...")
        results["twitter"] = self.twitter.post_tweet(message)
        print(f"  Twitter: {results['twitter']}")
        
        return results
    
    def generate_summary(self):
        """Generate a social media summary"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "facebook": {},
            "instagram": {},
            "twitter": {}
        }
        
        # Facebook insights
        fb_posts = self.facebook.get_recent_posts(limit=5)
        if isinstance(fb_posts, list):
            summary["facebook"] = {
                "recent_posts_count": len(fb_posts),
                "posts": [{"message": p.get("message", "")[:50], "date": p.get("created_time")} for p in fb_posts[:3]]
            }
        
        # Instagram insights
        ig_insights = self.instagram.get_insights()
        if isinstance(ig_insights, list):
            summary["instagram"] = {
                "insights": ig_insights
            }
        
        return summary


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python social_media_client.py <command> [args]")
        print("Commands:")
        print("  post <message> [--image <url>]  - Post to all platforms")
        print("  post_fb <message>               - Post to Facebook only")
        print("  post_ig <image_url> <caption>   - Post to Instagram")
        print("  post_twitter <message>          - Post to Twitter")
        print("  summary                         - Generate social media summary")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = SocialMediaManager()
    
    if command == "post":
        message = " ".join(sys.argv[2:])
        image_url = None
        if "--image" in sys.argv:
            idx = sys.argv.index("--image")
            if idx + 1 < len(sys.argv):
                image_url = sys.argv[idx + 1]
        
        print(f"\nPosting: {message}")
        if image_url:
            print(f"Image: {image_url}")
        print()
        
        results = manager.post_to_all(message, image_url)
        print(f"\nResults: {json.dumps(results, indent=2)}")
    
    elif command == "post_fb":
        message = " ".join(sys.argv[2:])
        result = manager.facebook.post_to_page(message)
        print(f"Facebook: {json.dumps(result, indent=2)}")
    
    elif command == "post_ig":
        if len(sys.argv) < 4:
            print("Usage: python social_media_client.py post_ig <image_url> <caption>")
            sys.exit(1)
        image_url = sys.argv[2]
        caption = " ".join(sys.argv[3:])
        result = manager.instagram.post_image(image_url, caption)
        print(f"Instagram: {json.dumps(result, indent=2)}")
    
    elif command == "post_twitter":
        message = " ".join(sys.argv[2:])
        result = manager.twitter.post_tweet(message)
        print(f"Twitter: {json.dumps(result, indent=2)}")
    
    elif command == "summary":
        summary = manager.generate_summary()
        print(json.dumps(summary, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
