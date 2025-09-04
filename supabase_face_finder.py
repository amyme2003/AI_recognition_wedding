import os
import argparse
import numpy as np
import insightface
from insightface.app import FaceAnalysis
import cv2
import tempfile
import urllib.request
from tqdm import tqdm
import concurrent.futures
from supabase.client import create_client, Client
import time
import re
from PIL import Image
import io
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional
import json

# Supabase configuration
SUPABASE_URL = "https://swkeetndpxrodetmldxv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN3a2VldG5kcHhyb2RldG1sZHh2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTMxMzEsImV4cCI6MjA3MjU2OTEzMX0.uI9K0knnZVJYAbJ2zBUa2EZ3Lod7oLkG-k-h_qgVdgM"  # Replace with your actual key

# Initialize FastAPI app
app = FastAPI(title="Wedding Photo Finder API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize face detection model
def initialize_face_model():
    """Initialize the InsightFace model"""
    try:
        face_app = FaceAnalysis(name='buffalo_l')
        face_app.prepare(ctx_id=0, det_size=(640, 640))
        print("InsightFace model loaded successfully")
        return face_app
    except Exception as e:
        print(f"Error loading InsightFace model: {e}")
        return None

# Initialize Supabase client
def get_supabase_client():
    """Get Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def extract_drive_id(url):
    """Extract Google Drive file ID from URL"""
    # Pattern for Google Drive links
    patterns = [
        r"https://drive\.google\.com/file/d/(.*?)(/|$)",
        r"https://drive\.google\.com/open\?id=(.*?)($|&)",
        r"https://docs\.google\.com/file/d/(.*?)(/|$)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def download_from_drive(file_id, output_path=None, max_retries=3, retry_delay=5):
    """Download file from Google Drive with retry logic"""
    if not output_path:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        output_path = temp_file.name
        temp_file.close()
    
    # Direct download URL formats to try
    urls = [
        f"https://drive.google.com/uc?id={file_id}&export=download",
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    ]
    
    for retry in range(max_retries):
        for url in urls:
            try:
                # Use requests with a session for better handling
                session = requests.Session()
                response = session.get(url, stream=True, timeout=30)
                
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    # Verify the image
                    try:
                        with Image.open(output_path) as img:
                            img.verify()  # Verify it's a valid image
                        return output_path
                    except Exception as e:
                        print(f"Downloaded file is not a valid image: {e}")
                        # Continue to next URL or retry
                        continue
            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {retry+1}: {e}")
                # Continue to next URL or retry
                continue
        
        # If we get here, all URLs failed on this retry
        if retry < max_retries - 1:
            print(f"Retrying download after {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    print(f"Failed to download file after {max_retries} retries")
    return None

def extract_face_embedding(image_path, face_app):
    """Extract face embedding using InsightFace"""
    try:
        # Use OpenCV to read the image instead of insightface.utils.face_align.read_image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Failed to read image: {image_path}")
            return None
            
        # Convert BGR to RGB (InsightFace expects RGB)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        faces = face_app.get(img)
        
        if not faces:
            return None
            
        # Use the largest face in the image (likely the main subject)
        largest_face = max(faces, key=lambda x: x.bbox[2] * x.bbox[3])
        return largest_face.embedding
    except Exception as e:
        print(f"Error extracting face embedding: {e}")
        return None

def process_photo(photo_url, face_app):
    """Process a single photo from Google Drive URL"""
    try:
        # Extract Drive ID
        drive_id = extract_drive_id(photo_url)
        if not drive_id:
            return {
                "success": False,
                "error": "Invalid Google Drive URL",
                "url": photo_url
            }
        
        # Download photo
        temp_path = download_from_drive(drive_id)
        if not temp_path:
            return {
                "success": False,
                "error": "Failed to download photo",
                "url": photo_url
            }
        
        # Extract embedding
        embedding = extract_face_embedding(temp_path, face_app)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if embedding is None:
            return {
                "success": False,
                "error": "No face detected",
                "url": photo_url
            }
        
        # Convert embedding to list for JSON serialization
        embedding_list = embedding.tolist()
        
        return {
            "success": True,
            "url": photo_url,
            "drive_id": drive_id,
            "embedding": embedding_list
        }
    except Exception as e:
        print(f"Error processing {photo_url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": photo_url
        }

def process_batch(urls, face_app):
    """Process a batch of photo URLs"""
    results = []
    for url in urls:
        result = process_photo(url, face_app)
        results.append(result)
    return results

def insert_to_supabase(photo_data, supabase):
    """Insert photo data into Supabase"""
    try:
        # Insert into photos table - omitting drive_id since it doesn't exist in the table
        result = supabase.table("photos").insert({
            "photo_url": photo_data["url"],
            "embedding": photo_data["embedding"]
        }).execute()
        
        return {
            "success": True,
            "url": photo_data["url"],
            "id": result.data[0]["id"] if result.data else None
        }
    except Exception as e:
        print(f"Error inserting to Supabase: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": photo_data["url"]
        }

def process_urls_file(file_path, batch_size=10):
    """Process a file containing Google Drive URLs"""
    # Initialize face model
    face_app = initialize_face_model()
    if not face_app:
        return {"error": "Failed to initialize face model"}
    
    # Initialize Supabase client
    supabase = get_supabase_client()
    
    # Read URLs from file
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(urls)} URLs to process")
    
    # Process in batches
    batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]
    
    all_results = []
    successful = 0
    failed = 0
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for batch in batches:
            future = executor.submit(process_batch, batch, face_app)
            futures.append(future)
        
        # Process results as they complete
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processing batches"):
            batch_results = future.result()
            
            # Insert successful results to Supabase
            for result in batch_results:
                if result["success"]:
                    insert_result = insert_to_supabase(result, supabase)
                    if insert_result["success"]:
                        successful += 1
                    else:
                        failed += 1
                        result["insert_error"] = insert_result["error"]
                else:
                    failed += 1
                
                all_results.append(result)
    
    elapsed_time = time.time() - start_time
    
    print(f"Processing completed in {elapsed_time:.2f} seconds")
    print(f"Successfully processed and inserted: {successful}")
    print(f"Failed: {failed}")
    
    # Save results to file
    with open("processing_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    return {
        "total": len(urls),
        "successful": successful,
        "failed": failed,
        "elapsed_time": elapsed_time
    }

# FastAPI routes
@app.post("/process_urls")
async def api_process_urls(file: UploadFile = File(...), batch_size: int = Form(10)):
    """API endpoint to process a file containing Google Drive URLs"""
    try:
        # Save uploaded file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(await file.read())
        temp_file.close()
        
        # Process the file
        result = process_urls_file(temp_file.name, batch_size)
        
        # Clean up
        os.unlink(temp_file.name)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_selfie")
async def upload_selfie(
    file: UploadFile = File(...),
    threshold: float = Form(0.8),
    limit: int = Form(1000)
):
    """
    Upload a selfie and find matching photos
    
    - file: The selfie image
    - threshold: Similarity threshold (0.0-1.0)
    - limit: Maximum number of results to return (default 1000 to get all matches)
    """
    try:
        # Initialize face model
        face_app = initialize_face_model()
        if not face_app:
            raise HTTPException(status_code=500, detail="Failed to initialize face model")
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Save uploaded file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(await file.read())
        temp_file.close()
        
        # Extract embedding
        embedding = extract_face_embedding(temp_file.name, face_app)
        
        # Clean up
        os.unlink(temp_file.name)
        
        if embedding is None:
            raise HTTPException(status_code=400, detail="No face detected in the selfie")
        
        # Convert embedding to list
        embedding_list = embedding.tolist()
        
        # Query Supabase for similar faces
        # Note: This requires the pgvector extension and a properly set up table
        result = supabase.rpc(
            "match_faces",
            {
                "query_embedding": embedding_list,
                "match_threshold": threshold,
                "match_limit": limit
            }
        ).execute()
        
        # Format results
        matches = []
        for item in result.data:
            matches.append({
                "id": item["id"],
                "photo_url": item["photo_url"],
                "similarity": item["similarity"]
            })
        
        return {
            "success": True,
            "matches": matches,
            "match_count": len(matches)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/all_photos")
async def all_photos():
    """Get all photos, including both processed and failed ones"""
    try:
        # Get processed photos from Supabase
        supabase = get_supabase_client()
        result = supabase.table("photos").select("id", "photo_url").execute()
        processed_photos = [{"id": item["id"], "photo_url": item["photo_url"], "status": "processed"} for item in result.data]
        
        # Get failed photos from processing_results.json
        failed_photos = []
        if os.path.exists("processing_results.json"):
            with open("processing_results.json", "r") as f:
                results = json.load(f)
                for item in results:
                    if not item["success"]:
                        failed_photos.append({
                            "id": f"failed_{len(failed_photos)}",
                            "photo_url": item["url"],
                            "status": "failed",
                            "reason": item.get("error", "Unknown error")
                        })
        
        return {
            "success": True,
            "processed_count": len(processed_photos),
            "failed_count": len(failed_photos),
            "photos": processed_photos + failed_photos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """API documentation"""
    return {
        "message": "Wedding Photo Finder API",
        "endpoints": [
            {
                "path": "/process_urls",
                "method": "POST",
                "description": "Process a file containing Google Drive URLs"
            },
            {
                "path": "/upload_selfie",
                "method": "POST",
                "description": "Upload a selfie and find matching photos"
            },
            {
                "path": "/all_photos",
                "method": "GET",
                "description": "Get all photos, including both processed and failed ones"
            }
        ]
    }

def main():
    parser = argparse.ArgumentParser(description='Process wedding photos from Google Drive and store in Supabase')
    parser.add_argument('--mode', choices=['process', 'serve'], default='serve',
                        help='Mode: process photos or serve API')
    parser.add_argument('--urls-file', help='File containing Google Drive URLs (one per line)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    parser.add_argument('--port', type=int, default=8000, help='Port for API server')
    
    args = parser.parse_args()
    
    if args.mode == 'process':
        if not args.urls_file:
            print("Error: --urls-file is required in process mode")
            return
            
        process_urls_file(args.urls_file, args.batch_size)
    else:
        # Serve API
        print(f"Starting API server on port {args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)

if __name__ == "__main__":
    main()

