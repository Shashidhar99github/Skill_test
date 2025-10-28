import os
from apikey import *
from youtube_transcript_api import YouTubeTranscriptApi
from typing import List
import groq

client = groq.Groq(
    api_key=GROQ_API_KEY
)

def get_video_text(video_url):
    try:
        video_id = video_url.split("=")[1]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)

        transcript = ""
        for i in transcript_text:
            transcript += " " + i['text']

        return transcript

    except Exception as e:
        raise e

def get_quiz_data(skill: str, level: str, topic: str, number_of_questions: str) -> str:
    """
    Generate quiz questions using Groq API with Mistral model.
    Returns the response as a string (Python list format).
    """
    prompt_template = f"""
    You are a helpful assistant programmed to generate questions based on the skill, level at which the user was, the particular topic the user needs. From the inputs that you have received, you're tasked with designing {number_of_questions} distinct questions. Each of these questions will be accompanied by 4 possible answers: one correct answer and three incorrect ones.

    You have to create exactly {number_of_questions} for the user.
    For clarity and ease of processing, structure your response in a way that emulates a Python list of lists.

    Your output should be shaped as follows:

    1. An outer list that contains {number_of_questions} inner lists.
    2. Each inner list represents a set of question and answers, and contains exactly 5 strings in this order:
    - The generated question
    - The correct answer
    - The first incorrect answer
    - The second incorrect answer
    - The third incorrect answer

    Your output should mirror this structure:
    [
        ["Generated Question 1", "Correct Answer 1", "Incorrect Answer 1.1", "Incorrect Answer 1.2", "Incorrect Answer 1.3"],
        ["Generated Question 2", "Correct Answer 2", "Incorrect Answer 2.1", "Incorrect Answer 2.2", "Incorrect Answer 2.3"],
        ...
    ]

    It is crucial that you adhere to this format as it's optimized for further Python processing.

    Skill: {skill}
    Level: {level}
    Topic: {topic}.

    Apart from the list of questions do not give any other content from your response and not mention the list name just provide the list alone 
    which can be easy for further python processing.
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt_template
            }
        ],
        model="llama-3.1-8b-instant",
        temperature=0.7,
        max_tokens=2000,
    )

    response_text = chat_completion.choices[0].message.content
    print(response_text)
    return response_text

# Remove or comment out this test call in production:
# get_quiz_data("java", "beginner", "strings", "5")