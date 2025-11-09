import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List
import groq

# ====================================================
# Load Environment Variables from .env file
# ====================================================
load_dotenv()

# Securely load API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ Missing GROQ_API_KEY in your .env file!")

# Initialize Groq client safely
try:
    client = groq.Groq(api_key=GROQ_API_KEY)
except Exception as e:
    raise RuntimeError(f"❌ Failed to initialize Groq client: {e}")


# ====================================================
# Get Video Transcript Function
# ====================================================
def get_video_text(video_url: str) -> str:
    """
    Fetches the transcript text from a YouTube video using its URL.
    Returns the complete transcript as a single string.
    """
    try:
        # Extract video ID safely
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        else:
            raise ValueError("Invalid YouTube URL format")

        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([entry['text'] for entry in transcript_data])
        return transcript

    except Exception as e:
        print(f"⚠️ Error fetching transcript: {e}")
        return ""


# ====================================================
# Generate Quiz Questions Function
# ====================================================
def get_quiz_data(skill: str, level: str, topic: str, number_of_questions: str) -> str:
    """
    Generate quiz questions using Groq API with Mistral model.
    Returns the response as a string formatted as a Python list.
    """
    prompt_template = f"""
    You are a helpful assistant programmed to generate {number_of_questions} distinct multiple-choice questions.
    Each question must include:
    - The question text
    - One correct answer
    - Three incorrect answers

    Return your response **only** as a Python-style list of lists, like this:
    [
        ["Question 1", "Correct Answer 1", "Wrong 1", "Wrong 2", "Wrong 3"],
        ["Question 2", "Correct Answer 2", "Wrong 1", "Wrong 2", "Wrong 3"]
    ]

    Do not add explanations or extra text outside the list.

    Skill: {skill}
    Level: {level}
    Topic: {topic}.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt_template}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=2000,
        )

        response_text = chat_completion.choices[0].message.content.strip()
        print("✅ Quiz generated successfully:\n", response_text)
        return response_text

    except Exception as e:
        print(f"⚠️ Error while generating quiz: {e}")
        return None
