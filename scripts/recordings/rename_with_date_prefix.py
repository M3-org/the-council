#!/usr/bin/env python3
"""
Rename files to have date prefix: YYYY-MM-DD_JedAI-Council_title_type.ext
"""

import re
from pathlib import Path

def extract_date_from_filename(filename):
    """Extract date from filename timestamp"""
    # Look for pattern like 2025-06-11T04-15-00-000Z
    match = re.search(r'(\d{4}-\d{2}-\d{2})T\d{2}-\d{2}-\d{2}-\d{3}Z', filename)
    if match:
        return match.group(1)
    return None

def rename_file_with_date_prefix(file_path):
    """Rename file to have date prefix"""
    filename = file_path.name
    
    # Skip S1E files
    if filename.startswith('S1E'):
        return False
    
    # Extract date
    date = extract_date_from_filename(filename)
    if not date:
        return False
    
    # Remove the timestamp part from the filename
    # Pattern: JedAI-Council_Title_2025-06-11T04-15-00-000Z_type.ext
    timestamp_pattern = r'_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z'
    
    # Replace the timestamp with empty string
    new_name = re.sub(timestamp_pattern, '', filename)
    
    # Add date prefix
    new_name = f"{date}_{new_name}"
    
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
    recordings_dir = Path("recordings")
    
    if not recordings_dir.exists():
        print("Error: recordings directory not found")
        return
    
    print("Renaming files to add date prefix...")
    
    total_renamed = 0
    
    # Get all files and sort them
    files = list(recordings_dir.glob("*"))
    files.sort()
    
    for file_path in files:
        if file_path.is_file():
            if rename_file_with_date_prefix(file_path):
                total_renamed += 1
    
    print(f"\nDone! Renamed {total_renamed} files total.")

if __name__ == "__main__":
    main()