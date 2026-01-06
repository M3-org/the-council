#!/usr/bin/env python3
"""
Transcribe audio using Google Gemini 3 Flash via OpenRouter API.
Outputs word-level timestamps in structured JSON format.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3-flash-preview"


def get_api_key():
    """Get API key from environment."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("Error: OPENROUTER_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return key


def encode_audio(audio_path: str) -> tuple[str, str]:
    """Base64 encode audio file and detect format."""
    path = Path(audio_path)
    suffix = path.suffix.lower().lstrip(".")

    format_map = {
        "mp3": "mp3",
        "wav": "wav",
        "m4a": "m4a",
        "aac": "aac",
        "ogg": "ogg",
        "flac": "flac",
    }

    audio_format = format_map.get(suffix, suffix)

    with open(audio_path, "rb") as f:
        audio_data = base64.standard_b64encode(f.read()).decode("utf-8")

    return audio_data, audio_format


def transcribe(audio_path: str, model: str = DEFAULT_MODEL) -> dict:
    """Transcribe audio file with word-level timestamps."""

    api_key = get_api_key()
    audio_data, audio_format = encode_audio(audio_path)

    # JSON schema for structured output
    transcript_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "transcript",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "segments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "start": {
                                    "type": "number",
                                    "description": "Start time in seconds"
                                },
                                "end": {
                                    "type": "number",
                                    "description": "End time in seconds"
                                },
                                "text": {
                                    "type": "string",
                                    "description": "Transcribed text for this segment"
                                },
                                "words": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "word": {"type": "string"},
                                            "start": {"type": "number"},
                                            "end": {"type": "number"}
                                        },
                                        "required": ["word", "start", "end"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["start", "end", "text", "words"],
                            "additionalProperties": False
                        }
                    },
                    "language": {
                        "type": "string",
                        "description": "Detected language code (e.g., 'en')"
                    }
                },
                "required": ["segments", "language"],
                "additionalProperties": False
            }
        }
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Transcribe this audio with precise word-level timestamps. "
                            "For each word, provide the exact start and end time in seconds. "
                            "Group words into logical segments (sentences or phrases). "
                            "Be precise with timestamps - they should align with when each word is spoken."
                        )
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_data,
                            "format": audio_format
                        }
                    }
                ]
            }
        ],
        "response_format": transcript_schema
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/the-council",
        "X-Title": "JedAI Council Transcription"
    }

    print(f"Transcribing: {audio_path}", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)
    print(f"Audio format: {audio_format}", file=sys.stderr)

    response = requests.post(
        OPENROUTER_API_URL,
        headers=headers,
        json=payload,
        timeout=300  # 5 minute timeout for long audio
    )

    if response.status_code != 200:
        print(f"API Error: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)

    result = response.json()

    # Extract content from response
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")

    # Parse the JSON content
    try:
        transcript = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}", file=sys.stderr)
        print(f"Raw content: {content}", file=sys.stderr)
        sys.exit(1)

    return transcript


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio using Gemini 3 Flash via OpenRouter"
    )
    parser.add_argument("audio_file", help="Path to audio file (mp3, wav, m4a, etc.)")
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

    if not os.path.exists(args.audio_file):
        print(f"Error: File not found: {args.audio_file}", file=sys.stderr)
        sys.exit(1)

    transcript = transcribe(args.audio_file, args.model)

    output_json = json.dumps(transcript, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
