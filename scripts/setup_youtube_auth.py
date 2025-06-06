#!/usr/bin/env python3
"""
YouTube API Authentication Setup
Generates refresh token for GitHub Actions workflow

Usage: python scripts/setup_youtube_auth.py
"""

import json
import os
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# YouTube API scope for uploading videos and managing playlists
SCOPES = ['https://www.googleapis.com/auth/youtube']

def setup_youtube_auth():
    """Generate YouTube API refresh token for automated uploads"""
    
    print("YouTube API Authentication Setup")
    print("=" * 40)
    
    # Check for existing credentials file
    if not os.path.exists('client_secrets.json'):
        print("client_secrets.json not found!")
        print("\nSetup Instructions:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a new project or select existing one")
        print("3. Enable 'YouTube Data API v3' in APIs & Services → Library")
        print("4. Create OAuth 2.0 credentials in APIs & Services → Credentials")
        print("5. Download the credentials JSON file")
        print("6. Rename it to 'client_secrets.json' and place in this directory")
        print("\nMake sure to add your email as a test user in OAuth consent screen!")
        return
    
    try:
        # Initialize OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', SCOPES
        )
        
        print("\nStarting OAuth flow...")
        print("A browser window will open for authentication")
        
        # Run local server for OAuth callback
        credentials = flow.run_local_server(port=0)
        
        print("\nAuthentication successful!")
        
        # Display credentials for GitHub Secrets
        print("\nGitHub Secrets Configuration:")
        print("=" * 40)
        print("Add these secrets to your GitHub repository:")
        print("Settings → Secrets and variables → Actions → New repository secret")
        print()
        print(f"YOUTUBE_CLIENT_ID = {credentials.client_id}")
        print(f"YOUTUBE_CLIENT_SECRET = {credentials.client_secret}")
        print(f"YOUTUBE_REFRESH_TOKEN = {credentials.refresh_token}")
        
        # Save credentials locally for testing
        creds_data = {
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'refresh_token': credentials.refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token'
        }
        
        with open('youtube_credentials.json', 'w') as f:
            json.dump(creds_data, f, indent=2)
        
        print(f"\nCredentials also saved to: youtube_credentials.json")
        print("Keep this file secure and don't commit to version control!")
        
        print("\nSetup Complete!")
        print("Your GitHub Actions workflow can now upload to YouTube automatically.")
        
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        print("\nTroubleshooting:")
        print("• Make sure client_secrets.json is valid")
        print("• Check that YouTube Data API v3 is enabled")
        print("• Ensure your email is added as test user in OAuth consent screen")
        print("• Try using a different browser or incognito mode")

if __name__ == '__main__':
    setup_youtube_auth() 