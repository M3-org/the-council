#!/usr/bin/env python3
"""
Fix specific date mismatches for episodes that don't have exact slug matches
"""

from pathlib import Path

def main():
    recordings_dir = Path("recordings")
    
    # Manual mappings for episodes that need date corrections
    corrections = {
        # Current wrong date -> correct date mapping
        "2025-07-11_JedAI-Council_The-A2A-Network--Agents-of-Change": "2025-06-28_JedAI-Council_The-A2A-Network--Agents-of-Change",
        "2025-07-11_JedAI-Council_The-Oracle-s-Dilemma": "2025-07-02_JedAI-Council_The-Oracle-s-Dilemma", 
        "2025-07-11_JedAI-Council_The-Philosopher-s-Token": "2025-07-04_JedAI-Council_The-Philosopher-s-Token",
        "2025-07-11_JedAI-Council_The-Web3-Philosopher-s-Stone": "2025-07-03_JedAI-Council_The-Web3-Philosopher-s-Stone",
        "2025-07-11_JedAI-Council_Twitter-Suspended--Memes-Upended": "2025-06-15_JedAI-Council_Twitter-Suspended--Memes-Upended",
        "2025-07-11_JedAI-Council_Twitter-s-API-Apocalypse": "2025-06-18_JedAI-Council_Twitter-s-API-Apocalypse",
    }
    
    total_renamed = 0
    
    print("Fixing specific date mismatches...")
    
    for file_path in recordings_dir.glob("*"):
        if not file_path.is_file():
            continue
            
        filename = file_path.name
        
        # Check if this file matches any of our correction patterns
        for wrong_pattern, correct_pattern in corrections.items():
            if filename.startswith(wrong_pattern):
                # Get the file extension/suffix part
                suffix = filename[len(wrong_pattern):]
                new_filename = correct_pattern + suffix
                new_path = recordings_dir / new_filename
                
                if new_path.exists():
                    print(f"Skipped: {filename} (target exists)")
                    continue
                
                try:
                    file_path.rename(new_path)
                    print(f"Renamed: {filename} → {new_filename}")
                    total_renamed += 1
                except Exception as e:
                    print(f"Error renaming {filename}: {e}")
                
                break  # Move to next file
    
    print(f"\\nDone! Renamed {total_renamed} files total.")

if __name__ == "__main__":
    main()