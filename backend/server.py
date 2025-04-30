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

# API keys
openai_api_key = os.environ.get('OPENAI_API_KEY')
gemini_api_key = os.environ.get('GEMINI_API_KEY')

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
            max_tokens = 800
            complexity = "simple"
        elif request.duration <= 10:
            max_tokens = 1500
            complexity = "moderate"
        else:
            max_tokens = 2500
            complexity = "complex"
            
        # First detect the language of the prompt
        language_detection = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "Identify the language of the following text. Respond with ONLY the language name in English. For example: 'English', 'Spanish', 'French', etc."},
                    {"role": "user", "content": request.prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.3,
            }
        )
        
        if language_detection.status_code != 200:
            language = "English"  # Default to English if detection fails
        else:
            language = language_detection.json()["choices"][0]["message"]["content"].strip()
            
        # Create age-appropriate instruction
        age_guidance = ""
        if request.age == 0:
            age_guidance = "infants under 1 year old. Use extremely simple words, very short sentences, and lots of repetition. Focus on colors, shapes, sounds, and familiar objects. Keep it very short with rhythmic patterns."
        elif request.age <= 3:
            age_guidance = "very young children (1-3 years old). Use simple words, short sentences, and repetitive elements. Focus on basic concepts and familiar objects."
        elif request.age <= 6:
            age_guidance = "preschool children (4-6 years old). Use simple language with some new vocabulary. Include simple moral lessons and gentle adventure."
        elif request.age <= 9:
            age_guidance = "elementary school children (7-9 years old). Use moderate vocabulary with some challenge words. Include more complex storylines with clear moral lessons."
        else:
            age_guidance = "older children (10-12 years old). Use rich vocabulary and more complex sentence structures. Include more sophisticated themes while maintaining age-appropriate content."

        # Generate story content using OpenAI API (direct HTTP request)
        system_prompt = f"You are a children's bedtime story creator. Create a {request.duration} minute {complexity} bedtime story appropriate for {age_guidance} Make it engaging, descriptive, and with a positive message. Include a title at the beginning. The story should be written in {language}."
        
        story_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": system_prompt},
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
        image_prompt = f"A children's book illustration for a story about {request.prompt}, suitable for a {request.age} year old child. Cute, colorful, child-friendly style with 3D pop effect."
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
        
        # Detect language of the story
        language_detection = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "Identify the language of the following text. Respond with ONLY the language name in English. For example: 'English', 'Spanish', 'French', etc."},
                    {"role": "user", "content": story.content[:200]}  # First 200 chars should be enough
                ],
                "max_tokens": 50,
                "temperature": 0.3,
            }
        )
        
        # Select appropriate voice based on language
        if language_detection.status_code != 200:
            voice = "nova"  # Default to Nova if detection fails
        else:
            language = language_detection.json()["choices"][0]["message"]["content"].strip().lower()
            
            # Map languages to appropriate voices
            # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
            voice_map = {
                "english": "nova",
                "spanish": "alloy",
                "french": "alloy",
                "german": "alloy",
                "italian": "alloy",
                "portuguese": "alloy",
                "japanese": "alloy",
                "chinese": "alloy",
                "arabic": "alloy",
                "hindi": "alloy",
                "russian": "alloy"
            }
            
            voice = voice_map.get(language, "alloy")  # Default to alloy for other languages
        
        # Generate speech using OpenAI API (direct HTTP request)
        speech_response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "tts-1",
                "voice": voice,
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
