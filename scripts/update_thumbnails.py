#!/usr/bin/env python3
"""
Script to extract YouTube thumbnail URLs from playlist.json and update episodes.json
"""

import json
import os

def load_json_file(filename):
    """Load JSON file and return data"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing {filename}: {e}")
        return None

def get_highest_resolution_thumbnail(thumbnails):
    """Get the highest resolution thumbnail URL from thumbnails array"""
    if not thumbnails:
        return None
    
    # Find the thumbnail with the highest resolution (336x188)
    # or the last one in the array as fallback
    highest_res = thumbnails[-1]  # Last thumbnail is usually highest resolution
    
    # Double-check for 336x188 resolution
    for thumb in thumbnails:
        if thumb.get('width') == 336 and thumb.get('height') == 188:
            return thumb['url']
    
    # Return the last thumbnail URL as fallback
    return highest_res['url']

def create_video_thumbnail_mapping(playlist_data):
    """Create mapping from video ID to highest resolution thumbnail URL"""
    mapping = {}
    
    if not playlist_data or 'entries' not in playlist_data:
        print("Error: Invalid playlist data structure")
        return mapping
    
    for entry in playlist_data['entries']:
        video_id = entry.get('id')
        thumbnails = entry.get('thumbnails', [])
        
        if video_id and thumbnails:
            thumbnail_url = get_highest_resolution_thumbnail(thumbnails)
            if thumbnail_url:
                mapping[video_id] = thumbnail_url
                print(f"Mapped {video_id} -> {thumbnail_url}")
    
    return mapping

def update_episodes_thumbnails(episodes_data, thumbnail_mapping):
    """Update episodes.json with YouTube thumbnail URLs"""
    if not episodes_data:
        return episodes_data
    
    updated_count = 0
    
    for date, episode_data in episodes_data.items():
        if 'en' in episode_data:
            episode = episode_data['en']
            video_id = episode.get('id')
            
            if video_id and video_id in thumbnail_mapping:
                old_thumbnail = episode.get('thumbnail', 'N/A')
                new_thumbnail = thumbnail_mapping[video_id]
                
                episode['thumbnail'] = new_thumbnail
                updated_count += 1
                
                print(f"Updated {date} ({video_id}): {old_thumbnail} -> {new_thumbnail}")
    
    print(f"\nTotal episodes updated: {updated_count}")
    return episodes_data

def main():
    # Load data files
    print("Loading playlist.json...")
    playlist_data = load_json_file('playlist.json')
    if not playlist_data:
        return
    
    print("\nLoading episodes.json...")
    episodes_data = load_json_file('episodes.json')
    if not episodes_data:
        return
    
    # Create video ID to thumbnail URL mapping
    print("\nCreating video ID to thumbnail URL mapping...")
    thumbnail_mapping = create_video_thumbnail_mapping(playlist_data)
    
    if not thumbnail_mapping:
        print("No thumbnail mapping created. Exiting.")
        return
    
    print(f"\nCreated mapping for {len(thumbnail_mapping)} videos.")
    
    # Update episodes with new thumbnails
    print("\nUpdating episodes with YouTube thumbnails...")
    updated_episodes = update_episodes_thumbnails(episodes_data, thumbnail_mapping)
    
    # Save updated episodes.json
    print("\nSaving updated episodes.json...")
    try:
        with open('episodes.json', 'w', encoding='utf-8') as f:
            json.dump(updated_episodes, f, indent=2, ensure_ascii=False)
        print("episodes.json updated successfully!")
    except Exception as e:
        print(f"Error saving episodes.json: {e}")
        return
    
    # Display summary
    print("\n=== SUMMARY ===")
    print(f"Total videos in playlist: {len(playlist_data.get('entries', []))}")
    print(f"Total thumbnail mappings created: {len(thumbnail_mapping)}")
    print(f"Total episodes in episodes.json: {len(episodes_data)}")
    
    # Show some example mappings
    print("\n=== EXAMPLE MAPPINGS ===")
    for i, (video_id, url) in enumerate(thumbnail_mapping.items()):
        if i < 5:  # Show first 5 mappings
            print(f"{video_id}: {url}")
        else:
            break

if __name__ == "__main__":
    main()