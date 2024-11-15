from flask import Flask, jsonify, request
from flask_cors import CORS # type: ignore
import os
import requests

app = Flask(__name__)
CORS(app)

# Function to find a YouTube link within a tweet's text
def find_youtube_link(tweet_content):
    if "youtube.com" in tweet_content or "youtu.be" in tweet_content:
        parts = tweet_content.split()
        for part in parts:
            if "youtube.com" in part or "youtu.be" in part:
                return part 
    return None

# Function to call endpoint for slide generation
def generate_slides(video_id):
    try:
        url = f"http://ec2-3-133-134-57.us-east-2.compute.amazonaws.com/api/youtube2slides/generate-slides/{video_id}"
        
        # Make the POST request
        response = requests.post(url)
        
        # Check for successful response
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error generating slides: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred while generating slides: {str(e)}")
        return None

# Endpoint to receive tweet data and process it
@app.route('/api/tweet', methods=['POST'])
def receive_tweet():
    data = request.json

    if not data or 'tweet_content' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    tweet_content = data['tweet_content']
    tweet_id = data.get('tweet_id')
    author = data.get('author')

    # Check for YouTube link in tweet content
    youtube_link = find_youtube_link(tweet_content)
    if youtube_link:
        # Extract video ID from the YouTube link
        video_id = youtube_link.split("v=")[1] if "v=" in youtube_link else youtube_link.split("/")[-1]

        # Generate slides using endpoints
        slide_data = generate_slides(video_id)

        if slide_data:
            return jsonify({
                'message': 'Slides generated successfully',
                'tweet_id': tweet_id,
                'author': author,
                'youtube_link': youtube_link,
                'slides': slide_data
            }), 200
        else:
            return jsonify({'error': 'Failed to generate slides'}), 500
    else:
        return jsonify({'message': 'No YouTube link found'}), 200

if __name__ == '__main__':
    app.run(debug=True)
