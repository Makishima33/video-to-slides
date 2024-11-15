from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import httpx

app = Flask(__name__)
CORS(app)
# Set up the YouTube API client
api_key = os.getenv('YOUTUBE_API_KEY')
if not api_key:
    raise ValueError("API key is missing. Ensure the '.env' file contains the 'YOUTUBE_API_KEY' key.")

youtube = build('youtube', 'v3', developerKey=api_key)

# Function to retrieve video metadata
def get_video_metadata(video_id):
    try:
        request = youtube.videos().list(
            part='snippet,contentDetails',
            id=video_id
        )
        response = request.execute()
        video_info = response.get('items', [])[0]['snippet']

        # Get the highest quality thumbnail available
        thumbnails = video_info.get('thumbnails', {})
        thumbnail_url = thumbnails.get('maxres', {}).get('url') or \
                        thumbnails.get('high', {}).get('url') or \
                        thumbnails.get('default', {}).get('url')

        metadata = {
            'title': video_info.get('title'),
            'description': video_info.get('description'),
            'thumbnail_url': thumbnail_url  # Add thumbnail URL to metadata
        }

        return metadata
    except Exception as e:
        print(f"Error retrieving metadata: {e}")
        return None


# Function to retrieve video transcript
def get_video_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item['text'] for item in transcript])
        return transcript_text
    except Exception as e:
        print(f"Error retrieving transcript: {e}")
        return None
# Function to generate a summary using Azure OpenAI
def generate_summary(transcript):
    try:
        AZURE_OPENAI_KEY_USEAST = os.getenv("AZURE_OPENAI_KEY_USEAST")
        ENDPOINT_USEAST = os.getenv("ENDPOINT_USEAST")
        if not AZURE_OPENAI_KEY_USEAST or not ENDPOINT_USEAST:
            raise ValueError("Azure OpenAI credentials are missing.")

        endpoint = ENDPOINT_USEAST
        deployment_id = "gpt-4o"
        api_key = AZURE_OPENAI_KEY_USEAST

        url = f"{endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version=2024-09-01-preview"

        # Prompt to generate a concise summary of the transcript
        prompt = f"""
        Create a concise and informative summary for the following video transcript:

        Transcript: {transcript}

        The summary should highlight the main points discussed in the video, keeping it brief and informative.
        """

        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.5
        }

        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }

        response = httpx.post(url, json=data, headers=headers, timeout=120)
        response.raise_for_status()

        result = response.json()
        summary = result['choices'][0]['message']['content'].strip()
        return summary

    except Exception as e:
        print(f"Error generating summary with Azure OpenAI: {e}")
        return "Error generating summary."

# Function to split transcript into subtopics using Azure OpenAI GPT-4o
def identify_subtopics_with_azure_openai(transcript):
    try:
        AZURE_OPENAI_KEY_USEAST = os.getenv("AZURE_OPENAI_KEY_USEAST")
        ENDPOINT_USEAST = os.getenv("ENDPOINT_USEAST")
        if not AZURE_OPENAI_KEY_USEAST or not ENDPOINT_USEAST:
            raise ValueError("Azure OpenAI credentials are missing.")

        endpoint = ENDPOINT_USEAST
        deployment_id = "gpt-4o"
        api_key = AZURE_OPENAI_KEY_USEAST

        url = f"{endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version=2024-09-01-preview"

        prompt = f"""
        Analyze the following video transcript and return a structured list of subtopics.
        For each subtopic, include a brief summary and the text that corresponds to that subtopic.

        Transcript: {transcript}
        
        Format the response like this:
        - Subtopic 1: (Subtopic title here)
          Text: (corresponding text here)
        - Subtopic 2: (Subtopic title here)
          Text: (corresponding text here)
        """

        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }

        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }

        response = httpx.post(url, json=data, headers=headers, timeout=120)
        response.raise_for_status()

        result = response.json()
        subtopic_data = result['choices'][0]['message']['content'].strip()
        return subtopic_data

    except Exception as e:
        print(f"Error identifying subtopics with Azure OpenAI GPT-4o: {e}")
        return None

# Parse the subtopics returned by GPT-4o
def parse_subtopics(subtopic_text):
    sections = subtopic_text.split("\n- ")
    subtopics = {}

    for section in sections:
        try:
            if "Subtopic" in section:
                title_line, text_line = section.split("\n  Text: ")
                
                title = title_line.replace("Subtopic", "").strip(": ").lstrip("- ").strip()
                
                # Store the cleaned title and the corresponding text
                subtopics[title] = text_line.strip()
        except ValueError as e:
            # Log the error and the section causing it
            print(f"Error processing section: {section} - {str(e)}")
            continue
    
    return subtopics


# Step 3: Summarize the content for each subtopic using GPT-4o
def summarize_content_with_azure_openai(transcript_section):
    """
    Summarize the transcript section into subtopics and content using Azure OpenAI GPT-4o.
    """
    try:
        AZURE_OPENAI_KEY_USEAST = os.getenv("AZURE_OPENAI_KEY_USEAST")
        ENDPOINT_USEAST = os.getenv("ENDPOINT_USEAST")
        if not AZURE_OPENAI_KEY_USEAST or not ENDPOINT_USEAST:
            raise ValueError("Azure OpenAI credentials are missing.")
        
        endpoint = ENDPOINT_USEAST
        deployment_id = "gpt-4o"
        api_key = AZURE_OPENAI_KEY_USEAST

        url = f"{endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version=2024-09-01-preview"

        prompt = f"""
        Based on the following video transcript section, create content for a slide presentation. 
        Please provide the output formatted as follows:
        
        - Head: A short sentence summarizing the overall theme of the section.
        - Title: A concise and relevant title for the slide.
        - Subtopic: A subheading that captures the key focus of the section.
        - Content: A list of bullet points summarizing the main points from the section. Should be less than 7 bullet points.

        Transcript Section: {transcript_section}
        
        Format the response exactly in the following format:
        Head: (provide the head text here)
        Title: (provide the title text here)
        Subtopic: (provide the subtopic text here)
        Content: 
        (provide the first bullet point here)
        (provide the second bullet point here)
        (and so on, each bullet point on a new line)
        """

        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.5
        }

        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }

        response = httpx.post(url, json=data, headers=headers, timeout=120)
        response.raise_for_status()

        result = response.json()
        summary = result['choices'][0]['message']['content'].strip()
        return summary

    except Exception as e:
        print(f"Error generating summary with Azure OpenAI GPT-4o: {e}")
        return None

# Step 4: Parse the GPT output into a structured slide object
def parse_gpt_output(output_text):
    lines = output_text.split("\n")
    
    # Extract head, title, and subtopic
    head = lines[0].replace("Head:", "").strip()
    title = lines[1].replace("Title:", "").strip()
    subtopic = lines[2].replace("Subtopic:", "").strip()
    content = [line.strip().replace("-", "", 1).strip() for line in lines[4:] if line.startswith("-")]

    return head, title, subtopic, content

def create_cover_page(title, thumbnail_url, user_name="Created using ChatSlide"):
    cover_slide = {
        "head": "",
        "title": "",  
        "subtopic": "",  
        "userName": user_name,
        "template": "Default",
        "content": [],
        "images": [],
        "media_types": [],
        "chart": [],
        "image_positions": [],
        "layout": "Blank_layout",
        "logo": "Default",
        "additional_images": [],
        "palette": "",
        "transcript": "",
        "logo_url": "",
        "background_url": thumbnail_url,
        "background_color": "",
        "titleFontFamily": "",
        "subtitleFontFamily": "",
        "contentFontFamily": ""
    }
    
    return cover_slide

def create_slide_objects_for_subtopics(metadata, subtopics):
    slides = {}
    cover_slide = create_cover_page(metadata['title'], metadata['thumbnail_url'])
    slides[0] = cover_slide
    for i, (subtopic, text) in enumerate(subtopics.items(), 1):
        transcript_summary = summarize_content_with_azure_openai(text)
        
        if transcript_summary:
            head, title_text, subtopic, content = parse_gpt_output(transcript_summary)
            slides[i] = {
                "head": head,
                "title": title_text,
                "subtopic": subtopic,
                "userName": "Created using ChatSlide",
                "template": "Creative_Brief_011",
                "content": content,
                "images": [], 
                "media_types": [],
                "chart": [],
                "image_positions": [],
                "layout": "Col_1_img_0_layout", 
                "logo": "Default",
                "additional_images": [],
                "palette": "",
                "transcript": "",
                "logo_url": "",
                "background_url": "",
                "background_color": "",
                "titleFontFamily": "",
                "subtitleFontFamily": "",
                "contentFontFamily": ""
            }

    return slides
# Function to generate a short comment using Azure OpenAI
def generate_short_comment_with_azure(video_title, video_summary):
    try:
        AZURE_OPENAI_KEY_USEAST = os.getenv("AZURE_OPENAI_KEY_USEAST")
        ENDPOINT_USEAST = os.getenv("ENDPOINT_USEAST")
        if not AZURE_OPENAI_KEY_USEAST or not ENDPOINT_USEAST:
            raise ValueError("Azure OpenAI credentials are missing.")

        endpoint = ENDPOINT_USEAST
        deployment_id = "gpt-4o"
        api_key = AZURE_OPENAI_KEY_USEAST

        url = f"{endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version=2024-09-01-preview"

        prompt = f"""
        Create a two-sentence comment based on what was learned from this video and how ChatSlide was used to make slides:
        
        Video Title: {video_title}
        Video Summary: {video_summary}
        
        Format:
        "I'm glad to share that I have learned [key insights] from this video and I made slides using ChatSlide: <link to the slides> to help me [purpose]."
        """

        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }

        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }

        response = httpx.post(url, json=data, headers=headers, timeout=120)
        response.raise_for_status()

        result = response.json()
        comment = result['choices'][0]['message']['content'].strip()
        return comment

    except Exception as e:
        print(f"Error generating comment with Azure OpenAI: {e}")
        return "Error generating comment."

@app.route('/api/generate-slides/<video_id>', methods=['POST'])
def generate_slides(video_id):
    try:
        if not isinstance(video_id, str):
            return jsonify({'error': 'Invalid video ID'}), 400
        
        print(f"Video ID received: {video_id}")
        
        # Process the video and generate slides
        metadata = get_video_metadata(video_id)
        if not metadata:
            print("Error retrieving metadata")
            return jsonify({'error': 'Unable to retrieve video metadata'}), 400
        
        
        transcript = get_video_transcript(video_id)
        if not transcript:
            print("Error retrieving transcript")
            return jsonify({'error': 'Unable to retrieve video transcript'}), 400
        
        
        if metadata and transcript:
            
            # Identify subtopics using Azure OpenAI
            subtopic_text = identify_subtopics_with_azure_openai(transcript)
            if not subtopic_text:
                print("Error identifying subtopics")
                return jsonify({'error': 'Unable to retrieve subtopics from transcript'}), 400
            
            
            subtopics = parse_subtopics(subtopic_text)
            
            
            slides = create_slide_objects_for_subtopics(metadata, subtopics)
            first_slide = slides[0]

            return jsonify(slides), 200     
        else:
            return jsonify({'error': 'Unable to retrieve metadata or transcript'}), 400
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-comment/<video_id>', methods=['POST'])
def generate_comment(video_id):
    try:
        metadata = get_video_metadata(video_id)
        if not metadata:
            return jsonify({'error': 'Unable to retrieve video metadata'}), 400
        
        transcript = get_video_transcript(video_id)
        if not transcript:
            return jsonify({'error': 'Unable to retrieve video transcript'}), 400

        video_title = metadata['title']
        video_summary = generate_summary(transcript)
        
        comment = generate_short_comment_with_azure(video_title, video_summary)
        
        return jsonify({'comment': comment}), 200
    except Exception as e:
        print(f"Error generating comment: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)