# test4.py
import base64
import requests
import os
import json
import re
import time
from groq import Groq
from dotenv import load_dotenv

# --- [Load environment variables, Initialize Groq, API Setup, Constants - SAME AS BEFORE] ---
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("Error: GROQ_API_KEY not found.")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

API_URL = os.getenv("API_URL")
API_APP = os.getenv("API_APP")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
if not all([API_URL, API_APP, API_KEY, API_SECRET]):
    print("Error: Brilliance Hub API configuration missing.")
HEADERS = {
    "x-api-app": API_APP,
    "x-api-key": API_KEY,
    "x-api-secret": API_SECRET,
    "Content-Type": "application/json"
} if all([API_APP, API_KEY, API_SECRET]) else {} # Ensure headers are valid

# --- [Constants - STYLES_MAP, number_words, jewelry_types, ALL_CATEGORIES - SAME AS BEFORE] ---
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
    "Rings": ["ring", "band"], "Earrings": ["earring", "stud", "hoop", "dangle"],
    "Pendants": ["pendant", "charm"], "Bracelets": ["bracelet", "bangle", "cuff"],
    "Necklaces": ["necklace", "chain", "collar"], "Charms": ["charm"]
}
ALL_CATEGORIES = list(set(STYLES_MAP.values()))
# --- End Constants ---


# --- [Core Functions: image_to_base64, generate_caption, create_json_from_caption - SAME AS BEFORE] ---
def image_to_base64(image_url):
    """Download an image and convert it to base64."""
    try:
        response = requests.get(image_url, timeout=10) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return base64.b64encode(response.content).decode('utf-8')
    except requests.exceptions.RequestException as e:
        print(f"Failed to download or access image URL: {image_url}. Error: {e}")
        return None
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return None

def generate_caption(image_url):
    """Send base64 image to LLaMA Vision model for captioning."""
    if not groq_client:
        print("Error: Groq client not initialized. Check API key.")
        return None

    print(f"Attempting to generate caption for: {image_url}")
    image_base64 = image_to_base64(image_url)
    if not image_base64:
        print("Image conversion to base64 failed.")
        return None

    prompt = """Describe this jewelry image in a concise way in one line highlighting it's color, type, material, characters written if any (if there are no characters then don't mention that).
    Avoid using the word 'jewelry' if it is a wearable item."""

    try:
        # Ensure the model name is correct and available
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile", # Or another suitable vision model if available like llama-3.2-90b-vision-preview
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
        if "rate limit" in str(e).lower():
             print("Rate limit likely exceeded. Waiting before retry...")
        return None

def create_json_from_caption(caption):
    """Use Groq's LLaMA to convert a jewelry caption into a JSON object, extracting only required info."""
    if not groq_client:
        print("Error: Groq client not initialized. Check API key.")
        return None

    print(f"Creating JSON from caption: {caption}")
    prompt = f"""
Given the following caption of a jewelry image, extract the following information and format it into a JSON object. Focus only on the jewelry item itself, ignoring background or irrelevant details. Extract only the most prominent and relevant features:

- **jewelry_type**: Possible values: Rings, Earrings, Pendants, Bracelets, Necklaces, Charms. Default to 'Pendants' if unclear.
- **material**: Possible values: Sterling Silver, Yellow, Rose, White, Diamond. Default to 'Sterling Silver' if unclear.
- **design**: Identify the primary shape or feature. Keep it concise (1-2 words):
    - Use 'rose' for rose shapes.
    - Use 'heart' for heart shapes.
    - Convert shapes (e.g., 'hexagonal') to (e.g., 'hexagon').
    - Convert number words (e.g., 'three') to numerals (e.g., 'numeral 3').
    - Use 'initial [letter]' for single letters (e.g., 'initial p' for 'p').
    - Otherwise, provide a brief description (e.g., 'Diamond', 'Floral', 'Mama').
- **categories**: Select up to 3 relevant tags representing the overall style (e.g., 'heart', 'diamond', 'engraved').

Provide the response STRICTLY as a JSON object only, without any introductory text or markdown formatting like ```json.

Caption: "{caption}"
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile", # Use a suitable text model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        llm_output = response.choices[0].message.content.strip()

        print("Raw LLM Output (should be JSON):")
        print(llm_output)

        json_data = json.loads(llm_output)
        print("Parsed JSON data:", json_data)
        return json_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Problematic LLM Output: {llm_output}")
        # Add fallback logic if needed, although response_format should prevent it
        return None
    except Exception as e:
        print(f"Error in LLaMA JSON creation request: {e}")
        return None


# --- NEW FUNCTION ---
def get_additional_keywords_with_llm(caption, used_keywords_set):
    """Use LLM to suggest 1-2 additional keywords from caption, excluding used ones."""
    if not groq_client:
        print("Error: Groq client not initialized for additional keyword extraction.")
        return ""

    print("  Attempting AI suggestion for Pass 3 keywords...")
    # Convert set to a readable list for the prompt
    used_keywords_list = ", ".join(filter(None, used_keywords_set)) # Filter out potential None or empty strings

    prompt = f"""
Analyze the following jewelry caption:
"{caption}"

The following keywords have already been used for searching or are considered primary identifiers:
[{used_keywords_list}]

Identify exactly one or two *additional* descriptive words from the caption that are NOT in the list above and are NOT generic filler words (like 'a', 'the', 'is', 'with', 'set', 'image', 'background', 'features', 'center', 'shaped'). Focus on words describing specific visual details, patterns, or secondary elements of the jewelry itself.

Return ONLY the identified keyword(s) as a single lowercase string (if two words, separate them with a space), or return an empty string if no suitable additional keywords are found. Do not add any explanation.

Examples:
- Caption: "A gold butterfly pendant with small pave diamonds on the wings." Used: [gold, pendant, butterfly, diamond]. Output: pave wings
- Caption: "Silver ring with an engraved floral pattern." Used: [silver, ring, pattern, ]. Output: "floral"
- Caption: "Rose gold necklace with a dangling pearl." Used: [rose gold, necklace, pearl]. Output: pearl
- Caption: "A sterling silver pendant with a heart- shaped embedded with word Mama." Used: [sterling silver, pendant, heart]. Output: mama
- Caption: "This image features a silver heart-shaped pendant with a diamond at its center, set against a white background." Used: [silver, heart]. Output: diamond
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant", # Use a fast model for this refinement task
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30, # Expect short output
            temperature=0.1,
            stop=["\n"] # Stop generation early if needed
        )
        keywords = response.choices[0].message.content.strip().lower()

        # Basic cleaning: remove potential quotes or extra formatting
        keywords = keywords.replace('"', '').replace("'", "").strip()

        print(f"  AI suggested keywords: '{keywords}'")
        return keywords

    except Exception as e:
        print(f"  Error during AI keyword suggestion: {e}")
        return "" # Return empty on error


def search_similar_products(json_prompt, initial_caption):
    """Searches the Brilliance Hub API based on extracted JSON criteria."""
    if not json_prompt or not isinstance(json_prompt, dict):
        print("Invalid JSON prompt provided to search function.")
        return {"error": "Invalid search criteria generated.", "data": [], "total_found": 0, "source_pass": "N/A"}
    if not HEADERS:
         print("Error: API headers not configured.")
         return {"error": "API configuration error.", "data": [], "total_found": 0, "source_pass": "N/A"}

    jew_type = json_prompt.get("jewelry_type", "Pendants").lower()
    design = json_prompt.get("design", "").lower().strip()
    material = json_prompt.get("material", "Metal").lower().strip()
    categories = [cat.lower().strip() for cat in json_prompt.get("categories", []) if cat]

    limit = 50
    max_attempts = 1
    first_pass_results = []
    second_pass_results = []
    third_pass_results = []
    last_successful_pass = None

    print(f"\n--- Starting Search ---")
    print(f"Criteria: Type='{jew_type}', Design='{design}', Material='{material}', Categories={categories}")

    # --- Pass 1: Material (Title) + Categories (Style) + Type (Type) ---
    # [SAME AS BEFORE - No changes needed here]
    search_style = [cat.capitalize() for cat in categories if cat]
    first_pass_search_term = material.capitalize() if material else "Jewelry"
    print(f"\nPass 1: Title='{first_pass_search_term}', Style={search_style}, Type={jew_type.capitalize() if jew_type else 'Any'}")
    offset = 0
    api_error_pass1 = False
    while offset < max_attempts * limit:
        search_body = {
            "offset": offset, "limit": limit, "title": first_pass_search_term, "style": search_style
        }
        if jew_type and jew_type != 'any': search_body["type"] = jew_type.capitalize()
        print(f"  API Request (Pass 1): {search_body}")
        try:
            response = requests.get(API_URL, headers=HEADERS, params=search_body, timeout=15)
            print(f"  API Response Status (Pass 1): {response.status_code}")
            response.raise_for_status()
            results = response.json()
            current_batch = results.get("data", [])
            if current_batch:
                first_pass_results.extend(current_batch)
                print(f"  Found {len(current_batch)} items in this batch (Pass 1). Total: {len(first_pass_results)}")
            else: break
            if len(current_batch) < limit: break
            offset += limit
        except requests.RequestException as e:
            print(f"  Error: First pass API search failed: {e}")
            api_error_pass1 = True; break
        except Exception as e:
            print(f"  Error: Unexpected error during first pass search: {e}")
            api_error_pass1 = True; break
    print(f"Total results from Pass 1: {len(first_pass_results)}")
    if first_pass_results and not api_error_pass1: last_successful_pass = "First Pass"


    # --- Pass 2: Filter Pass 1 results by Design keyword in Title ---
    # [SAME AS BEFORE - No changes needed here]
    if design and first_pass_results:
        print(f"\nPass 2: Filtering {len(first_pass_results)} items by Design='{design}' in title")
        common_words_second_pass = {
            "shaped", "style", "design", "pattern", "feature", "pendant", "earring", "ring", "bracelet", "necklace",
             "small", "large", "big", "little", "tiny", "medium", "simple", "basic", "with", "and",
             "attached", "hanging", "placed", "shown", "metal", "colored", "silver", "gold", "white", "yellow", "rose"
        }
        design_words = design.split()
        cleaned_design_words = [word for word in design_words if word not in common_words_second_pass and len(word) > 1]
        second_pass_filter_term = " ".join(cleaned_design_words)
        print(f"  Cleaned filter term (Pass 2): '{second_pass_filter_term}'")
        if second_pass_filter_term:
             second_pass_results = [
                 item for item in first_pass_results
                 if item.get("jew_title") and second_pass_filter_term in item["jew_title"].lower()
             ]
             print(f"  Results after Pass 2 filter: {len(second_pass_results)}")
             if second_pass_results: last_successful_pass = "Second Pass"
             else: second_pass_results = first_pass_results # Revert if filter yields nothing
        else:
             print("  Skipping Pass 2 filter as cleaned design term is empty.")
             second_pass_results = first_pass_results
    else:
        print("\nSkipping Pass 2 filter (No design keyword or no Pass 1 results).")
        second_pass_results = first_pass_results


    # --- Pass 3: Filter Pass 2 results using AI-suggested keywords ---
    # [MODIFIED SECTION]
    current_results_for_third_pass = second_pass_results # Start with results from previous stage

    if current_results_for_third_pass and initial_caption:
        print(f"\nPass 3: Filtering {len(current_results_for_third_pass)} items using AI suggested keywords from caption")

        # Build the set of already used keywords for the AI prompt
        used_keywords = set([c.lower() for c in categories if c] +
                            [d.lower() for d in design.split() if d] +
                            [material.lower(), jew_type.lower()])
        # Add common words to avoid the AI suggesting them if they slip through
        common_words_for_ai = {
            "a", "an", "the", "this", "that", "these", "those", "and", "or", "but", "of", "with", "for", "on", "at","its"
            "to", "from", "by", "as", "it", "is", "are", "was", "were", "be", "been", "has", "have", "had","no",
            "in", "out", "up", "down", "over", "under", "above", "below", "image", "photo", "picture", "view",
            "background", "surface", "display", "close-up", "shot", "features", "featuring", "depicts","present"
            "shaped", "style", "design", "pattern", "piece", "item", "accessory", "jewelry", "wearable",
            "made", "set", "against", "shown", "engraved", "center", # Add words explicitly mentioned in AI prompt instructions
             "color", "colored",
             "metal", "gold", "silver", "white", "yellow", "rose", "sterling",
             "ring", "pendant", "earring", "necklace", "bracelet", "charm", "band", "stud", "hoop"
        }
        full_exclusion_set = used_keywords.union(common_words_for_ai)

        # Call the AI function to get keywords
        third_pass_filter_term = get_additional_keywords_with_llm(initial_caption, full_exclusion_set)

        if third_pass_filter_term: # Only filter if AI provided a term
            print(f"  Using AI filter term (Pass 3): '{third_pass_filter_term}'")
            third_pass_results = [
                 item for item in current_results_for_third_pass
                 if item.get("jew_title") and third_pass_filter_term in item["jew_title"].lower()
             ]
            print(f"  Results after Pass 3 AI filter: {len(third_pass_results)}")
            if third_pass_results:
                last_successful_pass = "Third Pass"
            else:
                print("  AI filter term yielded no matches. Reverting to previous results.")
                third_pass_results = current_results_for_third_pass # Keep previous results
        else:
            print("  AI did not suggest keywords, or suggestion was empty. Skipping Pass 3 filter.")
            third_pass_results = current_results_for_third_pass # No filtering applied
    else:
         print("\nSkipping Pass 3 filter (No previous results or no caption).")
         third_pass_results = current_results_for_third_pass


    # --- Final Results Selection ---
    # [SAME AS BEFORE - No changes needed here]
    print("\n--- Final Search Summary ---")
    final_results_data = []
    source_pass_name = "N/A"
    if last_successful_pass == "Third Pass" and third_pass_results:
        final_results_data = third_pass_results[:4]
        source_pass_name = "Third Pass"
        print(f"Using results from Third Pass. Found {len(third_pass_results)}, returning top {len(final_results_data)}.")
    elif last_successful_pass == "Second Pass" and second_pass_results:
        final_results_data = second_pass_results[:4]
        source_pass_name = "Second Pass"
        print(f"Using results from Second Pass. Found {len(second_pass_results)}, returning top {len(final_results_data)}.")
    elif last_successful_pass == "First Pass" and first_pass_results:
        final_results_data = first_pass_results[:4]
        source_pass_name = "First Pass"
        print(f"Using results from First Pass. Found {len(first_pass_results)}, returning top {len(final_results_data)}.")
    else:
         if api_error_pass1:
             print("Search failed due to API error in the first pass.")
             return {"error": "Failed to retrieve initial search results from API.", "data": [], "total_found": 0, "source_pass": "N/A"}
         else:
             print("No similar products found across all search passes.")
             return {"data": [], "total_found": 0, "source_pass": "None"}

    print(f"Source of final results: {source_pass_name}")
    print(f"Number of items in final_results_data: {len(final_results_data)}")

    final_results = {
        "data": final_results_data,
        "total_found": len(final_results_data),
        "source_pass": source_pass_name,
    }
    return final_results


# --- [Example Usage (__main__ block) - SAME AS BEFORE] ---
if __name__ == "__main__":
    print("Running test4.py directly...")

    if not groq_client or not HEADERS:
         print("Exiting due to missing Groq client or API configuration.")
    else:
        image_url = input("Enter image URL to test: ")

        if image_url:
            print("\nStep 1: Generating Caption...")
            test_caption = generate_caption(image_url)

            if test_caption:
                print("\nStep 2: Creating JSON from Caption...")
                test_json = create_json_from_caption(test_caption)

                if test_json:
                    print("\nStep 3: Searching for Similar Products...")
                    # Pass the original caption to the search function
                    test_results = search_similar_products(test_json, test_caption)

                    print("\n--- Final Test Results ---")
                    if test_results:
                        print(json.dumps(test_results, indent=4))
                        print(f"Total items returned: {test_results.get('total_found', 0)}")
                        print(f"Source Pass: {test_results.get('source_pass', 'N/A')}")
                    else:
                        print("Search function returned None or an error structure.")
                else:
                    print("\nFailed to create JSON prompt.")
            else:
                print("\nFailed to generate caption.")
        else:
            print("No image URL provided.")