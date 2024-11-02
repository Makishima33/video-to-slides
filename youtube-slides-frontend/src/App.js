import React, { useState } from "react";
import "./App.css";

function App() {
  const [youtubeLink, setYoutubeLink] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [slides, setSlides] = useState(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");

  const extractVideoId = (url) => {
    try {
      const urlObj = new URL(url);
      if (urlObj.hostname === "youtu.be") {
        return urlObj.pathname.slice(1);
      } else if (urlObj.hostname.includes("youtube.com")) {
        return urlObj.searchParams.get("v");
      }
    } catch {
      return null;
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSlides(null);
    setComment("");

    if (!youtubeLink) {
      setError("Please enter a valid YouTube link.");
      return;
    }

    const videoId = extractVideoId(youtubeLink);
    if (!videoId) {
      setError("Invalid YouTube link. Please try again.");
      return;
    }

    setIsLoading(true);

    try {
      const slidesResponse = await fetch(
        `http://127.0.0.1:5000/api/generate-slides/${videoId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!slidesResponse.ok) {
        throw new Error("Failed to generate slides.");
      }

      const slidesData = await slidesResponse.json();
      setSlides(slidesData);

      const commentResponse = await fetch(
        `http://127.0.0.1:5000/api/generate-comment/${videoId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!commentResponse.ok) {
        throw new Error("Failed to generate comment.");
      }

      const commentData = await commentResponse.json();
      setComment(commentData.comment);
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
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
            className="input-field"
          />
          <button type="submit" className="submit-button">
            Generate Slides
          </button>
        </form>

        {isLoading && (
          <p className="loading-text">Generating slides and comment...</p>
        )}
        {error && <p className="error-text">{error}</p>}

        {comment && (
          <div className="comment-section">
            <h2>Generated Comment</h2>
            <p className="comment-text">{comment}</p>
          </div>
        )}

        {slides && (
          <div className="slides-section">
            <h2>Slides Generated</h2>
            <pre className="slides-json">{JSON.stringify(slides, null, 2)}</pre>
          </div>
        )}
      </header>
    </div>
  );
}

export default App;
