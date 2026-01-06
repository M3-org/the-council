#!/usr/bin/env python3
"""
Align Gemini transcript with session-log using LLM.

Takes:
- Gemini JSON: word-level timestamps from audio transcription
- Session-log JSON: speaker labels and correct script text

Uses an LLM to:
1. Match each Gemini segment to the correct speaker
2. Use session-log text to fix transcription errors
3. Output clean transcript with accurate speaker labels and timestamps
"""

import argparse
import json
import os
import sys

import requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"


def get_api_key():
    """Get API key from environment."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("Error: OPENROUTER_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return key


def load_json(path: str) -> dict:
    """Load JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_dialogues(session_log: dict) -> list[dict]:
    """Extract all dialogues with speaker info from session-log."""
    dialogues = []

    # Find episode data - prefer top-level episode_data as it has full dialogue
    # event_timeline's load_episode often has scenes without dialogue content
    episode_data = session_log.get("episode_data", {})

    # Check if episode_data has dialogues, if not try event_timeline
    has_dialogues = any(
        scene.get("dialogue") for scene in episode_data.get("scenes", [])
    )

    if not has_dialogues:
        for event in session_log.get("event_timeline", []):
            if event.get("type") == "load_episode":
                event_data = event.get("data", {})
                if any(scene.get("dialogue") for scene in event_data.get("scenes", [])):
                    episode_data = event_data
                    break

    if not episode_data:
        return dialogues

    # Get actor metadata
    show_config = session_log.get("show_config", {})
    actors = show_config.get("actors", {})

    # Extract dialogues from scenes
    for scene in episode_data.get("scenes", []):
        for dialogue in scene.get("dialogue", []):
            actor_id = dialogue.get("actor", "unknown")
            actor_info = actors.get(actor_id, {})

            dialogues.append({
                "actor_id": actor_id,
                "actor_name": actor_info.get("name", actor_id),
                "line": dialogue.get("line", ""),
                "scene": scene.get("number", 0)
            })

    return dialogues


def build_alignment_prompt(gemini_segments: list, dialogues: list) -> str:
    """Build the alignment prompt for the LLM."""

    # Format dialogues (script)
    script_lines = []
    for i, d in enumerate(dialogues):
        script_lines.append(f"{i}. [{d['actor_id']}] {d['actor_name']}: \"{d['line']}\"")
    script_str = "\n".join(script_lines)

    # Format Gemini segments (transcript)
    transcript_lines = []
    for i, seg in enumerate(gemini_segments):
        transcript_lines.append(f"{i}. [{seg['start']:.1f}s - {seg['end']:.1f}s] \"{seg['text']}\"")
    transcript_str = "\n".join(transcript_lines)

    prompt = f"""You are aligning an audio transcript to a script for the "JedAI Council" podcast.

## Script (correct text with speakers)
{script_str}

## Transcript (from audio, may have errors)
{transcript_str}

## Task
For each transcript segment, find the matching script line and output:
- The transcript segment index
- The matching script line index (or -1 if no match)
- The correct speaker_id and speaker_name from the script

Output a JSON array with one object per transcript segment:
```json
[
  {{"segment": 0, "script_match": 0, "speaker_id": "elizahost", "speaker_name": "Eliza"}},
  {{"segment": 1, "script_match": 1, "speaker_id": "aixvc", "speaker_name": "AIXVC"}},
  {{"segment": 2, "script_match": -1, "speaker_id": "unknown", "speaker_name": "Unknown"}}
]
```

Rules:
- Match based on content similarity, not position
- A transcript segment may be part of a longer script line
- Multiple transcript segments can match the same script line (if audio was split)
- Use speaker_id "unknown" only if truly unidentifiable
- Return ONLY the JSON array"""

    return prompt


def align_transcript(gemini_path: str, session_log_path: str, model: str = DEFAULT_MODEL) -> dict:
    """Align Gemini transcript with session-log using LLM."""

    api_key = get_api_key()

    gemini = load_json(gemini_path)
    session_log = load_json(session_log_path)

    segments = gemini.get("segments", [])
    dialogues = extract_dialogues(session_log)

    if not dialogues:
        print("Warning: No dialogues found in session-log", file=sys.stderr)
        return gemini

    prompt = build_alignment_prompt(segments, dialogues)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/the-council",
        "X-Title": "JedAI Council Transcript Alignment"
    }

    print(f"Aligning {len(segments)} segments to {len(dialogues)} script lines...", file=sys.stderr)

    response = requests.post(
        OPENROUTER_API_URL,
        headers=headers,
        json=payload,
        timeout=120
    )

    if response.status_code != 200:
        print(f"API Error: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)

    result = response.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "[]")

    # Clean markdown code blocks
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    try:
        alignments = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response: {e}", file=sys.stderr)
        print(f"Raw: {content}", file=sys.stderr)
        sys.exit(1)

    # Build alignment lookup
    alignment_map = {a["segment"]: a for a in alignments}

    # Build output segments
    output_segments = []
    for i, seg in enumerate(segments):
        align = alignment_map.get(i, {})
        script_idx = align.get("script_match", -1)

        # Get corrected text from script if matched
        if script_idx >= 0 and script_idx < len(dialogues):
            dialogue = dialogues[script_idx]
            text = dialogue["line"]
            scene = dialogue["scene"]
        else:
            text = seg["text"]
            scene = 0

        output_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": text,
            "speaker_id": align.get("speaker_id", "unknown"),
            "speaker_name": align.get("speaker_name", "Unknown"),
            "scene": scene,
            "words": seg.get("words", [])
        })

    # Count stats
    matched = sum(1 for a in alignments if a.get("script_match", -1) >= 0)
    print(f"Matched {matched}/{len(segments)} segments", file=sys.stderr)

    return {
        "segments": output_segments,
        "language": gemini.get("language", "en"),
        "metadata": {
            "gemini_source": os.path.basename(gemini_path),
            "session_log_source": os.path.basename(session_log_path),
            "total_segments": len(output_segments),
            "matched_segments": matched,
            "dialogues_in_script": len(dialogues)
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Align Gemini transcript with session-log using LLM"
    )
    parser.add_argument("gemini_json", help="Path to Gemini transcription JSON")
    parser.add_argument("session_log_json", help="Path to session-log JSON")
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})"
    )

    args = parser.parse_args()

    if not os.path.exists(args.gemini_json):
        print(f"Error: File not found: {args.gemini_json}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.session_log_json):
        print(f"Error: File not found: {args.session_log_json}", file=sys.stderr)
        sys.exit(1)

    aligned = align_transcript(args.gemini_json, args.session_log_json, args.model)

    output_json = json.dumps(aligned, indent=2, ensure_ascii=False)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
