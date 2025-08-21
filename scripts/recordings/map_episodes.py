#!/usr/bin/env python3
"""
Map list.txt episodes to actual recording files and update dates
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path

def load_list_episodes():
    """Load episodes from list.txt"""
    episodes = []
    with open('list.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
            date_str, url = line.split(',', 1)
            slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
            episodes.append((date_str, slug))
    return episodes

def find_matching_files(slug):
    """Find recording files that match the episode slug"""
    recordings_dir = Path("recordings")
    matching_files = []
    
    # Look for files with the slug in the name
    for file_path in recordings_dir.glob("*"):
        if slug in file_path.name.lower():
            matching_files.append(file_path)
    
    return matching_files

def update_timestamps(files, date_str):
    """Update file timestamps and JSON data"""
    dt = datetime.strptime(f"{date_str} 04:15:00", "%Y-%m-%d %H:%M:%S")
    timestamp = dt.timestamp()
    dt_utc = dt.replace(tzinfo=timezone.utc)
    iso_timestamp = dt_utc.isoformat()
    
    for file_path in files:
        # Update file timestamp
        os.utime(file_path, (timestamp, timestamp))
        print(f"Updated {file_path.name} timestamp to {date_str} 04:15:00")
        
        # Update JSON timestamps if it's a JSON file
        if file_path.suffix == '.json':
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                updated = False
                timestamp_fields = ['recorded_at', 'created_at', 'timestamp', 'date', 'recording_started_at', 'recording_ended_at']
                
                for field in timestamp_fields:
                    if field in data:
                        data[field] = iso_timestamp
                        updated = True
                
                # Update event timeline timestamps
                if 'event_timeline' in data:
                    for event in data['event_timeline']:
                        if 'timestamp' in event:
                            event['timestamp'] = iso_timestamp
                            updated = True
                
                if updated:
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"Updated JSON timestamps in {file_path.name}")
                    
            except Exception as e:
                print(f"Error updating {file_path}: {e}")

def main():
    print("Loading episodes from list.txt...")
    episodes = load_list_episodes()
    print(f"Found {len(episodes)} episodes")
    
    matches_found = 0
    
    for date_str, slug in episodes:
        print(f"\nLooking for episode: {slug} (date: {date_str})")
        
        matching_files = find_matching_files(slug)
        
        if matching_files:
            print(f"Found {len(matching_files)} matching files:")
            for file_path in matching_files:
                print(f"  - {file_path.name}")
            
            update_timestamps(matching_files, date_str)
            matches_found += 1
        else:
            print("  No matching files found")
    
    print(f"\nDone! Updated {matches_found} episodes out of {len(episodes)} total.")

if __name__ == "__main__":
    main()