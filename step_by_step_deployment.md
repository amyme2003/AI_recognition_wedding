# Step-by-Step Deployment Guide

This guide will walk you through exactly how to deploy and use the Wedding Photo Finder system.

## Prerequisites

- Python 3.8+ installed
- Access to your Google Drive wedding photos
- Supabase account already set up
- Basic command line knowledge

## Step 1: Set Up Your Environment

1. **Create a new directory for the project**:
   ```bash
   mkdir wedding-photo-finder
   cd wedding-photo-finder
   ```

2. **Download all the project files** to this directory:
   - `supabase_face_finder.py`
   - `create_urls_file.py`
   - `requirements.txt`
   - `simple_frontend.html`

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 2: Set Up Google Drive Access

1. **Create Google Cloud credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API
   - Create OAuth credentials (Desktop application)
   - Download the JSON file and save it as `credentials.json` in your project directory

2. **Extract Google Drive URLs**:
   ```bash
   python create_urls_file.py --folder-id YOUR_FOLDER_ID --output urls.txt
   ```
   Replace `YOUR_FOLDER_ID` with the ID from your Google Drive folder URL.
   
   The first time you run this, it will open a browser window asking you to authorize access to your Google Drive.

3. **Verify the URLs file**:
   Open `urls.txt` and check that it contains links to your wedding photos.

## Step 3: Process Photos and Store in Supabase

1. **Run the processing script**:
   ```bash
   python supabase_face_finder.py --mode process --urls-file urls.txt
   ```

   This will:
   - Download each photo from Google Drive
   - Extract face embeddings
   - Store them in your Supabase database
   - Show progress as it processes

   For a large collection, this may take some time (potentially hours).

2. **Check processing results**:
   - The script will create a `processing_results.json` file
   - Review this file to see which photos were processed successfully
   - If some photos failed, you can fix issues and rerun with just those photos

## Step 4: Start the API Server

1. **Run the API server**:
   ```bash
   python supabase_face_finder.py --mode serve --port 8000
   ```

2. **Verify the server is running**:
   Open a browser and go to `http://localhost:8000/`
   You should see the API documentation page.

## Step 5: Test the Frontend Locally

1. **Open the frontend**:
   Open `simple_frontend.html` in your browser

2. **Upload a test selfie**:
   - Choose a photo of someone you know is in the wedding photos
   - Click "Find My Photos"
   - Verify that matching photos are displayed

## Step 6: Deploy to Production

### Option A: Deploy on a VPS or Cloud Server

1. **Set up a server** (DigitalOcean, AWS, etc.)

2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip
   pip install -r requirements.txt
   ```

3. **Set up a production web server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker supabase_face_finder:app
   ```

4. **Set up Nginx** as a reverse proxy (optional but recommended)

5. **Upload the frontend** to your web server

### Option B: Deploy on Vercel, Netlify, or GitHub Pages

1. **Deploy the frontend** to your preferred static hosting service

2. **Deploy the API** to a serverless platform like:
   - Vercel
   - Netlify Functions
   - AWS Lambda

3. **Update the API URL** in the frontend to point to your deployed API

### Option C: Simple Local Network Deployment

If you just want to run this on your local network during the wedding:

1. **Find your computer's local IP address**

2. **Start the API server**:
   ```bash
   python supabase_face_finder.py --mode serve --port 8000
   ```

3. **Update the API URL** in `simple_frontend.html`:
   Change `const API_URL = 'http://localhost:8000';` to `const API_URL = 'http://YOUR_LOCAL_IP:8000';`

4. **Share the frontend URL** with guests on your local network

## Step 7: Share with Wedding Guests

1. **Create a simple landing page** explaining how to use the system

2. **Share the URL** with your wedding guests via:
   - Email
   - Wedding website
   - QR code at the venue

3. **Add instructions** for guests:
   - "Upload a selfie to find all your photos from the wedding"
   - "Adjust the slider if you want more or fewer results"

## Troubleshooting

### API Server Issues

- **InsightFace installation problems**:
  ```bash
  pip uninstall insightface
  pip install insightface==0.7.3
  ```

- **Supabase connection issues**:
  Verify your Supabase URL and key in `supabase_face_finder.py`

### Google Drive Issues

- **Authentication errors**:
  Delete `token.pickle` and try again

- **Download failures**:
  Some files might have restricted permissions. Make sure all photos are accessible.

### Frontend Issues

- **CORS errors**:
  If hosting the frontend and API on different domains, you may need to adjust CORS settings.

## Maintenance

- **Adding new photos**:
  1. Add photos to your Google Drive folder
  2. Extract new URLs
  3. Process only the new photos
  4. No need to restart the API server

- **Backing up data**:
  Regularly export your Supabase data to avoid loss

## Next Steps

- Add user authentication to protect privacy
- Implement photo grouping by event or date
- Add download functionality for guests