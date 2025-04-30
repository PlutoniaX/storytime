import { useState, useEffect, useRef } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const CORRECT_PASSWORD = "bedtime123";

function App() {
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(5);
  const [age, setAge] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [currentStory, setCurrentStory] = useState(null);
  const [previousStories, setPreviousStories] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [password, setPassword] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const audioRef = useRef(null);
  const storyContentRef = useRef(null);

  // Fetch previous stories on component mount
  useEffect(() => {
    fetchStories();
  }, []);

  const fetchStories = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/stories`);
      setPreviousStories(response.data);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching stories:", err);
      setError("Failed to load previous stories. Please try again later.");
      setLoading(false);
    }
  };

  const generateStory = async (e) => {
    e.preventDefault();
    
    if (!prompt.trim()) {
      setError("Please enter a story prompt");
      return;
    }
    
    try {
      setError(null);
      setGenerating(true);
      setProgress(0);
      
      // Start progress simulation
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          // Simulate progress up to 90% (the actual completion will push it to 100%)
          if (prev < 90) {
            return prev + Math.random() * 5;
          }
          return prev;
        });
      }, 500);
      
      // Generate the story
      const response = await axios.post(`${API}/generate-story`, {
        prompt: prompt.trim(),
        age: parseInt(age),
        duration: parseInt(duration)
      });
      
      // Set progress to 100% when done
      clearInterval(progressInterval);
      setProgress(100);
      
      setCurrentStory(response.data);
      
      // Refresh the story list
      fetchStories();
      
      // Small delay to show completed progress bar before resetting
      setTimeout(() => {
        setGenerating(false);
        setProgress(0);
      }, 500);
      
    } catch (err) {
      console.error("Error generating story:", err);
      setError("Failed to generate story. Please try again.");
      setGenerating(false);
      setProgress(0);
    }
  };

  const playAudio = async (storyId) => {
    try {
      setIsPlaying(true);
      
      // Generate the audio if not already done
      const audioResponse = await axios.post(
        `${API}/text-to-speech`,
        { story_id: storyId },
        { responseType: 'blob' }
      );
      
      // Create a blob URL for the audio
      const audioBlob = new Blob([audioResponse.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      
      // Play the audio
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.play();
      }
    } catch (err) {
      console.error("Error playing audio:", err);
      setError("Failed to play the story. Please try again.");
      setIsPlaying(false);
    } finally {
      // Set isPlaying to false when audio ends or if there's an error
      audioRef.current.onended = () => setIsPlaying(false);
    }
  };

  const loadStory = (story) => {
    // Stop audio if playing when switching stories
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
    setCurrentStory(story);
  };

  // Login handling function
  const handleLogin = (e) => {
    e.preventDefault();
    if (password === CORRECT_PASSWORD) {
      setIsAuthenticated(true);
      setPasswordError("");
      // Store in session storage to persist through page refreshes
      sessionStorage.setItem("bedtimeAuth", "true");
    } else {
      setPasswordError("Incorrect password. Please try again.");
    }
  };

  // Check for stored authentication on mount
  useEffect(() => {
    const storedAuth = sessionStorage.getItem("bedtimeAuth");
    if (storedAuth === "true") {
      setIsAuthenticated(true);
    }
  }, []);

  // Scroll to story content when a story is loaded
  useEffect(() => {
    if (currentStory && storyContentRef.current) {
      storyContentRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      });
    }
  }, [currentStory]);

  return (
    <div className="app-container">
      <header className="header">
        <h1 className="title">Bedtime Story Generator</h1>
        <p className="subtitle">Create magical bedtime stories for your child</p>
      </header>

      {!isAuthenticated ? (
        <div className="login-container">
          <div className="login-card">
            <h2>Password Required</h2>
            <p>Please enter the password to access bedtime stories.</p>
            <form onSubmit={handleLogin} className="login-form">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="password-input"
                required
              />
              {passwordError && <div className="password-error">{passwordError}</div>}
              <button type="submit" className="login-btn">Enter</button>
            </form>
          </div>
        </div>
      ) : (
        <main className="main-content" ref={storyContentRef}>
        <section className="story-generator">
          <form onSubmit={generateStory} className="story-form">
            <div className="form-group">
              <label htmlFor="prompt">Story Prompt:</label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter a theme or topic for your bedtime story (e.g., 'a brave little dragon learning to fly')"
                required
                className="story-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="age">Child's Age:</label>
              <div className="age-slider">
                <input
                  type="range"
                  id="age"
                  min="0"
                  max="12"
                  step="1"
                  value={age}
                  onChange={(e) => setAge(parseInt(e.target.value))}
                  className="slider"
                />
                <span className="age-value">
                  {age === 0 ? "Under 1 year" : `${age} years old`}
                </span>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="duration">Story Duration (minutes):</label>
              <div className="duration-slider">
                <input
                  type="range"
                  id="duration"
                  min="3"
                  max="15"
                  step="1"
                  value={duration}
                  onChange={(e) => setDuration(parseInt(e.target.value))}
                  className="slider"
                />
                <span className="duration-value">{duration} minutes</span>
              </div>
            </div>

            <button 
              type="submit" 
              className="generate-btn"
              disabled={generating}
            >
              {generating ? 
                <div className="generating-container">
                  <span>Generating Story...</span>
                  <div className="progress-container">
                    <div 
                      className="progress-bar" 
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>
                : 
                "Generate Bedtime Story"
              }
            </button>
          </form>

          {error && <div className="error-message">{error}</div>}
        </section>

        {currentStory && (
          <section className="current-story">
            <div className="story-content">
              <div className="story-header">
                <h2>{currentStory.content.split("\n")[0]}</h2>
                <div className="story-meta">
                  <span>{new Date(currentStory.created_at).toLocaleDateString()}</span>
                  <span>{currentStory.duration} minute story</span>
                </div>
              </div>
              
              {currentStory.image_url && (
                <div className="story-image">
                  <img src={currentStory.image_url} alt="Story illustration" />
                </div>
              )}
              
              <div className="story-text">
                {currentStory.content.split("\n").slice(1).map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
              
              <div className="story-controls">
                <button
                  className="play-btn"
                  onClick={() => playAudio(currentStory.id)}
                  disabled={isPlaying}
                >
                  {isPlaying ? "Playing..." : "Read Aloud"}
                </button>
                <audio 
                  ref={audioRef}
                  onEnded={() => setIsPlaying(false)}
                  onError={() => {
                    setError("Failed to play audio. Please try again.");
                    setIsPlaying(false);
                  }}
                />
              </div>
            </div>
          </section>
        )}

        <section className="previous-stories">
          <h2 className="section-title">Previous Stories</h2>
          
          {loading ? (
            <p>Loading previous stories...</p>
          ) : previousStories.length > 0 ? (
            <div className="story-list">
              {previousStories.map((story) => (
                <div 
                  key={story.id} 
                  className="story-card"
                  onClick={() => loadStory(story)}
                >
                  <div className="story-card-content">
                    <h3>{story.content.split("\n")[0]}</h3>
                    <p className="story-prompt">{story.prompt}</p>
                    <div className="story-meta">
                      <span>{new Date(story.created_at).toLocaleDateString()}</span>
                      <span>{story.duration} min</span>
                    </div>
                  </div>
                  {story.image_url && (
                    <div className="story-card-image">
                      <img src={story.image_url} alt="Story thumbnail" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p>No previous stories yet. Generate your first story!</p>
          )}
        </section>
      </main>

        <footer className="footer">
          <p>© 2025 Bedtime Story Generator - Made with love for sleepy children everywhere</p>
        </footer>
      )}
    </div>
  );
}

export default App;
