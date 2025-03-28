import base64
import requests
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def image_to_base64(image_url):
    """Download an image and convert it to base64."""
    response = requests.get(image_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    else:
        print(f"Failed to download image: {response.status_code}")
        return None

def generate_caption(image_url):
    """Send base64 image to LLaMA Vision model for captioning."""
    image_base64 = image_to_base64(image_url)
    if not image_base64:
        print("Image conversion failed.")
        return None

    prompt = "Describe this jewelry image in detail."

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]}
            ],
            max_tokens=200,
            temperature=0.1
        )

        caption = response.choices[0].message.content.strip()
        print(f"Generated Caption: {caption}")
        return caption

    except Exception as e:
        print(f"Error in LLaMA vision request: {e}")
        return None

# Example usage
image_url = "https://meteor.stullercloud.com/das/45684194?$xlarge$"
generate_caption(image_url)
