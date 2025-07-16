# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **JedAI Council** project - an automated AI agent council that simulates governance debates between AI characters. The system records immersive 3D episodes where AI agents deliberate on DAO proposals and crypto/AI topics, then automatically publishes them to YouTube and WordPress.

## Common Commands

### Recording and Publishing
```bash
# Record a new episode
npm run record -- https://shmotime.com/shmotime_episode/episode-slug/

# Upload video to YouTube
npm run upload

# Manual recording with specific date
node scripts/recorder.js --date=2025-07-12 https://shmotime.com/shmotime_episode/episode-url/

# Set up YouTube authentication (first time only)
python scripts/setup_youtube_auth.py

# Prepare YouTube metadata from session log
python scripts/prepare_youtube_metadata.py path/to/session-log.json

# Upload to YouTube with metadata
python scripts/upload_to_youtube.py --from-json path/to/youtube-meta.json
```

### Dependencies
```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

### Episode Management
```bash
# View episode list mapping
cat list.txt

# Check recent recordings
ls -la recordings/

# Process episode data
python scripts/scrape.py
```

## Code Architecture

### Core Components

#### 1. **Episode Recording System** (`scripts/recorder.js`)
- **ShmotimeRecorder Class**: Main recording engine using Puppeteer
- **Event System**: Captures recording events (start_intro, end_credits, etc.)
- **Filename Management**: Generates canonical filenames from episode data and dates
- **Post-processing**: FFmpeg integration for video format conversion

#### 2. **Episode Data Structure** (`episodes/`)
- **Episode JSON Files**: Structured data defining scenes, dialogue, and character positions
- **Character System**: AI agents positioned in virtual council chamber pods
- **Scene Architecture**: Location-based scenes with dialogue arrays and character actions
- **Metadata Integration**: Episode data flows through recording → session logs → YouTube metadata

#### 3. **Automated Publishing Pipeline**
- **YouTube Upload** (`scripts/upload_to_youtube.py`): OAuth2-based video publishing
- **Metadata Generation** (`scripts/prepare_youtube_metadata.py`): Extracts titles, descriptions, thumbnails
- **WordPress Integration** (`scripts/submit_to_wordpress.py`): Publishes episode information
- **GitHub Actions**: Fully automated daily episode recording and publishing

#### 4. **Media Assets** (`media/`)
- **Character Avatars**: 2D and 3D character representations
- **Thumbnails**: Episode-specific artwork
- **3D Models**: Council chamber environment (`models/jedi_council_baked.glb`)

### Key Data Flows

1. **Episode Creation**: JSON files in `episodes/` define content structure
2. **Recording**: `recorder.js` loads episode data and captures video/audio
3. **Session Logging**: Recording generates `*_session-log.json` with complete metadata
4. **YouTube Pipeline**: `prepare_youtube_metadata.py` → `upload_to_youtube.py`
5. **WordPress Publishing**: `submit_to_wordpress.py` creates blog posts

### Authentication & Secrets

- **YouTube API**: Requires `client_secrets.json` and OAuth2 flow
- **Environment Variables**: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
- **GitHub Secrets**: Used for automated publishing workflows

### File Organization

- `episodes/`: Episode content definitions (JSON)
- `recordings/`: Generated video files and session logs
- `scripts/`: All automation and processing scripts
- `media/`: Visual assets and character designs
- `models/`: 3D environment assets
- `wp-payloads/`: WordPress publishing data

### Episode Filename Convention
Episodes use standardized naming: `YYYY-MM-DD_JedAI-Council_Episode-Title.ext`

The system maps episode URLs to recording dates via `list.txt` for consistent filename generation.

### Recording Event System
The recorder listens for specific events:
- `start_intro` → `end_intro`: Introduction sequence
- `start_ep` → `end_ep`: Main episode content  
- `start_credits` → `end_credits`: Closing credits
- `start_postcredits` → `end_postcredits`: Post-credits content

Configure `--stop-recording-at` to control when recording stops.

## Development Notes

- The system is designed for content automation, not interactive development
- Episode data is the single source of truth for all content
- Recording uses headless Chrome with optimized settings for video capture
- All scripts support both local interactive and CI/CD execution modes
- Character positioning uses a 5-pod system (north, south, east, west, center)