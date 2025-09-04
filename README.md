# Wedding Photo Finder

A web application that allows wedding guests to find photos of themselves by uploading a selfie. The system uses face recognition to match selfies with a collection of wedding photos.

## Features

- **Face Recognition**: Uses InsightFace for accurate face detection and embedding extraction
- **Google Drive Integration**: Processes photos stored in Google Drive
- **Supabase Backend**: Stores face embeddings for fast similarity search
- **Elegant UI**: Clean, responsive interface with a navy blue and white theme
- **Selfie Matching**: Guests upload a selfie to find all photos they appear in

## Project Structure

- `supabase_face_finder.py`: Main application with API endpoints and processing logic
- `create_urls_file.py`: Utility to extract URLs from Google Drive folders
- `simple_frontend.html`: Frontend interface for guests to upload selfies
- `requirements.txt`: Python dependencies
- `step_by_step_deployment.md`: Detailed deployment instructions

## Setup and Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Extract Google Drive URLs**:
   ```bash
   python create_urls_file.py --folder-id YOUR_FOLDER_ID --output urls.txt
   ```

3. **Process photos** (one-time admin task):
   ```bash
   python supabase_face_finder.py --mode process --urls-file urls.txt
   ```

4. **Start the API server**:
   ```bash
   python supabase_face_finder.py --mode serve --port 8000
   ```

5. **Serve the frontend**:
   ```bash
   python -m http.server 8080
   ```

## Deployment

See `step_by_step_deployment.md` for detailed deployment instructions, including options for:
- VPS/Cloud Server deployment
- Serverless deployment (Render, Vercel, etc.)
- Local network deployment

## Technologies Used

- **Backend**: Python, FastAPI, InsightFace
- **Storage**: Supabase (PostgreSQL with pgvector)
- **Frontend**: HTML, JavaScript, TailwindCSS
- **APIs**: Google Drive API

## License

MIT