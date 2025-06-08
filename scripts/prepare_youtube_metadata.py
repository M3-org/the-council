#!/usr/bin/env python3
"""
YouTube Metadata Extractor
Extracts episode data from session log and prepares YouTube upload metadata

Usage: python scripts/prepare_youtube_metadata.py <session-log.json>
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from PIL import Image

def extract_youtube_metadata(session_log_path, playlist_id=None):
    """Extract YouTube metadata from session log file"""
    
    if not os.path.exists(session_log_path):
        print(f"Session log file not found: {session_log_path}")
        return None
    
    try:
        with open(session_log_path, 'r') as f:
            session_data = json.load(f)
    except Exception as e:
        print(f"Error reading session log: {e}")
        return None
    
    # Extract core episode data
    episode_data = session_data.get('episode_data', {})
    if not episode_data:
        print(f"Error: 'episode_data' not found in {session_log_path}")
        sys.exit(1)

    episode_id = episode_data.get('id', 'S?E?')
    episode_title = episode_data.get('name', 'Unknown Episode')
    episode_premise = episode_data.get('premise', '')
    
    # Get video file paths
    original_video = session_data.get('original_video_file', '')
    processed_video = session_data.get('processed_mp4_file', '')
    
    # Determine best video file to use
    video_file = processed_video if processed_video else original_video
    video_path = f"recordings/{video_file}" if video_file else None
    
    # Check if video file exists
    if video_path and not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        video_path = None
    
    # Create YouTube title
    youtube_title = f"JedAI Council {episode_id}: {episode_title}"
    
    # Create comprehensive description
    show_config = session_data.get('show_config', {})
    show_description = show_config.get('description', '')
    
    # Generate a simple description from scene summaries
    scene_descriptions = ""
    for scene in session_data.get('scenes', []):
        scene_descriptions += f"{scene.get('summary', 'Scene summary not available')}\n"
    
    youtube_description = f"""JedAI Council Episode {episode_id}: {episode_title}

{episode_premise}

{scene_descriptions}

{show_description}

Recorded: {datetime.now().strftime('%B %d, %Y')}
Show: JedAI Council  

Links:
• JedAI Council: https://m3org.com/tv/jedai-council
• ElizaOS: https://github.com/elizaOS/eliza
"""
    
    # Generate tags
    tags = [
        "JedAI Council",
        "AI",
        "Blockchain", 
        "Web3",
        "ElizaOS",
        "ai16z",
        "Governance",
        "AGI",
        "Automation",
        "Crypto",
        "Agents",
        "DAO"
    ]
    
    # Try to find thumbnail from episode data
    thumbnail_url = episode_data.get('image', '')
    thumbnail_file = None
    
    if thumbnail_url:
        # Extract filename from URL for local download
        thumbnail_filename = f"{episode_id}.jpg"
        thumbnail_file = f"media/thumbnails/{thumbnail_filename}"
    
    return {
        'episode_id': episode_id,
        'episode_title': episode_title,
        'episode_premise': episode_premise,
        'video_file': video_path,
        'youtube_title': youtube_title,
        'youtube_description': youtube_description,
        'tags': ', '.join(tags),
        'category_id': '22',  # News & Politics
        'privacy_status': 'unlisted',
        'thumbnail_file': thumbnail_file,
        'thumbnail_url': thumbnail_url,
        'playlist_id': playlist_id,
        'session_log': session_log_path
    }

def save_metadata_json(metadata, output_path):
    """Save metadata to JSON file for upload_to_youtube.py --from-json"""
    
    json_metadata = {
        'video_file': metadata['video_file'],
        'title': metadata['youtube_title'],
        'description': metadata['youtube_description'],
        'tags': metadata['tags'],
        'category_id': metadata['category_id'],
        'privacy_status': metadata['privacy_status']
    }
    
    # Exclude thumbnail from automated upload for robustness
    # The thumbnail is still downloaded and archived for manual upload
    # if metadata['thumbnail_file']:
    #     json_metadata['thumbnail_file'] = metadata['thumbnail_file']
    
    if metadata['playlist_id']:
        json_metadata['playlist_id'] = metadata['playlist_id']
    
    try:
        with open(output_path, 'w') as f:
            json.dump(json_metadata, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving JSON metadata: {e}")
        return False

def compress_image(input_path, output_path, max_size_mb=1.8):
    """Compress image to stay under YouTube's 2MB thumbnail limit"""
    try:
        max_size_bytes = max_size_mb * 1024 * 1024
        
        with Image.open(input_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Start with high quality
            quality = 95
            
            while quality > 10:
                # Save to temporary location to check size
                img.save(output_path, 'PNG', optimize=True)
                
                # Check file size
                if os.path.getsize(output_path) <= max_size_bytes:
                    break
                
                # If still too large, reduce dimensions and try again
                if quality == 95:
                    # Resize to YouTube's recommended thumbnail size
                    img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                elif quality == 85:
                    # Further reduce size if needed
                    img = img.resize((960, 540), Image.Resampling.LANCZOS)
                
                quality -= 10
            
            # Final check - if still too large, use JPEG
            if os.path.getsize(output_path) > max_size_bytes:
                jpeg_path = output_path.replace('.png', '.jpg')
                img.save(jpeg_path, 'JPEG', quality=85, optimize=True)
                if os.path.getsize(jpeg_path) <= max_size_bytes:
                    os.remove(output_path)
                    os.rename(jpeg_path, output_path.replace('.png', '.jpg'))
                    return output_path.replace('.png', '.jpg')
            
            return output_path
            
    except Exception as e:
        print(f"Error compressing image: {e}")
        return input_path

def download_thumbnail(url, output_path):
    """Download and compress thumbnail from URL"""
    if not url:
        return False
    
    try:
        import requests
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()
        
        # Download to temporary location first
        temp_path = output_path + '.tmp'
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Compress the image
        final_path = compress_image(temp_path, output_path)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Verify final size
        file_size_mb = os.path.getsize(final_path) / (1024 * 1024)
        if file_size_mb > 2.0:
            print(f"Warning: Thumbnail still large ({file_size_mb:.1f}MB)")
        
        return True
        
    except Exception as e:
        print(f"Could not download thumbnail: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/prepare_youtube_metadata.py <session-log.json> [playlist-id]")
        sys.exit(1)
    
    session_log_path = sys.argv[1]
    playlist_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Extract metadata
    metadata = extract_youtube_metadata(session_log_path, playlist_id)
    if not metadata:
        sys.exit(1)
    
    print(f"Episode: {metadata['episode_title']} ({metadata['episode_id']})")
    print(f"Video File: {metadata['video_file']}")
    print(f"YouTube Title: {metadata['youtube_title']}")
    if metadata['playlist_id']:
        print(f"Playlist ID: {metadata['playlist_id']}")
    
    # Download thumbnail if available
    if metadata['thumbnail_url'] and metadata['thumbnail_file']:
        if download_thumbnail(metadata['thumbnail_url'], metadata['thumbnail_file']):
            # Verify final file exists and size
            if os.path.exists(metadata['thumbnail_file']):
                size_mb = os.path.getsize(metadata['thumbnail_file']) / (1024 * 1024)
                print(f"Thumbnail: {metadata['thumbnail_file']} ({size_mb:.1f}MB)")
            else:
                print("Thumbnail download failed")
                metadata['thumbnail_file'] = None
        else:
            metadata['thumbnail_file'] = None
            print("Thumbnail download failed, proceeding without")
    
    # Generate output filenames
    base_name = Path(session_log_path).stem.replace('_session-log', '')
    json_output = f"recordings/{base_name}_youtube-meta.json"
    
    # Save JSON metadata file
    if save_metadata_json(metadata, json_output):
        print(f"Metadata saved: {json_output}")
    
    print(f"✅ YouTube metadata prepared successfully for {base_name}")
    print(f"Episode: {metadata['episode_title']} ({metadata['episode_id']})")
    print(f"Thumbnail: {metadata['thumbnail_file']}")
    print(f"YouTube Title: {metadata['youtube_title']}")

if __name__ == '__main__':
    main() 
