# AI Agent Council


## What is it?

The AI Agent Council is a simulated governance chamber where AI agents—each trained on a specific slice of your DAO's knowledge and goals—deliberate on proposals, strategies, or problems in real time.

Think *Jedi Council* meets *Shark Tank* but with AI agents tailored towards a DAO. Each agent embodies a different point of view (users, builders, traders, ops) and gives structured, context-aware feedback regarding proposals, daily progress, user questions, and more.

The experience follows a cinematic flow:
1. Visitor arrives at the 3D website
2. Eliza (AI host) greets them and collects their question
3. Eliza transitions to the council chamber
4. The council debate plays out as an immersive 3D simulation
5. Optional wrap-up with Eliza summarizing the council's insights

## Why it matters

When things get noisy or decisions become gridlocked, the Council helps restore clarity:

- **Discover value-aligned opportunities** when you feel lost or disconnected
- **See different perspectives** quickly—across devs, users, operators, and investors
- **Get proposal feedback** before committing resources
- **Find group flow faster**, especially when the humans need rest

It's like having your own strategy room of champions, always ready to brainstorm—a step towards building a true DAO with humans + AI aligned and working together.

## How it works

### Shared Context Engine
- Autonomous data gathering from Discord, GitHub, X, and market activity
- AI memory tuned to past votes, outcomes, and key initiatives
- Continuous context updates ensure agents stay current with community priorities

### Agent Personas
- Agents trained with distinct POVs (user-first, technical, market-oriented)
- Each character has unique visual design, voice, and decision-making framework
- Collective intelligence emerges from their interactions

### Simulation Format
- Screenplay-style simulations with 3D character models
- Text-to-speech for dynamic dialogue generation
- Cinematic camera work and transitions

## Project Structure

```
.
├── character-context.txt       # Character training data
├── media/                      # Visual assets
│   ├── avatar-png/             # 2D character avatars
│   ├── avatars/                # Character design assets by project
│   │   ├── [avatar]/           # Individual character folders with assets
│   │   └── [avatar].glb        # Optimized models for web
│   ├── chatgpt/                # Transition scenes
│   └── unreal/                 # Environment screenshots
├── models/                     # 3D assets
│   └── jedi_council_baked.glb  # Council chamber environment
└── README.md                   # Project documentation
```

## Technical Components

- **3D Web Rendering**: Immersive council chamber environment
- **AI Character System**: Distinct personalities with contextual awareness
- **Text-to-Speech**: Dynamic voice generation for character dialogue
- **Animation Pipeline**: Character expressiveness and cinematography
- **Data Integration**: Autonomous gathering of community context

## Automated Episode Production

This repository contains a GitHub Actions workflow that fully automates the recording of new JedAI Council episodes and uploads them to YouTube.

**Workflow File**: [`.github/workflows/daily-episode-recording.yml`](./.github/workflows/daily-episode-recording.yml)

### How It Works

The workflow runs on a daily schedule and performs the following steps:

1.  **Fetch Latest Episode**: Gets the URL for the newest episode from the Shmotime API.
2.  **Record Episode**: Uses a headless Chrome browser to record the episode, saving a video file and a detailed session log.
3.  **Prepare Metadata**: A Python script processes the session log to generate a clean title, description, and tags. It also downloads and compresses the episode thumbnail.
4.  **Upload to YouTube**: Another Python script uploads the video, sets all the metadata, and adds it to the correct playlist.
5.  **Wait for Processing**: The workflow pauses for 5 minutes to give YouTube's servers time to process the video before the next step.
6.  **Archive & Cleanup**: The session log and thumbnail are saved as workflow artifacts, and the large video files are removed from the runner to save space.

### Setup for Your Fork

To get the automated workflow running on your own fork of this repository, follow these steps:

1.  **Get YouTube API Credentials**:
    *   Create a project in the [Google Cloud Console](https://console.cloud.google.com/).
    *   Enable the **YouTube Data API v3**.
    *   Create **OAuth 2.0 Client IDs** credentials for a "Desktop app".
    *   Download the JSON file and save it as `client_secrets.json` in the root of your local repository. **Do not commit this file.**

2.  **Generate a Refresh Token**:
    *   Run the setup script from your terminal:
        ```bash
        pip install -r requirements.txt
        python scripts/setup_youtube_auth.py
        ```
    *   This will open a browser window for you to sign in and grant access.
    *   The script will then print the three secret values you need for the next step.

3.  **Create GitHub Repository Secrets**:
    *   In your forked repository on GitHub, go to `Settings` > `Secrets and variables` > `Actions`.
    *   Create the following three repository secrets with the values from the previous step:
        *   `YOUTUBE_CLIENT_ID`
        *   `YOUTUBE_CLIENT_SECRET`
        *   `YOUTUBE_REFRESH_TOKEN`

4.  **Configure Workflow (Optional)**:
    *   You can change the YouTube playlist by editing the `YOUTUBE_PLAYLIST_ID` environment variable at the top of the `.github/workflows/daily-episode-recording.yml` file.

The workflow is now ready to run automatically or be triggered manually from the Actions tab on GitHub.

### Backfilling Episodes

To record all missing episodes from `list.txt`:

```bash
while IFS=, read -r date url; do node scripts/recorder.js --skip-existing --headless --mute --quiet --date="$date" "$url"; done < list.txt
```

Flags:
- `--skip-existing` - Skip if recording already exists
- `--headless` - Run without visible browser
- `--mute` - Mute audio during recording
- `--quiet` - Reduce log output

## Vision

The Council is an evolution in how DAOs can make decisions—combining human creativity with AI processing power to create more thoughtful, inclusive, and effective governance.

By creating this collective intelligence layer, we're experimenting with how visual simulation and AI personalities might enhance governance discussions, making complex coordination challenges more accessible and engaging for everyone.

This is a community project where builders can contribute to shaping the future of human+AI collaboration in decentralized organizations.

## Current Status

- **Prototype Live**: Screenplay-based episodes + internal tests
- **Data Integration**: Context engine being connected to community sources
- **Character Development**: Defining agent personalities and knowledge domains
- **Next Phase**: Interactive council sessions with direct user participation

these commands work on any shmotime episode viewing link btw `?debug_save_event_stream=1&downloadAudio=true`
if u want to download the clean mp3s or the huge actual event log
