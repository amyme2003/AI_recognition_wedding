#!/usr/bin/env python3
"""
Script to create a file with Google Drive URLs from a folder ID.
This helps prepare the input for the supabase_face_finder.py script.

Requirements:
- Google API Client: pip install google-api-python-client

Usage:
python create_urls_file.py --folder-id YOUR_FOLDER_ID --output urls.txt
"""

import argparse
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_credentials():
    """Get and save user credentials."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def list_files_in_folder(service, folder_id, page_token=None):
    """List all files in a Google Drive folder."""
    results = []
    
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType)',
            pageToken=page_token
        ).execute()
        
        items = response.get('files', [])
        
        for item in items:
            # If it's a folder, recursively list files
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                sub_results = list_files_in_folder(service, item['id'])
                results.extend(sub_results)
            # If it's an image file, add it to results
            elif item['mimeType'].startswith('image/'):
                results.append(item)
        
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Create a file with Google Drive URLs from a folder')
    parser.add_argument('--folder-id', required=True, help='Google Drive folder ID')
    parser.add_argument('--output', default='drive_urls.txt', help='Output file path')
    
    args = parser.parse_args()
    
    # Get credentials and build service
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    
    print(f"Listing files in folder {args.folder_id}...")
    files = list_files_in_folder(service, args.folder_id)
    
    print(f"Found {len(files)} files")
    
    # Write URLs to file
    with open(args.output, 'w') as f:
        for file in files:
            url = f"https://drive.google.com/file/d/{file['id']}/view"
            f.write(f"{url}\n")
    
    print(f"URLs written to {args.output}")

if __name__ == '__main__':
    main()

# Made with Bob
