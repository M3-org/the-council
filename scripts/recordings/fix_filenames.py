#!/usr/bin/env python3
"""
Fix episode filenames to use correct dates from list.txt
"""

import os
import json
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
        if slug in file_path.name.lower():
            matching_files.append(file_path)
    
    return matching_files

def rename_files(files, slug, date_str):
    """Rename files to use correct date format"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = dt.strftime("%Y-%m-%dT04-15-00-000Z")
    
    for file_path in files:
        if file_path.name.startswith("S1E"):
            # Skip S1E files
            continue
            
        # Extract the episode name from the filename
        parts = file_path.name.split('_')
        if len(parts) >= 2:
            episode_name = '_'.join(parts[1:])
            
            # Replace the timestamp with the correct date
            old_timestamp_pattern = r'_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z'
            
            # Create new filename with correct date
            new_name = f"JedAI-Council_{episode_name.split('_')[0]}_{formatted_date}"
            
            # Add file extension
            if '.' in episode_name:
                extension = '.' + episode_name.split('.')[-1]
                new_name = new_name.replace(formatted_date, formatted_date.replace('.', '')) + extension
            
            # Handle different file types
            if file_path.suffix == '.json':
                if '_session-log.json' in file_path.name:
                    new_name = new_name.replace('.json', '_session-log.json')
                elif '_episode-data.json' in file_path.name:
                    new_name = new_name.replace('.json', '_episode-data.json')
                elif '_youtube-meta.json' in file_path.name:
                    new_name = new_name.replace('.json', '_youtube-meta.json')
            elif file_path.suffix == '.mp4' and 'fps30' in file_path.name:
                new_name = new_name.replace('.mp4', '_fps30.mp4')
            
            # Clean up the name
            new_name = new_name.replace('__', '_')
            new_path = file_path.parent / new_name
            
            if new_path != file_path and not new_path.exists():
                try:
                    file_path.rename(new_path)
                    print(f"Renamed: {file_path.name} → {new_name}")
                except Exception as e:
                    print(f"Error renaming {file_path.name}: {e}")
            else:
                print(f"Skipped: {file_path.name} (target exists or no change needed)")

def main():
    print("Loading episodes from list.txt...")
    episodes = load_list_episodes()
    print(f"Found {len(episodes)} episodes")
    
    matches_found = 0
    
    for slug, date_str in episodes.items():
        print(f"\nProcessing episode: {slug} (date: {date_str})")
        
        matching_files = find_matching_files(slug)
        
        if matching_files:
            print(f"Found {len(matching_files)} matching files")
            rename_files(matching_files, slug, date_str)
            matches_found += 1
        else:
            print("  No matching files found")
    
    print(f"\nDone! Processed {matches_found} episodes out of {len(episodes)} total.")

if __name__ == "__main__":
    main()