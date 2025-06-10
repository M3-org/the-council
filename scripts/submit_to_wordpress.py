import os
import csv
import json
import base64
import re
import requests
import mimetypes
import argparse

# --- Configuration ---
PLAYLIST_CSV = "playlist.csv"
PASSCODE = os.environ.get('WORDPRESS_PASSCODE')  # Replace with your actual passcode
API_ENDPOINT = "https://m3org.com/tv/wp-json/jedai-council/v1/submit-episode"
RECORDINGS_DIR = "recordings"
THUMBNAILS_DIR = "media/thumbnails"

def sanitize_for_filename(text):
    """Sanitizes a string to be part of a filename."""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9]', '-', text)
    text = re.sub(r'--+', '-', text)
    return text

def normalize_episode_id(episode_id):
    """Normalizes episode ID to remove leading zeros, e.g., S01E01 -> S1E1."""
    match = re.search(r'S([0-9]+)E([0-9]+)', episode_id, re.IGNORECASE)
    if not match:
        return None
    s_num = int(match.group(1))
    e_num = int(match.group(2))
    return f"S{s_num}E{e_num}"

def process_episodes(episodes_to_process=None, limit=None, dry_run=False):
    """Reads the playlist, prepares data, and submits each episode."""
    if not os.path.exists(PLAYLIST_CSV):
        print(f"❌ Error: Playlist file not found at {PLAYLIST_CSV}")
        return

    if dry_run:
        print("💧 NOTE: Running in --dry-run mode. No data will be submitted to WordPress.")

    processed_count = 0
    episodes_found = set()
    with open(PLAYLIST_CSV, mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row

        for row in reader:
            if not row: continue # Skip empty rows
            full_title, youtube_url = row
            full_title = full_title.strip()
            youtube_url = youtube_url.strip()

            # Extract S#E# from the title
            match = re.search(r'(S[0-9]+E[0-9]+)', full_title, re.IGNORECASE)
            if not match:
                # This row doesn't have a valid episode ID, so we can't process it.
                continue
            
            episode_id_from_title = match.group(1).upper()
            normalized_episode_id = normalize_episode_id(episode_id_from_title)

            # --- Filter based on CLI arguments ---
            if episodes_to_process and normalized_episode_id not in episodes_to_process:
                print(f"-> Skipping '{normalized_episode_id}': Not in the requested list.")
                continue # Skip if not in the list of episodes to process
            
            episodes_found.add(normalized_episode_id)
            print(f"🎬 Processing: {full_title}")

            # Extract the part of the title after "S#E#: "
            episode_name_part = re.sub(r'.*S[0-9]+E[0-9]+:\s*', '', full_title, flags=re.IGNORECASE)
            sanitized_name = sanitize_for_filename(episode_name_part)

            # Construct file paths
            episode_data_file = os.path.join(RECORDINGS_DIR, f"{episode_id_from_title}_JedAI-Council_{sanitized_name}_episode-data.json")
            thumbnail_file = os.path.join(THUMBNAILS_DIR, f"{normalized_episode_id}.jpg")

            # --- Read Episode Data ---
            if not os.path.exists(episode_data_file):
                print(f"   ❌ WARNING: Data file not found. Expected: {episode_data_file}")
                continue
            
            with open(episode_data_file, 'r', encoding='utf-8') as f:
                try:
                    episode_data = json.load(f)
                except json.JSONDecodeError:
                    print(f"   ❌ WARNING: Invalid JSON in '{episode_data_file}'. Skipping.")
                    continue
            
            # --- Prepare Payload ---
            submission_data = {
                "passcode": PASSCODE,
                "episode_data": episode_data,
                "youtube_url": youtube_url,
            }

            # --- Handle Featured Image ---
            if os.path.exists(thumbnail_file):
                try:
                    mime_type, _ = mimetypes.guess_type(thumbnail_file)
                    if not mime_type:
                        mime_type = 'image/jpeg' # Default
                    
                    with open(thumbnail_file, "rb") as image_file:
                        base64_content = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    data_url = f"data:{mime_type};base64,{base64_content}"
                    submission_data["featured_image"] = data_url
                    print(f"   🖼️  Found and encoded thumbnail: {thumbnail_file}")

                except Exception as e:
                    print(f"   ❌ WARNING: Could not process thumbnail {thumbnail_file}. Error: {e}")
            else:
                print(f"   ℹ️  NOTE: Thumbnail not found for {normalized_episode_id}. Submitting without featured image.")

            # --- Submit to WordPress ---
            if dry_run:
                print(f"   🌵 DRY RUN: Would submit '{episode_name_part}' to WordPress.")
                print(f"      Payload size: {len(json.dumps(submission_data)) / 1024:.1f} KB")
            else:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    print(f"   📡 Submitting '{episode_name_part}' to WordPress...")
                    response = requests.post(API_ENDPOINT, json=submission_data, headers=headers)
                    response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

                    response_data = response.json()
                    print(f"   ✅ Success! Post ID: {response_data.get('post_id')}, URL: {response_data.get('post_url')}")

                except requests.exceptions.HTTPError as errh:
                    print(f"   ❌ HTTP Error: {errh}")
                    print(f"      Response: {errh.response.text}")
                except requests.exceptions.ConnectionError as errc:
                    print(f"   ❌ Error Connecting: {errc}")
                except requests.exceptions.Timeout as errt:
                    print(f"   ❌ Timeout Error: {errt}")
                except requests.exceptions.RequestException as err:
                    print(f"   ❌ Oof: Something Else: {err}")
            
            print("-" * 20)

            processed_count += 1
            if limit and processed_count >= limit:
                print(f"🏃 Reached limit of {limit} episodes.")
                break

    # --- Final Summary ---
    if episodes_to_process:
        print("\n--- Summary ---")
        found_any = False
        for ep_id in episodes_to_process:
            if ep_id in episodes_found:
                print(f"✅ Found and processed: {ep_id}")
                found_any = True
            else:
                print(f"❌ Not found in {PLAYLIST_CSV}: {ep_id}")
        if not found_any:
            print(f"\nTip: Check if the episode IDs exist in '{PLAYLIST_CSV}' and are in the format 'S#E#'.")
        print("---------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit JedAI Council episodes to WordPress.")
    parser.add_argument(
        '--episodes',
        nargs='+',
        metavar='S#E#',
        help='One or more specific episode IDs to process (e.g., S1E1 S1E5). IDs are case-insensitive.'
    )
    parser.add_argument(
        '--limit',
        type=int,
        metavar='N',
        help='Limit the number of episodes to process from the CSV file.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Run the script without actually submitting data to WordPress. Useful for testing."
    )
    
    args = parser.parse_args()

    # Normalize episode IDs from command line arguments for case-insensitive matching
    episodes_arg = [normalize_episode_id(e) for e in args.episodes] if args.episodes else None

    process_episodes(episodes_to_process=episodes_arg, limit=args.limit, dry_run=args.dry_run)
    print("🚀 All episodes processed.") 