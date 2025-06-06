# JedAI Council Automation Scripts

This directory contains the scripts used by the GitHub Actions workflow to automatically record, process, and upload JedAI Council episodes to YouTube.

## Core Workflow

The process is a simple, three-step pipeline:

1.  **`recorder.js`**: Records the web-based episode and outputs a video file and a JSON session log with detailed metadata about the recording.
2.  **`prepare_youtube_metadata.py`**: Takes the session log, downloads the episode thumbnail, compresses it, and generates a new `_youtube-meta.json` file ready for the uploader.
3.  **`upload_to_youtube.py`**: Reads the `_youtube-meta.json` file and uploads the video to the specified YouTube channel and playlist.

An additional script, `setup_youtube_auth.py`, is used for a one-time setup to generate the necessary API credentials.

---

## Script Details

### 1. `recorder.js`

Records a Shmotime episode using a headless Chrome browser (Puppeteer).

**Key Functionality:**
-   Launches a headless browser with a virtual display.
-   Navigates to the episode URL.
-   Records the screen and audio into a `.webm` file.
-   Stops recording automatically when the `end_postcredits` event is detected.
-   Converts the `.webm` file to a 30fps `.mp4` using `ffmpeg`.
-   Exports a detailed `_session-log.json` containing all episode data and events.

**Usage:**
```bash
node scripts/recorder.js [options] <url>
```

| Option | Description | Default |
|---|---|---|
| `--headless` | Run in headless mode (required for CI) | `false` |
| `--mute` | Mute audio on the runner | `false` |
| `--quiet` | Suppress verbose debug logs | `false` |
| `--video-width` | Video width in pixels | `1920` |
| `--video-height`| Video height in pixels | `1080` |
| `--stop-recording-at`| Event to trigger recording stop | `end_credits`|

### 2. `prepare_youtube_metadata.py`

Prepares all necessary metadata for the YouTube upload.

**Key Functionality:**
-   Parses the `_session-log.json` from the recorder.
-   Extracts the episode title, description, and tags.
-   Downloads the episode thumbnail image from the URL provided in the session log.
-   **Compresses the thumbnail** to ensure it is under YouTube's 2MB limit.
-   Generates a final `_youtube-meta.json` file.

**Usage:**
```bash
python scripts/prepare_youtube_metadata.py <session_log_path> [youtube_playlist_id]
```

### 3. `upload_to_youtube.py`

Uploads the video to YouTube using the prepared metadata.

**Key Functionality:**
-   Authenticates with the YouTube API using provided credentials.
-   Uploads the video file specified in the metadata JSON.
-   Sets the title, description, tags, and privacy status.
-   Adds the uploaded video to the specified playlist.

**Usage:**
```bash
python scripts/upload_to_youtube.py --from-json <youtube_meta_json_path>
```

### 4. `setup_youtube_auth.py`

A utility script to generate the OAuth refresh token required for the GitHub Actions workflow. This only needs to be run once during initial setup.

**Usage:**
```bash
python scripts/setup_youtube_auth.py
```
This script will open a browser window for you to authenticate with Google and will then output the `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` values needed for the repository secrets.

---

## Manual Workflow Example

To run the entire process manually:

```bash
# 1. Record the episode (this creates the .mp4 and session-log.json)
node scripts/recorder.js \
  --headless \
  --mute \
  --quiet \
  https://shmotime.com/shmotime_episode/holo-agents-and-token-economics/

# 2. Prepare the metadata (this creates the youtube-meta.json)
# Note: Find the exact session log filename from the output of the previous command
python scripts/prepare_youtube_metadata.py \
  "recordings/S1E15_JedAI-Council_holo-agents-and-token-economics_session-log.json" \
  "PLp5K4ceh2pR0-rg8WPuFnlLTsreQ7HOQx"

# 3. Upload to YouTube
# Note: This step requires local client_secrets.json and youtube_credentials.json
python scripts/upload_to_youtube.py \
  --from-json "recordings/S1E15_JedAI-Council_holo-agents-and-token-economics_youtube-meta.json"
```
