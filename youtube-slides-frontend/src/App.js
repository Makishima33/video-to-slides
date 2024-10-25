import React, { useState } from "react";
import "./App.css";

function App() {
  const [youtubeLink, setYoutubeLink] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [slides, setSlides] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!youtubeLink) return;

    setIsLoading(true);

    // Extract video ID from YouTube URL
    const videoId = youtubeLink.split("v=")[1] || youtubeLink.split("/")[3];

    // Send the video ID to the backend
    const response = await fetch(
      `http://127.0.0.1:5000/api/generate-slides/${videoId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    const data = await response.json();
    setSlides(data);
    setIsLoading(false);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>YouTube Slide Generator</h1>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Enter YouTube link"
            value={youtubeLink}
            onChange={(e) => setYoutubeLink(e.target.value)}
            required
          />
          <button type="submit">Generate Slides</button>
        </form>
        {isLoading && <p>Generating slides...</p>}
        {slides && (
          <div>
            <h2>Slides Generated</h2>
            <pre>{JSON.stringify(slides, null, 2)}</pre>
          </div>
        )}
      </header>
    </div>
  );
}

export default App;
