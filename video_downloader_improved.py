#!/usr/bin/env python3

import instaloader
import sys
import time
import re

def download_single_post(post_url):
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        max_connection_attempts=1,
        request_timeout=10
    )
    
    try:
        # Extract shortcode from URL
        shortcode_match = re.search(r'/p/([A-Za-z0-9_-]+)/', post_url)
        if not shortcode_match:
            print("❌ Invalid Instagram post URL")
            return
        
        shortcode = shortcode_match.group(1)
        print(f"Downloading post: {shortcode}")
        
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        if not post.is_video:
            print("❌ This post is not a video")
            return
            
        L.download_post(post, target="single_post")
        print("✅ Video downloaded successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def download_videos_with_retry(username, count=5):
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        max_connection_attempts=1,
        request_timeout=10
    )
    
    try:
        print(f"Attempting to access @{username}...")
        profile = instaloader.Profile.from_username(L.context, username)
        print(f"✅ Profile found: {profile.full_name}")
        print(f"Posts: {profile.mediacount}")
        
        print(f"Searching for {count} videos...")
        video_count = 0
        
        for post in profile.get_posts():
            if post.is_video and video_count < count:
                print(f"Found video {video_count + 1}: {post.shortcode}")
                try:
                    L.download_post(post, target=username)
                    video_count += 1
                    print(f"✅ Downloaded video {video_count}/{count}")
                    time.sleep(2)  # Rate limiting
                except Exception as e:
                    print(f"⚠️ Failed to download: {e}")
                    
            elif video_count >= count:
                break
                
        print(f"✅ Process complete. Downloaded {video_count} videos")
        
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"❌ Profile @{username} does not exist")
    except instaloader.exceptions.LoginRequiredException:
        print(f"❌ Profile @{username} is private - login required")
    except Exception as e:
        if "429" in str(e) or "rate" in str(e).lower():
            print("❌ Rate limited by Instagram. Try again later or use --login")
        else:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python video_downloader_improved.py <username> [count]")
        print("   or: python video_downloader_improved.py --url <post_url>")
        sys.exit(1)
    
    if sys.argv[1] == "--url":
        if len(sys.argv) < 3:
            print("Usage: python video_downloader_improved.py --url <post_url>")
            sys.exit(1)
        post_url = sys.argv[2]
        download_single_post(post_url)
    else:
        username = sys.argv[1]
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        download_videos_with_retry(username, count)
