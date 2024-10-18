import os
import json
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import httpx

# Set up the YouTube API client
api_key = os.getenv('YOUTUBE_API_KEY')
if not api_key:
    raise ValueError("API key is missing. Ensure the '.env' file contains the 'YOUTUBE_API_KEY' key.")

youtube = build('youtube', 'v3', developerKey=api_key)

# Function to retrieve video metadata
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
        if "Subtopic" in section:
            title_line, text_line = section.split("\n  Text: ")
            title = title_line.replace("Subtopic", "").strip(": ")
            subtopics[title] = text_line.strip()
    
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
    
    # Remove any leading hyphen and extra spaces in subtopic
    # subtopic = subtopic.lstrip("-").strip().replace("-", "")
    
    # Extract content bullet points without the leading '-'
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

# Create slide objects for each subtopic
def create_slide_objects_for_subtopics(metadata, subtopics):
    slides = {}
    cover_slide = create_cover_page(metadata['title'], metadata['thumbnail_url'])
    slides[0] = cover_slide
    for i, (subtopic, text) in enumerate(subtopics.items(), 1):
        transcript_summary = summarize_content_with_azure_openai(text)
        
        if transcript_summary:
            head, title_text, subtopics, content = parse_gpt_output(transcript_summary)
            slide = {
                "head": head,
                "title": title_text,
                "subtopic": subtopics,
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
            slides[f"{i}"] = slide

    return slides

# Main function to retrieve video content and generate the slides
def main():
    video_id = 'ML-Rg0XIikA'

    # Step 1: Retrieve video metadata
    metadata = get_video_metadata(video_id)

    # Step 2: Retrieve video transcript
    transcript = get_video_transcript(video_id)

    # Step 3: Identify subtopics using GPT-4o
    if metadata and transcript:
        subtopic_text = identify_subtopics_with_azure_openai(transcript)
        subtopics = parse_subtopics(subtopic_text)

        # Step 4: Generate slide objects for each subtopic
        slides = create_slide_objects_for_subtopics(metadata, subtopics)

        # Step 5: Save the slides to a JSON file
        with open('slides_by_subtopic.json', 'w', encoding='utf-8') as f:
            json.dump(slides, f, ensure_ascii=False, indent=2)
        print("\nSlides saved to 'slides_by_subtopic.json'")

if __name__ == '__main__':
    main()
