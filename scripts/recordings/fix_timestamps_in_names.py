#!/usr/bin/env python3
"""
Fix timestamps in episode filenames to match correct dates from list.txt
"""

import os
import re
from datetime import datetime
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

def find_matching_files(slug):
    """Find recording files that match the episode slug"""
    recordings_dir = Path("recordings")
    matching_files = []
    
    for file_path in recordings_dir.glob("*"):
        if slug in file_path.name.lower() and not file_path.name.startswith("S1E"):
            matching_files.append(file_path)
    
    return matching_files

def fix_filename_timestamp(file_path, date_str):
    """Fix the timestamp in the filename"""
    # Convert date to the format used in filenames: YYYY-MM-DDTHH-MM-SS-SSSZ
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    new_timestamp = dt.strftime("%Y-%m-%dT04-15-00-000Z")
    
    # Find the existing timestamp pattern in the filename
    timestamp_pattern = r'_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z'
    
    old_name = file_path.name
    
    # Replace the timestamp
    new_name = re.sub(timestamp_pattern, f'_{new_timestamp}', old_name)
    
    if new_name != old_name:
        new_path = file_path.parent / new_name
        
        if not new_path.exists():
            try:
                file_path.rename(new_path)
                print(f"Renamed: {old_name} → {new_name}")
                return True
            except Exception as e:
                print(f"Error renaming {old_name}: {e}")
                return False
        else:
            print(f"Skipped: {old_name} (target exists)")
            return False
    else:
        print(f"No change needed: {old_name}")
        return False

def main():
    print("Loading episodes from list.txt...")
    episodes = load_list_episodes()
    print(f"Found {len(episodes)} episodes")
    
    total_renamed = 0
    
    for slug, date_str in episodes.items():
        print(f"\nProcessing episode: {slug} (date: {date_str})")
        
        matching_files = find_matching_files(slug)
        
        if matching_files:
            print(f"Found {len(matching_files)} matching files")
            for file_path in matching_files:
                if fix_filename_timestamp(file_path, date_str):
                    total_renamed += 1
        else:
            print("  No matching files found")
    
    print(f"\nDone! Renamed {total_renamed} files total.")

if __name__ == "__main__":
    main()