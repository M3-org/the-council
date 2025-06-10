# JedAI Council Automation Scripts

This directory contains the scripts used to automatically record, process, and upload JedAI Council episodes to YouTube.

## 🚀 **Quick Start**

### One-Line Daily Recording
```bash
# Add this function to your ~/.zshrc
record-latest() {
    local current_dir=$(pwd)
    cd /home/jin/repo/the-council
    python scripts/record-and-publish.py --episode-url "$(curl -s "https://shmotime.com/wp-json/shmotime/v1/get-latest-episode?show_id=2578" | jq -r ".episode.permalink")" "$@"
    cd "$current_dir"
}

# Then use it:
record-latest --skip-wordpress          # Record latest episode, skip WordPress
record-latest --dry-run                 # Test run without uploading
record-latest --thumbnail-file custom.jpg  # Record with custom thumbnail
```

### Automated Daily Recording (Cron)
```bash
# Add to crontab for daily 04:15 UTC recording
crontab -e

# Add this line:
15 4 * * * cd /home/jin/repo/the-council && source .env && python scripts/record-and-publish.py --episode-url "$(curl -s "https://shmotime.com/wp-json/shmotime/v1/get-latest-episode?show_id=2578" | jq -r ".episode.permalink")" --skip-wordpress >> /home/jin/repo/the-council/cron.log 2>&1
```

---

## 📋 **Core Workflow**

The main script `record-and-publish.py` provides a complete automation pipeline:

1. **Episode Discovery**: Fetches latest episode from Shmotime API
2. **Recording**: Uses `recorder.js` to capture the episode
3. **Metadata Generation**: Creates YouTube metadata with `prepare_youtube_metadata.py`
4. **YouTube Upload**: Uploads video and adds to playlist with `upload_to_youtube.py`
5. **WordPress Submission**: (Optional) Submits episode data to WordPress

### Main Script Usage

```bash
# Full workflow - record latest episode and publish
python scripts/record-and-publish.py

# Record specific episode
python scripts/record-and-publish.py --episode-url "https://shmotime.com/shmotime_episode/episode-title/"

# Skip recording, use latest files
python scripts/record-and-publish.py --skip-recording

# Test without uploading
python scripts/record-and-publish.py --dry-run

# Record with custom thumbnail
python scripts/record-and-publish.py --thumbnail-file media/thumbnails/custom.jpg

# Skip YouTube upload
python scripts/record-and-publish.py --skip-youtube

# Clean up large files after processing
python scripts/record-and-publish.py --cleanup

# Update thumbnail for existing YouTube video
python scripts/record-and-publish.py --update-thumbnail-for VIDEO_ID --thumbnail-file thumbnail.jpg
```

---

## 🔧 **Individual Scripts**

### 1. `recorder.js`

Records Shmotime episodes using headless Chrome browser.

**Key Features:**
- Automatic episode detection and S1E# numbering
- Records to optimized .mp4 format (30fps)
- Exports comprehensive session logs with episode metadata
- Smart file naming: `S1E##_JedAI-Council_title_fps30.mp4`

**Direct Usage:**
```bash
node scripts/recorder.js [options] <episode-url>

# Options:
--headless              # Run without browser window (required for automation)
--mute                  # Mute audio during recording
--video-width=1920      # Video width in pixels
--video-height=1080     # Video height in pixels
--stop-recording-at=end_postcredits  # When to stop recording
```

**Output Files:**
- `S1E##_JedAI-Council_title_fps30.mp4` - Final video file
- `S1E##_JedAI-Council_title_session-log.json` - Complete recording metadata
- `S1E##_JedAI-Council_title_episode-data.json` - Episode-specific data

### 2. `prepare_youtube_metadata.py`

Generates YouTube metadata from session logs.

**Features:**
- Extracts episode titles and descriptions
- Downloads and compresses thumbnails (under 2MB limit)
- Creates properly formatted descriptions with emojis and links
- Generates optimized tags for AI/Blockchain content

**Usage:**
```bash
python scripts/prepare_youtube_metadata.py <session_log_path> [playlist_id]

# Example:
python scripts/prepare_youtube_metadata.py \
  "recordings/S1E15_session-log.json" \
  "PLp5K4ceh2pR0-rg8WPuFnlLTsreQ7HOQx"
```

**Generated Metadata Format:**
```json
{
  "video_file": "recordings/S1E15_JedAI-Council_title_fps30.mp4",
  "title": "JedAI Council S1E15: Episode Title",
  "description": "🤖 JedAI Council Episode S1E15...",
  "tags": "JedAI Council,AI,Blockchain,Web3,ElizaOS,ai16z,AGI",
  "category_id": "22",
  "privacy_status": "unlisted",
  "playlist_id": "PLp5K4ceh2pR0-rg8WPuFnlLTsreQ7HOQx"
}
```

### 3. `upload_to_youtube.py`

Uploads videos to YouTube with playlist management.

**Features:**
- OAuth 2.0 authentication with refresh token support
- Automatic playlist addition to JedAI Council playlist
- Thumbnail upload support
- Retry logic for failed uploads
- Environment variable support for CI/CD

**Usage:**
```bash
# Upload using metadata file (recommended)
python scripts/upload_to_youtube.py --from-json metadata.json

# Direct upload with parameters
python scripts/upload_to_youtube.py \
  --video-file "episode.mp4" \
  --title "Episode Title" \
  --description "Description..." \
  --playlist-id "PLp5K4ceh2pR0-rg8WPuFnlLTsreQ7HOQx"

# Update thumbnail only
python scripts/upload_to_youtube.py \
  --update-thumbnail-for VIDEO_ID \
  --thumbnail-file thumbnail.jpg
```

### 4. `setup_youtube_auth.py`

One-time YouTube API authentication setup.

**Usage:**
```bash
python scripts/setup_youtube_auth.py
```

This creates `youtube_credentials.json` with proper OAuth scope for playlist management.

---

## 🌐 **Episode Discovery & API**

### Shmotime API Integration

Episodes are automatically fetched from: `https://shmotime.com/wp-json/shmotime/v1/get-latest-episode?show_id=2578`

**API Response:**
```json
{
  "success": true,
  "episode": {
    "id": 4713,
    "title": "Episode Title",
    "permalink": "https://shmotime.com/shmotime_episode/episode-title/",
    "date": "2025-06-05T04:13:57+00:00",
    "excerpt": "Episode description...",
    "thumbnail": "https://shmotime.com/.../thumbnail.png"
  }
}
```

### Episode Numbering

Episodes are automatically numbered as S1E## based on:
- Publication date calculation (S1E1 = 2025-05-27)
- Sequential numbering for consistent tracking
- Smart conflict resolution for overlapping episodes

---

## 📁 **File Organization**

```
the-council/
├── .env                              # WordPress credentials
├── client_secrets.json              # YouTube OAuth config
├── youtube_credentials.json         # Generated auth tokens
├── scripts/
│   ├── record-and-publish.py        # Main automation script
│   ├── recorder.js                  # Episode recording
│   ├── prepare_youtube_metadata.py  # Metadata generation
│   ├── upload_to_youtube.py         # YouTube upload
│   └── setup_youtube_auth.py        # One-time auth setup
├── recordings/                      # Episode files
│   ├── S1E##_JedAI-Council_title_fps30.mp4
│   ├── S1E##_JedAI-Council_title_session-log.json
│   ├── S1E##_JedAI-Council_title_episode-data.json
│   └── S1E##_JedAI-Council_title_youtube-meta.json
└── media/thumbnails/                # Custom thumbnails
    └── S1E##.jpg
```

---

## ⚙️ **Setup Requirements**

### Dependencies
```bash
# Python dependencies
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests

# Node.js dependencies
npm install puppeteer puppeteer-stream

# System dependencies
# ffmpeg (for video processing)
# curl, jq (for API calls)
```

### Environment Variables
```bash
# Required in .env file:
WORDPRESS_PASSCODE=your_wordpress_passcode

# Optional YouTube credentials (can use files instead):
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token
```

### YouTube Setup
1. Create Google Cloud Project
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials → Download `client_secrets.json`
4. Run `python scripts/setup_youtube_auth.py` for first-time auth

---

## 🎯 **Common Workflows**

### Daily Automation
```bash
# Set up the alias in ~/.zshrc
record-latest() {
    local current_dir=$(pwd)
    cd /home/jin/repo/the-council
    python scripts/record-and-publish.py --episode-url "$(curl -s "https://shmotime.com/wp-json/shmotime/v1/get-latest-episode?show_id=2578" | jq -r ".episode.permalink")" "$@"
    cd "$current_dir"
}

# Daily recording at 04:15 UTC via cron
15 4 * * * cd /home/jin/repo/the-council && source .env && python scripts/record-and-publish.py --episode-url "$(curl -s "https://shmotime.com/wp-json/shmotime/v1/get-latest-episode?show_id=2578" | jq -r ".episode.permalink")" --skip-wordpress >> cron.log 2>&1
```

### Manual Processing
```bash
# Process specific episode
python scripts/record-and-publish.py --episode-url "https://shmotime.com/shmotime_episode/specific-episode/"

# Use existing recording files
python scripts/record-and-publish.py --skip-recording

# Test run without uploads
python scripts/record-and-publish.py --dry-run
```

### Batch Operations
```bash
# Upload multiple existing videos
for file in recordings/S1E*_youtube-meta.json; do
  python scripts/upload_to_youtube.py --from-json "$file"
done

# Update thumbnails for multiple videos
python scripts/upload_to_youtube.py --update-thumbnail-for VIDEO_ID1 --thumbnail-file thumb1.jpg
python scripts/upload_to_youtube.py --update-thumbnail-for VIDEO_ID2 --thumbnail-file thumb2.jpg
```

---

## 🔍 **Troubleshooting**

### Common Issues

**Authentication Problems:**
```bash
# Re-authenticate if YouTube upload fails
rm youtube_credentials.json
python scripts/setup_youtube_auth.py
```

**Playlist Issues:**
- Ensure YouTube credentials have playlist management scope
- Verify playlist ID: `PLp5K4ceh2pR0-rg8WPuFnlLTsreQ7HOQx`
- Check that playlist is not private

**Recording Issues:**
- Check that episode URL is accessible
- Verify ffmpeg is installed for video processing
- Check available disk space in recordings/ directory

**File Naming Issues:**
- Script automatically handles timestamp → episode format conversion
- Ensure episode data contains proper `id` and `name` fields

### Debug Commands
```bash
# Test API endpoint
curl -s "https://shmotime.com/wp-json/shmotime/v1/get-latest-episode?show_id=2578" | jq

# Verify latest files
ls -la recordings/ | head -10

# Check cron logs
tail -f /home/jin/repo/the-council/cron.log

# Test authentication
python scripts/setup_youtube_auth.py --test-auth
```

---

## 📊 **Monitoring**

### Log Files
- `cron.log` - Daily automation logs
- `recordings/*_session-log.json` - Detailed recording metadata
- YouTube upload output shows success/failure status

### Success Indicators
- ✅ Video files created with proper S1E## naming
- ✅ YouTube metadata generated successfully
- ✅ Video uploaded and added to playlist
- ✅ Proper title format: "JedAI Council S1E##: Title"

---

*Last updated: 2025-01-20*
*Current focus: Stable daily automation with record-and-publish.py*
