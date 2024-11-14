from flask import Flask, request, jsonify
import re

app = Flask(__name__)
# NEED:Configure IFTTT to Send Data to the Server
# focus on setting up the server and IFTTT integration to ensure smooth data flow
# Endpoint to receive data from IFTTT
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
        # Future work: summarize the video
        return jsonify({
            'message': 'YouTube link detected',
            'tweet_id': tweet_id,
            'author': author,
            'youtube_link': youtube_link
        })
    else:
        return jsonify({'message': 'No YouTube link found'}), 200

# Helper function to find YouTube links in text
def find_youtube_link(text):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    match = re.search(youtube_regex, text)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(6)}"
    return None

if __name__ == '__main__':
    app.run(debug=True)
