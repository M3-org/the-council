#!/usr/bin/env python3
"""
Rename MP4 files to match the date prefix format for episodes in list.txt only
"""

import re
from pathlib import Path

def load_list_episodes():
    """Load episodes from list.txt"""
    episodes = {}
    with open('list.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
            date_str, url = line.split(',', 1)
            slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
            episodes[slug] = date_str
    return episodes

def find_matching_mp4_files(slug):
    """Find MP4 files that match the episode slug"""
    recordings_dir = Path("recordings")
    matching_files = []
    
    for file_path in recordings_dir.glob("*.mp4"):
        # Skip S1E files
        if file_path.name.startswith("S1E"):
            continue
            
        # Check if slug matches the filename
        if slug in file_path.name.lower():
            matching_files.append(file_path)
    
    return matching_files

def rename_mp4_to_date_prefix(file_path, date_str):
    """Rename MP4 file to use date prefix format"""
    filename = file_path.name
    
    # Extract the episode title and type from current filename
    # Current format might be: JedAI-Council_Title_2025-XX-XXTXX-XX-XX-XXXZ_fps30.mp4
    # Or: 2025-XX-XX_JedAI-Council_Title_fps30.mp4
    
    if filename.startswith("2025-"):
        # Already has date prefix, no need to change
        return False
    
    # Extract date from timestamp if present
    timestamp_match = re.search(r'_(\d{4}-\d{2}-\d{2})T\d{2}-\d{2}-\d{2}-\d{3}Z', filename)
    if timestamp_match:
        # Remove the timestamp part
        new_name = re.sub(r'_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z', '', filename)
    else:
        # No timestamp, use as is
        new_name = filename
    
    # Add date prefix
    new_name = f"{date_str}_{new_name}"
    
    new_path = file_path.parent / new_name
    
    if new_path != file_path and not new_path.exists():
        try:
            file_path.rename(new_path)
            print(f"Renamed: {filename} → {new_name}")
            return True
        except Exception as e:
            print(f"Error renaming {filename}: {e}")
            return False
    else:
        print(f"Skipped: {filename} (no change needed or target exists)")
        return False

def main():
    print("Loading episodes from list.txt...")
    episodes = load_list_episodes()
    print(f"Found {len(episodes)} episodes")
    
    total_renamed = 0
    
    for slug, date_str in episodes.items():
        print(f"\nProcessing episode: {slug} (date: {date_str})")
        
        matching_files = find_matching_mp4_files(slug)
        
        if matching_files:
            print(f"Found {len(matching_files)} matching MP4 files")
            for file_path in matching_files:
                if rename_mp4_to_date_prefix(file_path, date_str):
                    total_renamed += 1
        else:
            print("  No matching MP4 files found")
    
    print(f"\nDone! Renamed {total_renamed} MP4 files total.")

if __name__ == "__main__":
    main()