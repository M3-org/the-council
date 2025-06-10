#!/usr/bin/env python3
"""
Record and Publish JedAI Council Episodes

This script replaces the GitHub Actions workflow with a more robust Python implementation.
It fetches the latest episode, records it, prepares metadata, and publishes to YouTube.

Usage Examples:
  # Full recording and publishing workflow:
  python record-and-publish.py

  # Test run without uploading:
  python record-and-publish.py --dry-run

  # Skip recording and use latest files:
  python record-and-publish.py --skip-recording

  # Record specific episode:
  python record-and-publish.py --episode-url "https://jedaicouncil.com/..."

  # Skip YouTube but do WordPress:
  python record-and-publish.py --skip-youtube

  # Clean up large files after completion:
  python record-and-publish.py --cleanup

  # Update thumbnail for existing video:
  python record-and-publish.py --update-thumbnail-for VIDEO_ID --thumbnail-file path/to/thumbnail.jpg

  # Record with custom thumbnail:
  python record-and-publish.py --thumbnail-file path/to/thumbnail.jpg

  # Update specific WordPress post:
  # python record-and-publish.py --update-wordpress-post POST_ID --episode-id S1E15 [--youtube-url URL]

  # Update WordPress with latest local files:
  # python record-and-publish.py --skip-recording --update-wordpress-post POST_ID

Required Environment Variables for Full Functionality:
  - YOUTUBE_CLIENT_ID: YouTube API client ID
  - YOUTUBE_CLIENT_SECRET: YouTube API client secret
  - YOUTUBE_REFRESH_TOKEN: YouTube API refresh token
  - WORDPRESS_PASSCODE: WordPress API passcode

The script will gracefully skip steps if credentials are missing.
"""

import os
import sys
import json
import subprocess
import requests
import time
import argparse
import re
from pathlib import Path
from datetime import datetime
import glob

# Configuration
SHOW_ID = 2578
API_URL = "https://shmotime.com/wp-json/shmotime/v1/get-latest-episode"
YOUTUBE_PLAYLIST_ID = "PLp5K4ceh2pR0-rg8WPuFnlLTsreQ7HOQx"
RECORDINGS_DIR = Path("recordings")

class RecordAndPublishError(Exception):
    """Custom exception for record and publish operations"""
    pass

def log(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def fetch_latest_episode():
    """Fetch the latest episode URL from the API"""
    log("Fetching latest episode URL from API...")
    
    try:
        response = requests.get(f"{API_URL}?show_id={SHOW_ID}")
        response.raise_for_status()
        data = response.json()
        
        episode_url = data.get('episode', {}).get('permalink')
        if not episode_url:
            raise RecordAndPublishError("No episode URL found in API response")
        
        log(f"Found episode URL: {episode_url}")
        return episode_url
        
    except requests.RequestException as e:
        raise RecordAndPublishError(f"Failed to fetch episode URL: {e}")
    except json.JSONDecodeError as e:
        raise RecordAndPublishError(f"Invalid JSON response from API: {e}")

def run_command(cmd, cwd=None, capture_output=True):
    """Run a shell command and return the result"""
    log(f"Running command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=True,
            shell=isinstance(cmd, str)
        )
        return result
    except subprocess.CalledProcessError as e:
        log(f"Command failed with exit code {e.returncode}", "ERROR")
        if e.stdout:
            log(f"STDOUT: {e.stdout}", "ERROR")
        if e.stderr:
            log(f"STDERR: {e.stderr}", "ERROR")
        raise RecordAndPublishError(f"Command failed: {e}")

def sanitize_filename(text):
    """Convert text to filename-safe format"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    text = text.lower().strip()
    text = re.sub(r'[^a-zA-Z0-9\s-]', '', text)  # Remove special chars except spaces and hyphens
    text = re.sub(r'\s+', '-', text)  # Replace spaces with hyphens
    text = re.sub(r'-+', '-', text)  # Replace multiple hyphens with single
    text = text.strip('-')  # Remove leading/trailing hyphens
    return text

def rename_timestamp_files_to_episode_format(episode_id, episode_title, recordings_dir=RECORDINGS_DIR):
    """Rename timestamp-based files to proper episode naming format"""
    if not episode_id or not episode_title:
        log("Cannot rename files: missing episode ID or title", "WARNING")
        return {}
    
    clean_title = sanitize_filename(episode_title)
    expected_prefix = f"{episode_id}_JedAI-Council_{clean_title}"
    
    # Find timestamp-based files that need renaming
    timestamp_pattern = re.compile(r'JedAI-Council_.*_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z')
    files_to_rename = {}
    
    for file_path in recordings_dir.glob("*"):
        if timestamp_pattern.search(file_path.name):
            # Determine the file type and new name
            if file_path.suffix == ".mp4" and "fps30" in file_path.name:
                new_name = f"{expected_prefix}_fps30.mp4"
            elif file_path.suffix == ".webm":
                new_name = f"{expected_prefix}.webm"
            elif file_path.name.endswith("_session-log.json"):
                new_name = f"{expected_prefix}_session-log.json"
            elif file_path.name.endswith("_episode-data.json"):
                new_name = f"{expected_prefix}_episode-data.json"
            elif file_path.name.endswith("_youtube-meta.json"):
                new_name = f"{expected_prefix}_youtube-meta.json"
            else:
                continue  # Skip unknown file types
            
            new_path = recordings_dir / new_name
            
            # Only rename if the target doesn't exist
            if not new_path.exists():
                try:
                    file_path.rename(new_path)
                    log(f"Renamed: {file_path.name} → {new_name}")
                    files_to_rename[file_path.name] = new_path
                except Exception as e:
                    log(f"Failed to rename {file_path.name}: {e}", "WARNING")
            else:
                log(f"Target file already exists, skipping rename: {new_name}", "WARNING")
    
    return files_to_rename

def extract_episode_title_from_session_log(session_log_path):
    """Extract episode title from session log file"""
    try:
        with open(session_log_path, 'r') as f:
            session_data = json.load(f)
        
        # Look for load_episode event in the event timeline
        event_timeline = session_data.get('event_timeline', [])
        for event in event_timeline:
            if event.get('type') == 'load_episode' and event.get('data'):
                # Check for 'name' field first (this is where the episode title is stored)
                episode_title = event['data'].get('name', '')
                if episode_title:
                    return episode_title
                # Fallback to 'title' field
                episode_title = event['data'].get('title', '')
                if episode_title:
                    return episode_title
        
        # Fallback: check if episode_data has title
        episode_data = session_data.get('episode_data', {})
        if episode_data.get('name'):
            return episode_data['name']
            
        return None
        
    except Exception as e:
        log(f"Could not extract title from session log: {e}", "WARNING")
        return None

def find_latest_file(pattern, directory=RECORDINGS_DIR):
    """Find the most recently created file matching the pattern, preferring episode-named files"""
    files = list(Path(directory).glob(pattern))
    
    if not files:
        return None
    
    # Separate episode-named files from timestamp-based files
    episode_files = []
    timestamp_files = []
    
    for file in files:
        # Episode files follow pattern: S1E##_JedAI-Council_title
        # Timestamp files follow pattern: JedAI-Council_Title_YYYY-MM-DDTHH-MM-SS-SSSZ
        if re.match(r'S\d+E\d+_JedAI-Council', file.name):
            episode_files.append(file)
        else:
            timestamp_files.append(file)
    
    # Prefer episode-named files, then fall back to timestamp files
    preferred_files = episode_files if episode_files else timestamp_files
    
    if not preferred_files:
        return None
    
    # Sort by modification time, most recent first
    preferred_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    latest_file = preferred_files[0]
    
    file_type = "episode-named" if latest_file in episode_files else "timestamp-based"
    log(f"Found latest {pattern} ({file_type}): {latest_file}")
    return latest_file

def record_episode(episode_url, headless=True, mute=True):
    """Record the episode using the Node.js recorder"""
    log(f"Recording episode from: {episode_url}")
    
    # Build recorder command
    cmd = [
        "node", "scripts/recorder.js",
        "--video-width=1920",
        "--video-height=1080", 
        "--stop-recording-at=end_postcredits",
        episode_url
    ]
    
    if headless:
        cmd.insert(2, "--headless")
    if mute:
        cmd.insert(2, "--mute")
    
    # Add verbose logging to help debug filename issues
    if not any("--quiet" in str(arg) for arg in cmd):
        # Remove --quiet if present and ensure verbose output
        cmd = [arg for arg in cmd if "--quiet" not in str(arg)]
    
    # Record start time to help find new files
    start_time = time.time()
    
    # Run the recorder
    result = run_command(cmd, capture_output=False)
    
    # Find the generated files (look for files created after recording started)
    log("Finding generated files...")
    
    # Wait a moment for file system to settle
    time.sleep(2)
    
    # Find files more accurately by checking creation time
    video_file = None
    session_log = None
    episode_data_file = None
    
    # Look for files created after recording started
    new_files = []
    for file_path in RECORDINGS_DIR.glob("*"):
        if file_path.stat().st_mtime > start_time:
            new_files.append(file_path)
    
    # Separate new files by type and preference (episode-named vs timestamp-based)
    new_video_files = [f for f in new_files if f.suffix == ".mp4" and "fps30" in f.name]
    new_session_logs = [f for f in new_files if f.name.endswith("_session-log.json")]
    new_episode_data = [f for f in new_files if f.name.endswith("_episode-data.json")]
    
    # Apply preference for episode-named files
    def prefer_episode_named(files):
        if not files:
            return None
        episode_files = [f for f in files if re.match(r'S\d+E\d+_JedAI-Council', f.name)]
        return episode_files[0] if episode_files else files[0]
    
    video_file = prefer_episode_named(new_video_files)
    session_log = prefer_episode_named(new_session_logs)
    episode_data_file = prefer_episode_named(new_episode_data)
    
    # Fallback to latest files if time-based search fails
    if not video_file:
        video_file = find_latest_file("*.mp4")
    if not session_log:
        session_log = find_latest_file("*_session-log.json")
    if not episode_data_file:
        episode_data_file = find_latest_file("*_episode-data.json")
    
    # Validate we found all required files
    if not session_log or not episode_data_file:
        raise RecordAndPublishError("Could not find required recording files")
    
    # Extract episode ID and debug episode data
    try:
        with open(episode_data_file, 'r') as f:
            episode_data = json.load(f)
        episode_id = episode_data.get('id', 'Unknown')
        episode_name = episode_data.get('name', '')
        
        # If episode name is empty, try to extract it from session log
        if not episode_name and session_log:
            episode_name = extract_episode_title_from_session_log(session_log)
            if episode_name:
                log(f"Extracted episode title from session log: '{episode_name}'")
                # Update the episode data file with the correct name
                episode_data['name'] = episode_name
                with open(episode_data_file, 'w') as f:
                    json.dump(episode_data, f, indent=2)
                log("Updated episode data file with extracted title")
                
                # Also update the session log's episode_data section
                try:
                    with open(session_log, 'r') as f:
                        session_data = json.load(f)
                    if 'episode_data' in session_data:
                        session_data['episode_data']['name'] = episode_name
                        with open(session_log, 'w') as f:
                            json.dump(session_data, f, indent=2)
                        log("Updated session log episode_data with extracted title")
                    else:
                        log("Session log missing episode_data section", "WARNING")
                except Exception as e:
                    log(f"Could not update session log: {e}", "WARNING")
        
        # Debug info about episode data
        log(f"Episode data loaded: ID='{episode_id}', Name='{episode_name}'")
        if not episode_name:
            log("WARNING: Episode name is still empty after extraction attempts", "WARNING")
            
    except Exception as e:
        raise RecordAndPublishError(f"Could not read episode data: {e}")
    
    log(f"Recording complete for episode {episode_id}")
    log(f"Video file: {video_file}")
    log(f"Session log: {session_log}")
    log(f"Episode data: {episode_data_file}")
    
    # Check if filenames follow expected pattern and rename if needed
    if video_file and episode_id != 'Unknown':
        expected_prefix = f"{episode_id}_JedAI-Council"
        if expected_prefix not in str(video_file):
            log(f"WARNING: Video filename doesn't match expected pattern. Expected: {expected_prefix}_*, Got: {video_file.name}", "WARNING")
            
            # Try to rename timestamp-based files to proper format
            if episode_name:
                log("Attempting to rename timestamp-based files to proper episode format...")
                renamed_files = rename_timestamp_files_to_episode_format(episode_id, episode_name)
                
                # Update file references if they were renamed
                for old_name, new_path in renamed_files.items():
                    if video_file and old_name == video_file.name:
                        video_file = new_path
                        log(f"Updated video file reference: {new_path}")
                    elif session_log and old_name == session_log.name:
                        session_log = new_path
                        log(f"Updated session log reference: {new_path}")
                    elif episode_data_file and old_name == episode_data_file.name:
                        episode_data_file = new_path
                        log(f"Updated episode data reference: {new_path}")
    
    return {
        'video_file': video_file,
        'session_log': session_log,
        'episode_data_file': episode_data_file,
        'episode_id': episode_id
    }

def prepare_youtube_metadata(session_log_path, video_file_path=None, playlist_id=YOUTUBE_PLAYLIST_ID, thumbnail_file=None):
    """Prepare YouTube metadata using the existing script"""
    log("Preparing YouTube metadata...")
    
    cmd = [
        "python", "scripts/prepare_youtube_metadata.py",
        str(session_log_path),
        playlist_id
    ]
    
    run_command(cmd)
    
    # Find the generated metadata file
    base_name = session_log_path.stem.replace('_session-log', '')
    metadata_file = RECORDINGS_DIR / f"{base_name}_youtube-meta.json"
    
    if not metadata_file.exists():
        raise RecordAndPublishError(f"YouTube metadata file not found: {metadata_file}")
    
    # Check and fix the metadata file
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        needs_update = False
        
        # Fix the video_file path if it's null
        if video_file_path and not metadata.get('video_file'):
            # Convert absolute path to relative path if needed
            if video_file_path.is_absolute():
                try:
                    relative_path = video_file_path.relative_to(Path.cwd())
                    metadata['video_file'] = str(relative_path)
                except ValueError:
                    # If we can't make it relative, use absolute path
                    metadata['video_file'] = str(video_file_path)
            else:
                metadata['video_file'] = str(video_file_path)
            needs_update = True
            log(f"Updated metadata with video file: {metadata['video_file']}")
        
        # Add thumbnail file if provided
        if thumbnail_file:
            # Convert to relative path if needed
            thumbnail_path = Path(thumbnail_file)
            if thumbnail_path.is_absolute():
                try:
                    relative_path = thumbnail_path.relative_to(Path.cwd())
                    metadata['thumbnail_file'] = str(relative_path)
                except ValueError:
                    metadata['thumbnail_file'] = str(thumbnail_path)
            else:
                metadata['thumbnail_file'] = str(thumbnail_file)
            needs_update = True
            log(f"Updated metadata with thumbnail file: {metadata['thumbnail_file']}")
        
        # Check if title is incomplete (ends with just episode ID and colon)
        title = metadata.get('title', '')
        if title and title.strip().endswith(':'):
            log("Title appears incomplete, regenerating metadata with updated session log...")
            # Re-run the metadata generation
            run_command(cmd)
            # Re-read the updated metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            # Update video file again if needed
            if video_file_path and not metadata.get('video_file'):
                if video_file_path.is_absolute():
                    try:
                        relative_path = video_file_path.relative_to(Path.cwd())
                        metadata['video_file'] = str(relative_path)
                    except ValueError:
                        metadata['video_file'] = str(video_file_path)
                else:
                    metadata['video_file'] = str(video_file_path)
                needs_update = True
            # Re-add thumbnail file if needed
            if thumbnail_file:
                thumbnail_path = Path(thumbnail_file)
                if thumbnail_path.is_absolute():
                    try:
                        relative_path = thumbnail_path.relative_to(Path.cwd())
                        metadata['thumbnail_file'] = str(relative_path)
                    except ValueError:
                        metadata['thumbnail_file'] = str(thumbnail_path)
                else:
                    metadata['thumbnail_file'] = str(thumbnail_file)
                needs_update = True
        
        # Save any updates
        if needs_update:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
    except Exception as e:
        log(f"Warning: Could not update metadata file: {e}", "WARNING")
    
    log(f"YouTube metadata prepared: {metadata_file}")
    return metadata_file

def upload_to_youtube(metadata_file, upload=True):
    """Upload video to YouTube using the existing script"""
    if not upload:
        log("Skipping YouTube upload (dry run mode)")
        return None
    
    log("Uploading to YouTube...")
    
    # Check for YouTube credentials file
    credentials_file = Path("youtube_credentials.json")
    if not credentials_file.exists():
        # Fall back to environment variables
        required_env_vars = ['YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            log(f"Missing YouTube credentials file and environment variables: {', '.join(missing_vars)}", "WARNING")
            log("Skipping YouTube upload")
            return None
    else:
        log(f"Using YouTube credentials from: {credentials_file}")
    
    cmd = [
        "python", "scripts/upload_to_youtube.py",
        "--from-json", str(metadata_file)
    ]
    
    result = run_command(cmd)
    
    # Extract YouTube URL from output
    youtube_url = None
    for line in result.stdout.split('\n'):
        if 'YOUTUBE_URL=' in line:
            youtube_url = line.split('=', 1)[1].strip()
            break
    
    if youtube_url:
        log(f"YouTube upload successful: {youtube_url}")
    else:
        log("Could not find YouTube URL in upload output", "WARNING")
    
    return youtube_url

def update_youtube_thumbnail(video_id, thumbnail_file, upload=True):
    """Update thumbnail for an existing YouTube video"""
    if not upload:
        log("Skipping thumbnail update (dry run mode)")
        return
    
    log(f"Updating YouTube thumbnail for video {video_id}...")
    
    # Check for YouTube credentials file
    credentials_file = Path("youtube_credentials.json")
    if not credentials_file.exists():
        # Fall back to environment variables
        required_env_vars = ['YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            log(f"Missing YouTube credentials file and environment variables: {', '.join(missing_vars)}", "WARNING")
            log("Skipping thumbnail update")
            return
    else:
        log(f"Using YouTube credentials from: {credentials_file}")
    
    # Verify thumbnail file exists
    if not Path(thumbnail_file).exists():
        raise RecordAndPublishError(f"Thumbnail file not found: {thumbnail_file}")
    
    cmd = [
        "python", "scripts/upload_to_youtube.py",
        "--update-thumbnail-for", video_id,
        "--thumbnail-file", str(thumbnail_file)
    ]
    
    try:
        run_command(cmd)
        log(f"Thumbnail update successful for video {video_id}")
    except RecordAndPublishError as e:
        log(f"Thumbnail update failed: {e}", "ERROR")
        raise

def submit_to_wordpress(episode_data_file, youtube_url, episode_id, upload=True):
    """Submit episode to WordPress using the submit_episodes.py script"""
    if not upload:
        log("Skipping WordPress submission (dry run mode)")
        return
    
    log("Submitting to WordPress...")
    
    # Check for WordPress credentials
    passcode = os.getenv('WORDPRESS_PASSCODE')
    if not passcode:
        log("Missing WordPress passcode, skipping WordPress submission", "WARNING")
        return
    
    # Use the submit_episodes.py script we already created
    cmd = [
        "python", "scripts/submit_to_wordpress.py",
        "--episodes", episode_id
    ]
    
    try:
        run_command(cmd)
        log("WordPress submission completed")
    except RecordAndPublishError as e:
        log(f"WordPress submission failed: {e}", "WARNING")

def cleanup_large_files():
    """Remove large video files to save space"""
    log("Cleaning up large video files...")
    
    video_files = list(RECORDINGS_DIR.glob("*.mp4")) + list(RECORDINGS_DIR.glob("*.webm"))
    
    for video_file in video_files:
        try:
            size_mb = video_file.stat().st_size / (1024 * 1024)
            log(f"Removing {video_file.name} ({size_mb:.1f}MB)")
            video_file.unlink()
        except Exception as e:
            log(f"Could not remove {video_file}: {e}", "WARNING")

def main():
    parser = argparse.ArgumentParser(description="Record and publish JedAI Council episodes")
    parser.add_argument('--dry-run', action='store_true', help='Run without uploading to YouTube or WordPress')
    parser.add_argument('--skip-recording', action='store_true', help='Skip recording, use latest files')
    parser.add_argument('--skip-youtube', action='store_true', help='Skip YouTube upload')
    parser.add_argument('--skip-wordpress', action='store_true', help='Skip WordPress submission')
    parser.add_argument('--cleanup', action='store_true', help='Clean up large files after processing')
    parser.add_argument('--episode-url', type=str, help='Use specific episode URL instead of fetching latest')
    parser.add_argument('--thumbnail-file', type=str, help='Custom thumbnail file to use for upload or update')
    parser.add_argument('--update-thumbnail-for', type=str, metavar='VIDEO_ID', 
                        help='Update thumbnail for existing YouTube video (provide video ID). When used, only thumbnail update is performed.')
    # parser.add_argument('--update-wordpress-post', type=str, metavar='POST_ID',
    #                     help='Update a specific WordPress post ID instead of creating new post. Can be used with --skip-recording to update with latest files.')
    # parser.add_argument('--episode-id', type=str, metavar='S1E##',
    #                     help='Specify episode ID for WordPress operations (e.g., S1E15). Auto-detected if not provided.')
    # parser.add_argument('--youtube-url', type=str,
    #                     help='Specify YouTube URL for WordPress update operations.')
    
    args = parser.parse_args()
    
    try:
        log("=== Starting Record and Publish Process ===")
        
        # Handle standalone thumbnail update mode
        if args.update_thumbnail_for:
            if not args.thumbnail_file:
                raise RecordAndPublishError("--thumbnail-file is required when using --update-thumbnail-for")
            
            log(f"=== Thumbnail Update Mode for Video ID: {args.update_thumbnail_for} ===")
            update_youtube_thumbnail(args.update_thumbnail_for, args.thumbnail_file, upload=not args.dry_run)
            log("=== Thumbnail update completed successfully ===")
            return
        
        # Handle standalone WordPress update mode
        # if args.update_wordpress_post and args.skip_recording and not args.episode_url:
        #     log(f"=== WordPress Update Mode for Post ID: {args.update_wordpress_post} ===")
        #     
        #     # Find latest files for the update
        #     all_episode_data = list(RECORDINGS_DIR.glob("*_episode-data.json"))
        #     if not all_episode_data:
        #         raise RecordAndPublishError("No episode data files found for WordPress update")
        #     
        #     # Get the most recent episode data file
        #     latest_episode_data = sorted(all_episode_data, key=lambda f: f.stat().st_mtime, reverse=True)[0]
        #     
        #     # Extract episode ID if not provided
        #     episode_id = args.episode_id
        #     if not episode_id:
        #         try:
        #             with open(latest_episode_data, 'r') as f:
        #                 episode_data = json.load(f)
        #             episode_id = episode_data.get('id', 'Unknown')
        #         except Exception as e:
        #             log(f"Could not extract episode ID from {latest_episode_data}: {e}", "WARNING")
        #     
        #     log(f"Using episode data: {latest_episode_data}")
        #     log(f"Episode ID: {episode_id}")
        #     
        #     update_wordpress_post(
        #         args.update_wordpress_post,
        #         episode_data_file=latest_episode_data,
        #         youtube_url=args.youtube_url,
        #         episode_id=episode_id,
        #         thumbnail_file=args.thumbnail_file,
        #         upload=not args.dry_run
        #     )
        #     log("=== WordPress update completed successfully ===")
        #     return
        
        # Validate thumbnail file if provided
        if args.thumbnail_file:
            thumbnail_path = Path(args.thumbnail_file)
            if not thumbnail_path.exists():
                raise RecordAndPublishError(f"Thumbnail file not found: {args.thumbnail_file}")
            log(f"Using custom thumbnail: {args.thumbnail_file}")
        
        # Step 1: Get episode URL
        if args.skip_recording:
            log("Skipping recording, looking for latest files...")
            
            # Find the most recent files by modification time (regardless of naming format)
            all_session_logs = list(RECORDINGS_DIR.glob("*_session-log.json"))
            all_episode_data = list(RECORDINGS_DIR.glob("*_episode-data.json"))
            all_video_files = list(RECORDINGS_DIR.glob("*.mp4"))
            
            if not all_session_logs or not all_episode_data:
                raise RecordAndPublishError("Could not find required files for skip-recording mode")
            
            # Sort by modification time (newest first)
            session_log = sorted(all_session_logs, key=lambda f: f.stat().st_mtime, reverse=True)[0]
            episode_data_file = sorted(all_episode_data, key=lambda f: f.stat().st_mtime, reverse=True)[0]
            video_file = sorted(all_video_files, key=lambda f: f.stat().st_mtime, reverse=True)[0] if all_video_files else None
            
            log(f"Found latest session log: {session_log}")
            log(f"Found latest episode data: {episode_data_file}")
            if video_file:
                log(f"Found latest video file: {video_file}")
            
            # Extract episode info and try to get title
            episode_id = "Unknown"
            episode_name = ""
            try:
                with open(episode_data_file, 'r') as f:
                    episode_data = json.load(f)
                episode_id = episode_data.get('id', 'Unknown')
                episode_name = episode_data.get('name', '')
            except Exception as e:
                log(f"Could not read episode data: {e}", "WARNING")
            
            # Override episode ID if provided via command line
            # if args.episode_id:
            #     episode_id = args.episode_id
            #     log(f"Using command line episode ID: {episode_id}")
            
            # Extract title from session log if missing and ensure both files are updated
            if not episode_name:
                episode_name = extract_episode_title_from_session_log(session_log)
                if episode_name:
                    log(f"Extracted episode title from session log: '{episode_name}'")
            
            # Always ensure both files have the correct title if we have one
            if episode_name:
                # Update episode data file with extracted title
                try:
                    with open(episode_data_file, 'r') as f:
                        episode_data = json.load(f)
                    if episode_data.get('name') != episode_name:
                        episode_data['name'] = episode_name
                        with open(episode_data_file, 'w') as f:
                            json.dump(episode_data, f, indent=2)
                        log("Updated episode data file with extracted title")
                except Exception as e:
                    log(f"Could not update episode data file: {e}", "WARNING")
                
                # Update the session log's episode_data section
                try:
                    with open(session_log, 'r') as f:
                        session_data = json.load(f)
                    if 'episode_data' in session_data:
                        if session_data['episode_data'].get('name') != episode_name:
                            session_data['episode_data']['name'] = episode_name
                            with open(session_log, 'w') as f:
                                json.dump(session_data, f, indent=2)
                            log("Updated session log episode_data with extracted title")
                    else:
                        log("Session log missing episode_data section", "WARNING")
                except Exception as e:
                    log(f"Could not update session log: {e}", "WARNING")
            
            recording_result = {
                'video_file': video_file,
                'session_log': session_log,
                'episode_data_file': episode_data_file,
                'episode_id': episode_id
            }
            
            # Rename timestamp-based files to proper format if needed
            if episode_name and episode_id != 'Unknown':
                expected_prefix = f"{episode_id}_JedAI-Council"
                needs_rename = False
                
                if video_file and expected_prefix not in str(video_file):
                    needs_rename = True
                elif session_log and expected_prefix not in str(session_log):
                    needs_rename = True
                elif episode_data_file and expected_prefix not in str(episode_data_file):
                    needs_rename = True
                
                if needs_rename:
                    log("Found timestamp-based files, attempting to rename...")
                    renamed_files = rename_timestamp_files_to_episode_format(episode_id, episode_name)
                    
                    # Update file references if they were renamed
                    for old_name, new_path in renamed_files.items():
                        if video_file and old_name == video_file.name:
                            recording_result['video_file'] = new_path
                            log(f"Updated video file reference: {new_path}")
                        elif session_log and old_name == session_log.name:
                            recording_result['session_log'] = new_path
                            log(f"Updated session log reference: {new_path}")
                        elif episode_data_file and old_name == episode_data_file.name:
                            recording_result['episode_data_file'] = new_path
                            log(f"Updated episode data reference: {new_path}")
        else:
            episode_url = args.episode_url or fetch_latest_episode()
            
            # Step 2: Record episode
            recording_result = record_episode(episode_url)
        
        # Step 3: Prepare YouTube metadata (if not skipping YouTube)
        youtube_url = None
        if not args.skip_youtube:
            metadata_file = prepare_youtube_metadata(
                recording_result['session_log'], 
                recording_result['video_file'],
                YOUTUBE_PLAYLIST_ID,
                args.thumbnail_file
            )
            
            # Step 4: Upload to YouTube
            youtube_url = upload_to_youtube(metadata_file, upload=not args.dry_run)
                
            if youtube_url and not args.dry_run:
                log("Video is processing on YouTube. Continuing without waiting...")
        
        # Use command line YouTube URL if provided
        # if args.youtube_url:
        #     youtube_url = args.youtube_url
        #     log(f"Using command line YouTube URL: {youtube_url}")
        
        # Step 5: Submit to WordPress (either new post or update)
        if not args.skip_wordpress:
            # if args.update_wordpress_post:
            #     # Update existing WordPress post
            #     update_wordpress_post(
            #         args.update_wordpress_post,
            #         episode_data_file=recording_result['episode_data_file'],
            #         youtube_url=youtube_url,
            #         episode_id=recording_result['episode_id'],
            #         thumbnail_file=args.thumbnail_file,
            #         upload=not args.dry_run
            #     )
            # elif youtube_url:
            if youtube_url:
                # Create new WordPress post
                submit_to_wordpress(
                    recording_result['episode_data_file'],
                    youtube_url,
                    recording_result['episode_id'],
                    upload=not args.dry_run
                )
        
        # Step 6: Cleanup
        if args.cleanup:
            cleanup_large_files()
        
        log("=== Process completed successfully ===")
        
    except RecordAndPublishError as e:
        log(f"Process failed: {e}", "ERROR")
        sys.exit(1)
    except KeyboardInterrupt:
        log("Process interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main() 