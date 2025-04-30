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
            
        # First detect the language of the prompt using Gemini
        language_detection = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            headers={
                "Content-Type": "application/json"
            },
            params={
                "key": gemini_api_key
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Identify the language of the following text. Respond with ONLY the language name in English. For example: 'English', 'Spanish', 'French', etc.\n\nText: " + request.prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 50
                }
            }
        )
        
        if language_detection.status_code != 200:
            language = "English"  # Default to English if detection fails
        else:
            try:
                language = language_detection.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError):
                language = "English"  # Default to English if parsing fails
            
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

        # Generate story content using Gemini API (direct HTTP request)
        prompt = f"""You are a children's bedtime story creator. Create a {request.duration} minute {complexity} bedtime story appropriate for {age_guidance} Make it engaging, descriptive, and with a positive message. Include a title at the beginning. The story should be written in {language}.

Create a bedtime story about: {request.prompt}"""
        
        story_response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            headers={
                "Content-Type": "application/json"
            },
            params={
                "key": gemini_api_key
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": max_tokens
                }
            }
        )
        
        if story_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error from Gemini API: {story_response.text}")
        
        try:
            story_content = story_response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            raise HTTPException(status_code=500, detail="Failed to parse story content from Gemini API")
        
        # Generate an image for the story using Gemini's Imagen model
        image_prompt = f"A children's book illustration for a story about {request.prompt}, suitable for a {request.age} year old child. Cute, colorful, child-friendly style with subtle 3D effect."
        
        image_response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            headers={
                "Content-Type": "application/json"
            },
            params={
                "key": gemini_api_key
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Generate a high-quality image: {image_prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4
                }
            }
        )
        
        if image_response.status_code != 200:
            # If Gemini image generation fails, use a placeholder image
            logging.error(f"Error from Gemini Image API: {image_response.text}")
            image_url = f"https://source.unsplash.com/random/1024x1024/?children,story,{request.prompt.replace(' ', ',')}"
        else:
            try:
                # Try to extract the image URL from Gemini's response
                response_data = image_response.json()
                
                # Extract the image URL if it's in the expected format
                if "candidates" in response_data and len(response_data["candidates"]) > 0:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "inlineData" in part and "data" in part["inlineData"]:
                                # Handle base64 image data if provided
                                image_base64 = part["inlineData"]["data"]
                                # Here we'd normally save this to a file or cloud storage
                                # For simplicity, we'll use a placeholder URL
                                image_url = f"https://source.unsplash.com/random/1024x1024/?children,story,{request.prompt.replace(' ', ',')}"
                                break
                            if "text" in part and "http" in part["text"]:
                                # Try to extract URL from text response
                                import re
                                urls = re.findall(r'https?://\S+', part["text"])
                                if urls:
                                    image_url = urls[0].strip('.,;()"\'')
                                    break
                
                # If we couldn't extract an image, use a placeholder
                if 'image_url' not in locals():
                    image_url = f"https://source.unsplash.com/random/1024x1024/?children,story,{request.prompt.replace(' ', ',')}"
            except Exception as e:
                logging.error(f"Error parsing Gemini image response: {str(e)}")
                image_url = f"https://source.unsplash.com/random/1024x1024/?children,story,{request.prompt.replace(' ', ',')}"
        
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
        
        # Detect language of the story using Gemini
        language_detection = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            headers={
                "Content-Type": "application/json"
            },
            params={
                "key": gemini_api_key
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Identify the language of the following text. Respond with ONLY the language name in English. For example: 'English', 'Spanish', 'French', etc.\n\nText: " + story.content[:200]  # First 200 chars should be enough
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 50
                }
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
