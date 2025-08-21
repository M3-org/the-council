#!/usr/bin/env python3
"""
Fix the remaining incorrectly dated files
"""

from pathlib import Path

def main():
    recordings_dir = Path("recordings")
    
    # Files that need to be moved to correct dates
    corrections = [
        # The-Twitter-Suspension-Crisis files should be 2025-07-08 not 2025-07-11
        {
            "pattern": "2025-07-11_JedAI-Council_The-Twitter-Suspension-Crisis",
            "correct_date": "2025-07-08"
        },
        # Treasury-Trials-and-Silent-Releases files should be 2025-06-24 not 2025-07-11
        {
            "pattern": "2025-07-11_JedAI-Council_Treasury-Trials-and-Silent-Releases",
            "correct_date": "2025-06-24"
        }
    ]
    
    total_renamed = 0
    
    print("Fixing remaining date mismatches...")
    
    for file_path in recordings_dir.glob("*"):
        if not file_path.is_file():
            continue
            
        filename = file_path.name
        
        for correction in corrections:
            pattern = correction["pattern"]
            correct_date = correction["correct_date"]
            
            if filename.startswith(pattern):
                # Extract the suffix (file type and extension)
                suffix = filename[len(pattern):]
                
                # Create new filename with correct date
                new_filename = f"{correct_date}_JedAI-Council_{pattern.split('_', 2)[2]}{suffix}"
                new_path = recordings_dir / new_filename
                
                if new_path.exists():
                    print(f"Skipped: {filename} (target already exists: {new_filename})")
                    continue
                
                try:
                    file_path.rename(new_path)
                    print(f"Renamed: {filename} → {new_filename}")
                    total_renamed += 1
                except Exception as e:
                    print(f"Error renaming {filename}: {e}")
                
                break  # Move to next file
    
    print(f"\nDone! Renamed {total_renamed} files total.")
    
    # Show final verification
    print("\nVerification - checking for remaining 2025-07-11 files that should be moved:")
    july_11_files = list(recordings_dir.glob("2025-07-11*"))
    if july_11_files:
        print("Remaining 2025-07-11 files:")
        for f in july_11_files:
            print(f"  {f.name}")
    else:
        print("✅ No incorrectly dated 2025-07-11 files remaining")

if __name__ == "__main__":
    main()