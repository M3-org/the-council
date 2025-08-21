#!/usr/bin/env python3
"""
Fix episode file dates and JSON timestamps based on list.txt

This script:
1. Reads the date mappings from list.txt
2. Matches episode URLs to recording files
3. Updates file timestamps
4. Updates JSON timestamps in episode data and session logs
"""

import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import subprocess

def load_date_mappings(list_file):
    """Load date mappings from list.txt"""
    mappings = {}
    with open(list_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
            date_str, url = line.split(',', 1)
            # Extract episode slug from URL
            slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
            mappings[slug] = date_str
    return mappings

def extract_episode_id_from_filename(filename):
    """Extract episode ID from filename (e.g., S1E14)"""
    # For files like S1E14_JedAI-Council_the-wisdom-of-transitions.webm
    # We want to get "S1E14"
    parts = filename.split('_')
    if len(parts) >= 1:
        episode_id = parts[0]
        # Validate it's in the format S1E##
        if re.match(r'S\d+E\d+', episode_id):
            return episode_id
    return None

def create_episode_id_to_date_mapping(date_mappings, recordings_dir):
    """Create mapping from episode IDs to dates based on URL order"""
    # First, get all existing episode IDs from the JSON files (not filenames)
    existing_episode_ids = []
    for file_path in Path(recordings_dir).glob("*_episode-data.json"):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                episode_id = data.get('id')
                if episode_id and episode_id not in existing_episode_ids:
                    existing_episode_ids.append(episode_id)
        except:
            continue
    
    # Sort episode IDs to ensure consistent mapping
    existing_episode_ids.sort(key=lambda x: int(x.replace('S1E', '')))
    
    print(f"Found existing episode IDs: {existing_episode_ids}")
    
    # Map the first N dates to the existing episode IDs
    episode_id_mapping = {}
    date_list = sorted(date_mappings.items())  # Sort by date
    
    for i, episode_id in enumerate(existing_episode_ids):
        if i < len(date_list):
            _, date = date_list[i]
            episode_id_mapping[episode_id] = date
    
    return episode_id_mapping

def find_matching_episodes(recordings_dir, episode_id_mapping):
    """Find which recording files match which dates by episode ID"""
    matches = {}
    
    for file_path in Path(recordings_dir).glob("*"):
        if file_path.is_file():
            # For episode data files, use the ID from the JSON content
            if file_path.name.endswith('_episode-data.json'):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        episode_id = data.get('id')
                        if episode_id and episode_id in episode_id_mapping:
                            episode_date = episode_id_mapping[episode_id]
                            if episode_date not in matches:
                                matches[episode_date] = []
                            matches[episode_date].append(file_path)
                except:
                    continue
            else:
                # For other files, use the filename episode ID
                episode_id = extract_episode_id_from_filename(file_path.name)
                if episode_id and episode_id in episode_id_mapping:
                    episode_date = episode_id_mapping[episode_id]
                    if episode_date not in matches:
                        matches[episode_date] = []
                    matches[episode_date].append(file_path)
    
    return matches

def update_file_timestamp(file_path, date_str):
    """Update file modification time to match the episode date"""
    # Set time to 4:15 AM (matching cron job time)
    dt = datetime.strptime(f"{date_str} 04:15:00", "%Y-%m-%d %H:%M:%S")
    timestamp = dt.timestamp()
    
    os.utime(file_path, (timestamp, timestamp))
    print(f"Updated {file_path.name} timestamp to {date_str} 04:15:00")

def update_json_timestamps(json_file, date_str):
    """Update timestamps in JSON files"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Create datetime at 4:15 AM for the episode date
        dt = datetime.strptime(f"{date_str} 04:15:00", "%Y-%m-%d %H:%M:%S")
        dt_utc = dt.replace(tzinfo=timezone.utc)
        iso_timestamp = dt_utc.isoformat()
        
        updated = False
        
        # Update various timestamp fields that might exist
        timestamp_fields = [
            'recorded_at',
            'created_at', 
            'timestamp',
            'date',
            'recording_started_at',
            'recording_ended_at'
        ]
        
        for field in timestamp_fields:
            if field in data:
                data[field] = iso_timestamp
                updated = True
        
        # For session logs, also update event timeline timestamps
        if 'event_timeline' in data:
            for event in data['event_timeline']:
                if 'timestamp' in event:
                    event['timestamp'] = iso_timestamp
                    updated = True
        
        if updated:
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Updated JSON timestamps in {json_file.name}")
        
    except Exception as e:
        print(f"Error updating {json_file}: {e}")

def main():
    recordings_dir = Path("recordings")
    list_file = Path("list.txt")
    
    if not list_file.exists():
        print("Error: list.txt not found")
        return
    
    if not recordings_dir.exists():
        print("Error: recordings directory not found")
        return
    
    print("Loading date mappings...")
    date_mappings = load_date_mappings(list_file)
    print(f"Found {len(date_mappings)} date mappings")
    
    print("Creating episode ID to date mapping...")
    episode_id_mapping = create_episode_id_to_date_mapping(date_mappings, recordings_dir)
    print(f"Created {len(episode_id_mapping)} episode ID mappings")
    
    print("Finding matching episodes...")
    matches = find_matching_episodes(recordings_dir, episode_id_mapping)
    print(f"Found {len(matches)} episode dates with files")
    
    print("\nProcessing files...")
    for episode_date, files in matches.items():
        print(f"\nProcessing episode for {episode_date}:")
        for file_path in files:
            print(f"  - {file_path.name}")
            
            # Update file timestamp
            update_file_timestamp(file_path, episode_date)
            
            # Update JSON timestamps for JSON files
            if file_path.suffix == '.json':
                update_json_timestamps(file_path, episode_date)
    
    print("\nDone! File timestamps and JSON data updated.")

if __name__ == "__main__":
    main()