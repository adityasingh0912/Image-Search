import base64
import requests
import os
import json
import re
import time
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Brilliance Hub API Setup
API_URL = os.getenv("API_URL")
HEADERS = {
    "x-api-app": os.getenv("API_APP"),
    "x-api-key": os.getenv("API_KEY"),
    "x-api-secret": os.getenv("API_SECRET"),
    "Content-Type": "application/json"
}

# Define constants (unchanged from original)
STYLES_MAP = {
    "vintage": "Vintage", "modern": "Modern", "classic": "Classic", "bohemian": "Bohemian",
    "minimalist": "Minimalist", "romantic": "Romantic", "art deco": "Art Deco",
    "nature-inspired": "Nature Inspired", "geometric": "Geometric", "abstract": "Abstract",
    "statement": "Statement", "delicate": "Delicate", "ethic": "Ethnic", "religious": "Religious",
    "custom": "Custom", "unique": "Unique", "luxury": "Luxury", "casual": "Casual",
    "formal": "Formal", "wedding": "Wedding", "engagement": "Engagement", "anniversary": "Anniversary",
    "birthday": "Birthday", "gift": "Gift", "handmade": "Handmade", "personalized": "Personalized",
    "celestial": "Celestial", "animal": "Animal", "floral": "Floral", "heart": "Heart",
    "infinity": "Infinity", "knot": "Knot", "star": "Star", "moon": "Moon", "cross": "Cross",
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

# Helper function to convert image to base64
def image_to_base64(image_url):
    """Download an image and convert it to base64."""
    response = requests.get(image_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    else:
        print(f"Failed to download image: {response.status_code}")
        return None

# Updated caption generation using Groq's LLaMA Vision model
def generate_caption(image_url):
    """Send base64 image to LLaMA Vision model for captioning."""
    image_base64 = image_to_base64(image_url)
    if not image_base64:
        print("Image conversion failed.")
        return None

    prompt = """Describe this jewelry image in a concise way in one line highlighting it's color, type, material, characters written if any (if there are no characters then don't mention that).
    Avoid using the word 'jewelry' if it is a wearable item."""

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


# Updated JSON prompt creation with concise extraction
def create_json_from_caption(caption):
    """Use Groq's LLaMA to convert a jewelry caption into a JSON object, extracting only required info."""
    prompt = f"""
Given the following caption of a jewelry image, extract the following information and format it into a JSON object. Focus only on the jewelry item itself, ignoring background or irrelevant details. Extract only the most prominent and relevant features:

- **jewelry_type**: Possible values: Rings, Earrings, Pendants, Bracelets, Necklaces, Charms. Default to 'Pendants' if unclear.
- **material**: Possible values: Sterling Silver, Yellow, Rose, White, Diamond. Default to 'Sterling Silver' if unclear.
- **design**: Identify the primary shape or feature. Keep it concise (1-2 words):
    - Use 'rose' for rose shapes.
    - Use 'heart' for heart shapes.
    - Convert shapes (e.g., 'hexagonal') to  (e.g., 'hexagon')
    - Convert number words (e.g., 'three') to numerals (e.g., 'numeral 3').
    - Use 'initial [letter]' for single letters (e.g., 'initial p' for 'p').
    - Otherwise, provide a brief description (e.g., 'Diamond', 'Floral').
- **categories**: Select up to 3 relevant tags representing the overall style (e.g., 'heart', 'diamond').

Provide the response as a JSON object.

Caption: "{caption}"
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1  # Low temperature for structured output
        )
        llm_output = response.choices[0].message.content.strip()

        print("Raw LLM Output:")
        print(llm_output)

        # Extract JSON content if wrapped in markdown
        if llm_output.startswith("```json") and llm_output.endswith("```"):
            llm_output = llm_output[len("```json"): -len("```")].strip()
        elif llm_output.startswith("```") and llm_output.endswith("```"):
            llm_output = llm_output[len("```"): -len("```")].strip()

        json_data = json.loads(llm_output)
        return json_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Problematic LLM Output: {llm_output}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Updated search function with refined third pass
def search_similar_products(json_prompt, initial_caption):
    if not json_prompt:
        print("Invalid JSON prompt. Cannot search for similar products.")
        return None

    jew_type = json_prompt.get("jewelry_type", "Pendants").lower()
    design = json_prompt.get("design", "")
    material = json_prompt.get("material", "Metal")
    categories = json_prompt.get("categories", [])
    limit = 5000
    max_attempts = 3
    first_pass_results = []
    second_pass_results = []
    third_pass_results = []
    final_results_data = []
    last_successful_pass = None

    # Category and type adjustments
    if jew_type == "charms":
        jew_type = "pendants"  # Treat charms as pendants for search
    if 'sunburst' in categories:
        categories.remove('sunburst')
    if 'gold' in categories:
        categories.remove('gold')
    
    # First Pass Search
    first_pass_search_term = f"{material}"
    if first_pass_search_term:
        offset = 0
        print(f"First pass search title: {first_pass_search_term}")
        while offset < max_attempts * limit:
            search_body = {
                "offset": offset,
                "limit": limit,
                "title": first_pass_search_term,
                "style": [cat.capitalize() for cat in categories]
            }
            if jew_type:
                search_body["type"] = jew_type.capitalize()
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

    # Second Pass Filter
    if design and first_pass_results:
        print(f"Second pass filter term (design): {design}")
        second_pass_filter_term = design.lower()
        # Common words to exclude in second pass
        common_words_second_pass = {
            "rectangular", "style", "design", "pattern", "feature",
            "small", "large", "big", "little", "tiny", "medium", "simple", "basic",
            "attached", "hanging", "placed", "shown"
        }
        
        # Split design into words and filter out common words
        design_words = second_pass_filter_term.split()
        cleaned_design_words = [word for word in design_words if word not in common_words_second_pass]
        second_pass_filter_term = " ".join(cleaned_design_words) if cleaned_design_words else second_pass_filter_term

        # Adjust filter term for numbers or initials
        if second_pass_filter_term.isdigit():
            second_pass_filter_term = f"numeral {second_pass_filter_term}"
        elif len(second_pass_filter_term) == 1 and second_pass_filter_term.isalpha():
            second_pass_filter_term = f"initial {second_pass_filter_term}"

        print(f"Cleaned second pass filter term: {second_pass_filter_term}")
        second_pass_results = [item for item in first_pass_results if 
                               second_pass_filter_term in item.get("jew_title", "").lower()]
        print(f"Number of results after filtering by design ('{second_pass_filter_term}'): {len(second_pass_results)}")
        if second_pass_results:
            last_successful_pass = "second"

    # Third Pass Filter - Focus on important factors only
    if second_pass_results:
        caption_lower = initial_caption.lower()
        # Important factors to consider (prioritized keywords)
        important_keywords = set(categories + [design.lower(), material.lower(), jew_type.lower()])
        # Expanded common_words list
        common_words = {
            "a", "an", "the", "this", "that", "these", "those",
            "in", "of", "with", "for", "on", "at", "to", "from", "by", "as",
            "above", "below", "around", "beside", "between", "among", "through",
            "is", "are", "was", "were", "be", "been", "being",
            "has", "have", "had", "does", "do", "did",
            "it", "its", "itself","word",
            "shaped", "background", "surface", "table", "display", "stand", "holder",
            "attached", "hanging", "sitting", "placed", "shown", "photographed",
            "image", "photo", "picture", "view", "angle", "close", "up","heartshaped","pendant"
            "clear", "detailed", "blurred", "focused","features","goldcolored","hexagonalshaped",
            "roundshaped", "ovalshaped", "triangularshaped", "square", "rectangular",
            "silvercolored", "rosecolored", "whitecolored", "yellowcolored",
            "piece", "item", "accessory", "ornament", "decoration","sunburst",
            "gold", "silver", "rose", "white", "yellow", "diamond", "metal"
        }
        words = caption_lower.split()
        unexpected_words = []
        
        for word in words:
            cleaned_word = re.sub(r'[^a-zA-Z]', '', word)
            if (cleaned_word and cleaned_word not in common_words and 
                cleaned_word not in important_keywords and len(cleaned_word) > 2):  # Avoid short, vague words
                unexpected_words.append(cleaned_word)
                if len(unexpected_words) >= 2:  # Limit to 2 significant terms
                    break

        if unexpected_words:
            third_pass_filter_term = " ".join(unexpected_words)
            print(f"Third pass filter term (important unexpected words): {third_pass_filter_term}")
            third_pass_results = [item for item in second_pass_results if 
                                 third_pass_filter_term in item.get("jew_title", "").lower()]
            print(f"Number of results after filtering by unexpected words: {len(third_pass_results)}")
            if third_pass_results:
                last_successful_pass = "third"
        else:
            print("No significant unexpected words found for third pass.")
    else:
        print("No second pass results to filter for the third pass.")

    # Final Results
    print("Final Search Summary:")
    if last_successful_pass == "third" and third_pass_results:
        final_results_data = third_pass_results[:4]
        print("Third Pass Results (First 4):")
    elif last_successful_pass == "second" and second_pass_results:
        final_results_data = second_pass_results[:4]
        print("Second Pass Results (First 4):")
    elif last_successful_pass == "first" and first_pass_results:
        final_results_data = first_pass_results[:4]
        print("First Pass Results (First 4):")
    else:
        print("No similar products found across all search passes.")

    print(f"Number of items in final_results_data: {len(final_results_data)}")
    final_results = {"data": final_results_data, "total_found": len(final_results_data)}
    print(json.dumps(final_results, indent=4))
    return final_results

# Main function
def find_similar_products(image_url):
    caption = generate_caption(image_url)
    if not caption:
        print("Failed to generate caption. Cannot proceed.")
        return None

    json_prompt = create_json_from_caption(caption)
    if not json_prompt:
        print("Failed to create JSON prompt.")
        return None

    results = search_similar_products(json_prompt, caption)
    return results

# Example usage
if __name__ == "__main__":
    image_url = "https://meteor.stullercloud.com/das/110833007?$xlarge$"
    find_similar_products(image_url)