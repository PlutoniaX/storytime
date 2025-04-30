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

- `GEMINI_API_KEY`: For Google Gemini story and image generation
- `OPENAI_API_KEY`: For text-to-speech functionality
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

## Deployment Instructions

### Local Deployment

1. **Prerequisites**:
   - Node.js 16+ and npm/yarn
   - Python 3.8+
   - MongoDB

2. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd bedtime-story-generator
   ```

3. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Create a .env file in the backend directory**:
   ```
   MONGO_URL="mongodb://localhost:27017"
   DB_NAME="bedtime_stories"
   GEMINI_API_KEY="your_gemini_api_key"
   OPENAI_API_KEY="your_openai_api_key"
   ```

5. **Frontend Setup**:
   ```bash
   cd frontend
   yarn install
   ```

6. **Create a .env file in the frontend directory**:
   ```
   REACT_APP_BACKEND_URL="http://localhost:8001"
   ```

7. **Start the Development Servers**:
   ```bash
   # In backend directory
   uvicorn server:app --host 0.0.0.0 --port 8001 --reload

   # In frontend directory (another terminal)
   yarn start
   ```

### Cloud Deployment

#### Deploy on Vercel or Netlify (Frontend)

1. Create a new project on Vercel or Netlify
2. Link to your GitHub repository
3. Set the build command to `cd frontend && yarn install && yarn build`
4. Set the publish directory to `frontend/build`
5. Add environment variables (REACT_APP_BACKEND_URL pointing to your backend)

#### Deploy Backend on Render or Railway

1. Create a new web service on Render or Railway
2. Link to your GitHub repository
3. Set the build command to `cd backend && pip install -r requirements.txt`
4. Set the start command to `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Add all required environment variables
6. Deploy!

#### Database Setup (MongoDB Atlas)

1. Create a free MongoDB Atlas account
2. Create a new cluster
3. Set up database access (username/password)
4. Get your connection string
5. Add it to your backend environment variables

## Future Enhancements

- User accounts for personalized story collections
- More customization options (age range, moral lessons, etc.)
- Multiple illustration styles and voice options
- Downloadable PDFs and audio files
- Bedtime music integration

---

Created with ❤️ for sleepy children everywhere
