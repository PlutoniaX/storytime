# Bedtime Story Generator

A magical app that creates personalized bedtime stories for children with just a few clicks. Generate engaging, age-appropriate stories with beautiful illustrations and audio narration.

## Features

- **Story Generation**: Create custom bedtime stories based on any prompt (e.g., "a brave little dragon learning to fly")
- **Duration Control**: Adjust story length from 3-15 minutes to perfectly fit your bedtime routine
- **Beautiful Illustrations**: Each story comes with a custom-generated, child-friendly illustration
- **Audio Narration**: Have the story read aloud with a soothing voice
- **Story History**: Access previously generated stories anytime

## Technology Stack

- **Frontend**: React with Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI Services**:
  - OpenAI GPT-4 for story generation
  - DALL-E 3 for image generation
  - OpenAI TTS (Text-to-Speech) for audio narration

## How to Use

1. **Enter a Story Prompt**:
   - Type any theme, character, or scenario you'd like the story to be about
   - Be as specific or imaginative as you want (e.g., "a friendly octopus who helps clean the ocean")

2. **Set Story Duration**:
   - Use the slider to select how long you want the story to be (3-15 minutes)
   - Shorter stories are simpler, while longer stories are more complex

3. **Generate the Story**:
   - Click "Generate Bedtime Story" and wait while magic happens
   - The app creates a unique story with title, content, and illustration

4. **Read and Listen**:
   - Once generated, you can read the story on screen
   - Click "Read Aloud" to have the story narrated
   - View the beautiful illustration that accompanies your tale

5. **Access Previous Stories**:
   - Scroll down to see all previously generated stories
   - Click on any story card to view it again

## Development and Setup

### Environment Variables

The app requires the following environment variables:

- `OPENAI_API_KEY`: For GPT-4, DALL-E, and TTS functionality
- `MONGO_URL`: MongoDB connection string
- `DB_NAME`: Database name

### Running the App

**Backend**:
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend**:
```bash
cd frontend
yarn install
yarn start
```

## Future Enhancements

- User accounts for personalized story collections
- More customization options (age range, moral lessons, etc.)
- Multiple illustration styles and voice options
- Downloadable PDFs and audio files
- Bedtime music integration

---

Created with ❤️ for sleepy children everywhere
