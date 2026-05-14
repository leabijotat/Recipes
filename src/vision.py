# sends a photo to Claude and returns a list of recognized ingredients

import base64 # converts binary image data into a text string so it can be sent via API
import io # allows us to handle image bytes in memory like a file, without saving to disk
import json # parses Claude's response: Claude returns ingredients as JSON string, then json.loads() converts it into a Python dictionary
import os # reads environment variables used to load the API key from the .env file
import streamlit as st

os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

from anthropic import Anthropic
from PIL import Image

# load API key and model from .env; if ANTHROPIC_MODEL is not set, claude-haiku-4-5 is used as default
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

# large images are resized to reduce API token usage
MAX_EDGE = 1568

# prompt sent to Claude instructs it to return only a JSON list of generic ingredient names
PROMPT = """Identify every distinct food ingredient visible in this photo.
Skip non-food items and anything you can't see clearly.
Use generic names (e.g. 'milk' not 'Borden whole milk', 'greek yogurt' not 'Chobani').

Reply with ONLY a JSON object in this exact shape, nothing else:
{"ingredients": [{"name": "milk"}, {"name": "eggs"}, ...]}
"""

# prepares the image for the Claude API: opens it, converts to RGB if needed, resizes to reduce token usage, then encodes it as a base64 string
def encode_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    buf = io.BytesIO() # in-memory buffer saves the processed image without writing to disk
    img.save(buf, format="JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode()

# sends the fridge photo to Claude and returns a list of detected ingredients as JSON
def extract_ingredients(image_bytes):
    # abort early if the API key is missing 
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
    # encode the image and create the Anthropic client with the API key
    b64 = encode_image(image_bytes)
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    # builds the API request: one message with two content blocks; the image and the text prompt
    # the Anthropic API requires content as a list, so image and prompt are passed together
    image_block = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}
    messages = [{"role": "user", "content": [image_block, {"type": "text", "text": PROMPT}]}]
    result = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=2048, messages=messages)
    # extract the raw text from Claude's response
    text = result.content[0].text.strip()
    # strip markdown code fences that the model sometimes adds
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    # parses the JSON string into a Python dictionary and returns the ingredients list
    data = json.loads(text) 
    return data.get("ingredients", [])