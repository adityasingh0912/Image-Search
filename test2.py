import re
import requests
import time
import json
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError
from dotenv import load_dotenv
import os
import groq

# Load environment variables
load_dotenv()

# Hugging Face Setup
hf_client = InferenceClient(token=os.getenv("HF_TOKEN"))

# Brilliance Hub API Setup
API_URL = os.getenv("API_URL")
HEADERS = {
    "x-api-app": os.getenv("API_APP"),
    "x-api-key": os.getenv("API_KEY"),
    "x-api-secret": os.getenv("API_SECRET"),
    "Content-Type": "application/json"
}

# Define STYLES_MAP, number_words, jewelry_types, ALL_CATEGORIES (unchanged)
STYLES_MAP = {
    "vintage": "Vintage",
    "modern": "Modern",
    "classic": "Classic",
    "bohemian": "Bohemian",
    "minimalist": "Minimalist",
    "romantic": "Romantic",
    "art deco": "Art Deco",
    "nature-inspired": "Nature Inspired",
    "geometric": "Geometric",
    "abstract": "Abstract",
    "statement": "Statement",
    "delicate": "Delicate",
    "ethic": "Ethnic",
    "religious": "Religious",
    "custom": "Custom",
    "unique": "Unique",
    "luxury": "Luxury",
    "casual": "Casual",
    "formal": "Formal",
    "wedding": "Wedding",
    "engagement": "Engagement",
    "anniversary": "Anniversary",
    "birthday": "Birthday",
    "gift": "Gift",
    "handmade": "Handmade",
    "personalized": "Personalized",
    "celestial": "Celestial",
    "animal": "Animal",
    "floral": "Floral",
    "heart": "Heart",
    "infinity": "Infinity",
    "knot": "Knot",
    "star": "Star",
    "moon": "Moon",
    "cross": "Cross",
    "tree of life": "Tree of Life"
}

number_words = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"
}

jewelry_types = {
    "Rings": ["ring", "band"],
    "Earrings": ["earring", "stud", "hoop", "dangle"],
    "Pendants": ["pendant", "charm"],
    "Bracelets": ["bracelet", "bangle", "cuff"],
    "Necklaces": ["necklace", "chain", "collar"],
    "Charms": ["charm"]
}

ALL_CATEGORIES = list(set(STYLES_MAP.values()))

# Helper Function to Detect Jewelry Type (unchanged)
def detect_jewelry_type(caption_lower):
    for type_name, keywords in jewelry_types.items():
        if any(keyword in caption_lower for keyword in keywords):
            return type_name
    return "Pendants"  # Default

# Function to Extract Styles (unchanged)
def extract_styles_from_caption(caption):
    found_styles = []
    caption_lower = caption.lower()
    for style_key, style_value in STYLES_MAP.items():
        if style_key in caption_lower:
            found_styles.append(style_value)
    return found_styles

# Generate Caption (unchanged)
def generate_caption(image_url):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            caption_obj = hf_client.image_to_text(
                image_url,
                model="Salesforce/blip-image-captioning-large"
            )
            if hasattr(caption_obj, 'generated_text'):
                print(f"Generated Caption: {caption_obj.generated_text}")
                return caption_obj.generated_text
            else:
                print("Caption object missing 'generated_text'.")
                return None
        except HfHubHTTPError as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed for {image_url}. Retrying...")
                time.sleep(2)
            else:
                print(f"Failed to generate caption after {max_retries} attempts.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error during caption generation: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None

# New Function to Create JSON Prompt with LLM
import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def create_json_from_caption(caption):
    """Use Groq's LLaMA to convert a jewelry caption into a JSON object."""
    # Define the prompt for LLaMA
    prompt = f"""
Given the following caption of a jewelry image, extract the following information and format it into a JSON object:

- **jewelry_type**: Possible values: Rings, Earrings, Pendants, Bracelets, Necklaces, Charms. Default to 'Pendants' if unclear.
- **material**: Possible values: Sterling Silver, Yellow, Rose, White, Diamond, Metal. Default to 'Sterling silver' if unclear.
- **design**: Describe the design.
    - If the design is a heart shape, use the value 'heart'.
    - If the design includes sunburst, use the value ''.
    - If the design includes a number word (e.g., 'three', 'five'), output the numeral (e.g., '3', '5').
    - If the design includes a word that looks like a letter 'p', output 'initial p'.
    - If the design includes a word that looks like a letter 'q', output 'initial q'.
    - Otherwise, provide a concise description (e.g., 'Diamond', 'Floral').
- **categories**: List relevant tags (e.g., 'heart', 'diamond').

Provide the response as a JSON object.

Caption: "{caption}"
"""

    try:
        # Call Groq's API
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Adjust model name if needed
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1  # Low temperature for structured output
        )
        llm_output = response.choices[0].message.content.strip()

        # Print the raw output from the LLM
        print("Raw LLM Output:")
        print(llm_output)

        # Extract JSON content if it's wrapped in markdown
        if llm_output.startswith("```json") and llm_output.endswith("```"):
            llm_output = llm_output[len("```json"): -len("```")].strip()
        elif llm_output.startswith("```") and llm_output.endswith("```"):
            llm_output = llm_output[len("```"): -len("```")].strip()

        # Parse the JSON response
        json_data = json.loads(llm_output)
        return json_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Problematic LLM Output: {llm_output}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
# Search Similar Products (updated for hierarchical search and category/type handling)
def search_similar_products(json_prompt, initial_caption):
    if not json_prompt:
        print("Invalid JSON prompt. Cannot search for similar products.")
        return None

    jew_type = json_prompt.get("jewelry_type", "Pendants").lower() # Convert to lowercase for easier comparison
    design = json_prompt.get("design", "")
    material = json_prompt.get("material", "Metal")
    categories = json_prompt.get("categories", [])
    limit = 1000
    max_attempts = 3
    first_pass_results = []
    second_pass_results = []
    third_pass_results = []
    final_results_data = []
    last_successful_pass = None

    # --- Category and Type Adjustments ---
    if jew_type == "charms":
        jew_type = "pendants"  # Treat charms as pendants for search

    if 'sunburst' in categories:
        categories.remove('sunburst')
    if 'gold' in categories:
        categories.remove('gold')

    # --- First Pass Search ---
    first_pass_search_term = f"{material} {jew_type}" if material and jew_type else jew_type
    if first_pass_search_term:
        offset = 0
        print(f"First pass search title: {first_pass_search_term}")
        while offset < max_attempts * limit:
            search_body = {
                "offset": offset,
                "limit": limit,
                "type": jew_type.capitalize(), # Capitalize for API request
                "title": first_pass_search_term,
                "style": [cat.capitalize() for cat in categories] # Capitalize categories
            }
            try:
                response = requests.get(API_URL, headers=HEADERS, params=search_body)
                response.raise_for_status()
                results = response.json()
                if "data" in results:
                    first_pass_results.extend(results["data"])
                if len(results.get("data", [])) < limit:
                    break
                offset += limit
            except requests.RequestException as e:
                print(f"First pass search failed: {e}")
                offset += limit
        print(f"Number of results from the first pass: {len(first_pass_results)}")
        if first_pass_results:
            last_successful_pass = "first"
    else:
        print("No first pass search term provided.")

    # --- Second Pass Filter ---
    if design and first_pass_results:
        print(f"Second pass filter term (design): {design}")
        second_pass_filter_term = design.lower()
        if second_pass_filter_term.isdigit():
            second_pass_filter_term = f"numeral {second_pass_filter_term}"
            print(f"Modified second pass filter term for number: {second_pass_filter_term}")
        elif len(second_pass_filter_term) == 1 and second_pass_filter_term.isalpha():
            second_pass_filter_term = f"initial {second_pass_filter_term}"
            print(f"Modified second pass filter term for letter: {second_pass_filter_term}")

        second_pass_results = [item for item in first_pass_results if second_pass_filter_term in item.get("jew_title", "").lower()]
        print(f"Number of results after filtering by design ('{design}'): {len(second_pass_results)}")
        if second_pass_results:
            last_successful_pass = "second"
    else:
        print("No design to filter by or no first pass results for the second pass.")

    # --- Third Pass Filter ---
    if second_pass_results:
        unexpected_words = []
        caption_lower = initial_caption.lower()
        common_words = ["pendant", "necklace","word", "ring", "earrings", "bracelet", "charm",
                        "silver", "gold", "diamond", "metal", "heart", "shaped", "number",
                        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                        "in", "a", "an", "the", "is", "of", "with", "and", "for", "on", "at",
                        "it", "this", "that", "be", "to", "from", "by", "as", "are", "was",
                        "were", "has", "have", "had", "can", "could", "will", "would", "may",
                        "might", "should", "must", "close", "up", "white", "background"]
        words = caption_lower.split()
        for word in words:
            cleaned_word = re.sub(r'[^a-zA-Z]', '', word)
            if cleaned_word and cleaned_word not in common_words and cleaned_word not in jew_type.lower() and cleaned_word not in material.lower() and cleaned_word not in design.lower():
                unexpected_words.append(cleaned_word)

        if unexpected_words:
            third_pass_filter_term = " ".join(unexpected_words)
            print(f"Third pass filter term (unexpected words): {third_pass_filter_term}")
            third_pass_results = [item for item in second_pass_results if third_pass_filter_term in item.get("jew_title", "").lower()]
            print(f"Number of results after filtering by unexpected words: {len(third_pass_results)}")
            if third_pass_results:
                last_successful_pass = "third"
        else:
            print("No unexpected words found in the caption for the third pass.")
    else:
        print("No second pass results to filter for the third pass.")

    # --- Final Results ---
    print("Final Search Summary:")
    if last_successful_pass == "third" and third_pass_results:
        print("Third Pass Results (First 4):")
        final_results_data = third_pass_results[:4]
    elif last_successful_pass == "second" and second_pass_results:
        print("Second Pass Results (First 4):")
        final_results_data = second_pass_results[:4]
    elif last_successful_pass == "first" and first_pass_results:
        print("First Pass Results (First 4):")
        final_results_data = first_pass_results[:4]
    else:
        print("No similar products found across all search passes.")

    print(f"Number of items in final_results_data: {len(final_results_data)}")
    final_results = {"data": final_results_data, "total_found": len(final_results_data)}
    print(json.dumps(final_results, indent=4))
    return final_results

# Main Function (updated to pass initial_caption)
def find_similar_products(image_url):
    caption = generate_caption(image_url)
    if not caption:
        print("Failed to generate caption. Cannot proceed.")
        return

    json_prompt = create_json_from_caption(caption)
    if not json_prompt:
        print("Failed to create JSON prompt.")
        return

    results = search_similar_products(json_prompt, caption) # Pass the initial caption
    return results # Returning results for potential further use

# Run Example
if __name__ == "__main__":
    image_url_heart_shape_mama = "https://meteor.stullercloud.com/das/45684194?$xlarge$" # Example image with "mama"
    find_similar_products(image_url_heart_shape_mama)