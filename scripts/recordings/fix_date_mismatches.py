#!/usr/bin/env python3
"""
Fix date mismatches in recordings directory based on list.txt
"""

import re
from pathlib import Path

def load_list_episodes():
    """Load episodes from list.txt with correct dates"""
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

def extract_title_from_filename(filename):
    """Extract the episode title from filename"""
    # Remove date prefix and JedAI-Council prefix
    # From: 2025-06-11_JedAI-Council_The-Knowledge-Plugin-Conundrum_episode-data.json
    # To: The-Knowledge-Plugin-Conundrum
    
    # Remove file extension and type suffix
    base_name = filename
    for suffix in ['_episode-data.json', '_session-log.json', '_fps30.mp4', '.webm', '.mp4', '.json']:
        if base_name.endswith(suffix):
            base_name = base_name[:-len(suffix)]
            break
    
    # Split by underscores and get the title part
    parts = base_name.split('_')
    if len(parts) >= 3:
        return '_'.join(parts[2:])  # Skip date and JedAI-Council
    return None

def find_correct_date_for_title(title, episodes_map):
    """Find the correct date for an episode title"""
    # Convert title to slug format for matching
    title_slug = title.lower().replace('_', '-')
    
    # Look for exact match first
    for slug, date in episodes_map.items():
        if slug == title_slug:
            return date
    
    # Look for partial matches
    for slug, date in episodes_map.items():
        if slug in title_slug or title_slug in slug:
            return date
    
    return None

def rename_file_with_correct_date(file_path, correct_date):
    """Rename file with the correct date"""
    filename = file_path.name
    
    # Extract current date from filename
    current_date_match = re.match(r'(\d{4}-\d{2}-\d{2})_(.+)', filename)
    if not current_date_match:
        return False
    
    current_date = current_date_match.group(1)
    rest_of_filename = current_date_match.group(2)
    
    if current_date == correct_date:
        return False  # Already correct
    
    new_filename = f"{correct_date}_{rest_of_filename}"
    new_path = file_path.parent / new_filename
    
    if new_path.exists():
        print(f"Skipped: {filename} (target exists: {new_filename})")
        return False
    
    try:
        file_path.rename(new_path)
        print(f"Renamed: {filename} → {new_filename}")
        return True
    except Exception as e:
        print(f"Error renaming {filename}: {e}")
        return False

def main():
    recordings_dir = Path("recordings")
    
    if not recordings_dir.exists():
        print("Error: recordings directory not found")
        return
    
    print("Loading episodes from list.txt...")
    episodes_map = load_list_episodes()
    print(f"Found {len(episodes_map)} episodes in list.txt")
    
    # Find all files with date prefix format
    date_prefixed_files = []
    for file_path in recordings_dir.glob("*"):
        if file_path.is_file() and re.match(r'\d{4}-\d{2}-\d{2}_', file_path.name):
            date_prefixed_files.append(file_path)
    
    print(f"Found {len(date_prefixed_files)} date-prefixed files")
    
    total_renamed = 0
    processed_titles = set()
    
    for file_path in date_prefixed_files:
        title = extract_title_from_filename(file_path.name)
        if not title:
            continue
        
        # Skip if we've already processed this title
        if title in processed_titles:
            continue
        
        correct_date = find_correct_date_for_title(title, episodes_map)
        if not correct_date:
            print(f"No matching date found for title: {title}")
            continue
        
        # Find all files with this title
        title_files = []
        for f in date_prefixed_files:
            if title in f.name:
                title_files.append(f)
        
        if title_files:
            print(f"\\nProcessing title: {title} -> {correct_date}")
            for title_file in title_files:
                if rename_file_with_correct_date(title_file, correct_date):
                    total_renamed += 1
            processed_titles.add(title)
    
    print(f"\\nDone! Renamed {total_renamed} files total.")

if __name__ == "__main__":
    main()