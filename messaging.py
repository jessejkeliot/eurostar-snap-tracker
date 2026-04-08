import os
from pathlib import Path
from google import genai
from google.genai import types
from models import MinimalSearch, MinimalSearchModel
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

prompt_path = Path(__file__).resolve().parent / "prompt.txt"
if prompt_path.exists():
    with prompt_path.open("r", encoding="utf-8") as f:
        systemprompt = f.read()
else:
    systemprompt = ""

def send_results_to_user(user, results):
    pass

def parse_message(message):
    # make gemma 4 call with our system prompt
    client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
    schema = MinimalSearchModel.model_json_schema()
    today = datetime.today()
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=f"{systemprompt}\nToday's date is {today.strftime('%Y-%m-%d-%A')}\n\nUser: {message}",
        config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel("minimal")),
        response_mime_type="application/json",
        response_json_schema=schema
    ),
    )
    if response.text:
        print(response.text)
        search = MinimalSearchModel.model_validate_json(response.text)
        print(search)
        return MinimalSearch(**search.model_dump())
    return None

def list_models():
    client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
    
    pages = client.models.list()
    for page in pages:
        print(page)


if __name__ == "__main__":
    # list_models()
    parse_message("Hi there I want to book a train from London to Amsterdam leaving on the 16th of april")

    