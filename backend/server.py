from fastapi import FastAPI, APIRouter, HTTPException, Body
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import json
import base64
import requests
from fastapi.responses import StreamingResponse
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI API key
openai_api_key = os.environ.get('OPENAI_API_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class Story(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    duration: int  # in minutes
    content: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StoryRequest(BaseModel):
    prompt: str
    duration: int  # in minutes
    age: Optional[int] = 5  # default age if not provided

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/generate-story", response_model=Story)
async def generate_story(request: StoryRequest):
    try:
        # Determine story length based on duration
        if request.duration <= 5:
            max_tokens = 500
            complexity = "simple"
        elif request.duration <= 10:
            max_tokens = 1000
            complexity = "moderate"
        else:
            max_tokens = 1500
            complexity = "complex"

        # Generate story content using OpenAI API (direct HTTP request)
        story_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": f"You are a children's bedtime story creator. Create a {request.duration} minute {complexity} bedtime story appropriate for young children. Make it engaging, descriptive, and with a positive message. Include a title at the beginning."},
                    {"role": "user", "content": f"Create a bedtime story about: {request.prompt}"}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }
        )
        
        if story_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error from OpenAI API: {story_response.text}")
        
        story_content = story_response.json()["choices"][0]["message"]["content"].strip()
        
        # Generate an image for the story using DALL-E API (direct HTTP request)
        image_prompt = f"A children's book illustration for a story about {request.prompt}. Cute, colorful, child-friendly style."
        image_response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",
                "prompt": image_prompt,
                "size": "1024x1024",
                "quality": "standard",
                "n": 1,
            }
        )
        
        if image_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error from OpenAI Image API: {image_response.text}")
        
        image_url = image_response.json()["data"][0]["url"]
        
        # Create a story object
        story = Story(
            prompt=request.prompt,
            duration=request.duration,
            content=story_content,
            image_url=image_url
        )
        
        # Save to database
        await db.stories.insert_one(story.dict())
        
        return story
    
    except Exception as e:
        logging.error(f"Error generating story: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating story: {str(e)}")

@api_router.post("/text-to-speech")
async def text_to_speech(story_id: dict = Body(...)):
    try:
        # Extract story_id from the request body
        if not isinstance(story_id, dict) or "story_id" not in story_id:
            raise HTTPException(status_code=422, detail="Request body must contain 'story_id' field")
        
        story_id_str = story_id.get("story_id")
        
        # Get the story from the database
        story_doc = await db.stories.find_one({"id": story_id_str})
        if not story_doc:
            raise HTTPException(status_code=404, detail="Story not found")
        
        story = Story(**story_doc)
        
        # Generate speech using OpenAI API (direct HTTP request)
        speech_response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "tts-1",
                "voice": "nova",
                "input": story.content
            },
            stream=True
        )
        
        if speech_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error from OpenAI TTS API: {speech_response.text}")
        
        # Convert to streaming response
        def iterfile():
            for chunk in speech_response.iter_content(chunk_size=8192):
                yield chunk
        
        # Save audio URL to the database (would typically save to cloud storage in production)
        story.audio_url = f"/api/audio/{story_id_str}"
        await db.stories.update_one(
            {"id": story_id_str},
            {"$set": {"audio_url": story.audio_url}}
        )
        
        return StreamingResponse(iterfile(), media_type="audio/mpeg")
    
    except Exception as e:
        logging.error(f"Error generating speech: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating speech: {str(e)}")

@api_router.get("/stories", response_model=List[Story])
async def get_stories():
    try:
        stories = await db.stories.find().sort("created_at", -1).to_list(20)
        return [Story(**story) for story in stories]
    except Exception as e:
        logging.error(f"Error retrieving stories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stories: {str(e)}")

@api_router.get("/story/{story_id}", response_model=Story)
async def get_story(story_id: str):
    try:
        story = await db.stories.find_one({"id": story_id})
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        return Story(**story)
    except Exception as e:
        logging.error(f"Error retrieving story: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving story: {str(e)}")

# Status check routes (from template)
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
