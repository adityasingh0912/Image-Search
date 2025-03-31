# test4.py
import base64
import requests
import os
import json
import re
import time
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
# Crucial for this script to access API keys when run directly or imported
load_dotenv()

# Initialize Groq client
# Ensure GROQ_API_KEY is set in your .env file
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("Error: GROQ_API_KEY not found in environment variables.")
    # Consider exiting or raising an error if used as a standalone script
    # exit(1)
# Initialize only if the key exists
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# Brilliance Hub API Setup
# Ensure these are set in your .env file
API_URL = os.getenv("API_URL")
API_APP = os.getenv("API_APP")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Check if essential API config is missing
if not all([API_URL, API_APP, API_KEY, API_SECRET]):
    print("Error: Brilliance Hub API configuration (API_URL, API_APP, API_KEY, API_SECRET) missing in environment variables.")
    # Consider exiting or raising an error
    # exit(1)

HEADERS = {
    "x-api-app": API_APP,
    "x-api-key": API_KEY,
    "x-api-secret": API_SECRET,
    "Content-Type": "application/json"
}

# --- Constants (Copied from your previous version) ---
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
# --- End Constants ---


# --- Core Functions ---

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
        response = groq_client.chat.completions.create(
            model="llama-3.2-90b-vision-preview", # Use a valid vision model
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
        # Attempt to handle potential rate limits or temporary errors
        if "rate limit" in str(e).lower():
             print("Rate limit likely exceeded. Waiting before retry...")
             # time.sleep(5) # Optional: wait before failing
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
        # Use a current, suitable text model and request JSON output
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Verify this model is available and suitable
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,  # Low temperature for structured output
            response_format={"type": "json_object"} # Request JSON output directly
        )
        llm_output = response.choices[0].message.content.strip()

        print("Raw LLM Output (should be JSON):")
        print(llm_output)

        # Directly parse the JSON output
        json_data = json.loads(llm_output)
        print("Parsed JSON data:", json_data)
        return json_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Problematic LLM Output: {llm_output}")
        # Fallback: Try to extract JSON from markdown if direct JSON fails (less likely now)
        match = re.search(r'```json\s*([\s\S]*?)\s*```', llm_output, re.IGNORECASE)
        if match:
            try:
                json_data = json.loads(match.group(1).strip())
                print("Parsed JSON data (fallback from markdown):", json_data)
                return json_data
            except json.JSONDecodeError as fallback_e:
                print(f"Fallback JSON Decode Error: {fallback_e}")
                return None
        return None
    except Exception as e:
        print(f"Error in LLaMA JSON creation request: {e}")
        return None

def search_similar_products(json_prompt, initial_caption):
    """Searches the Brilliance Hub API based on extracted JSON criteria."""
    if not json_prompt or not isinstance(json_prompt, dict):
        print("Invalid JSON prompt provided to search function.")
        return {"error": "Invalid search criteria generated.", "data": [], "total_found": 0, "source_pass": "N/A"}

    # Check if API headers are properly configured
    if not all(HEADERS.values()):
         print("Error: API headers incomplete. Check .env configuration.")
         return {"error": "API configuration error.", "data": [], "total_found": 0, "source_pass": "N/A"}

    jew_type = json_prompt.get("jewelry_type", "Pendants").lower()
    design = json_prompt.get("design", "").lower().strip() # Ensure lowercase and stripped
    material = json_prompt.get("material", "Metal").lower().strip() # Ensure lowercase and stripped
    categories = [cat.lower().strip() for cat in json_prompt.get("categories", []) if cat] # Lowercase, strip, remove empty

    limit = 50 # Keep limit reasonable for web requests
    max_attempts = 1 # Limit API calls per pass for web requests
    first_pass_results = []
    second_pass_results = []
    third_pass_results = []
    last_successful_pass = None

    print(f"\n--- Starting Search ---")
    print(f"Criteria: Type='{jew_type}', Design='{design}', Material='{material}', Categories={categories}")

    # --- Search Pass Logic (Similar to app.py version) ---

    # Pass 1: Material (Title) + Categories (Style) + Type (Type)
    #------------------------------------------------------------
    search_style = [cat.capitalize() for cat in categories if cat]
    first_pass_search_term = material.capitalize() if material else "Jewelry" # Basic term if material is generic/missing
    print(f"\nPass 1: Title='{first_pass_search_term}', Style={search_style}, Type={jew_type.capitalize() if jew_type else 'Any'}")
    offset = 0
    api_error_pass1 = False
    while offset < max_attempts * limit:
        search_body = {
            "offset": offset,
            "limit": limit,
            "title": first_pass_search_term,
            "style": search_style
        }
        if jew_type and jew_type != 'any': # Only add type if specific
            search_body["type"] = jew_type.capitalize()

        print(f"  API Request (Pass 1): {search_body}")
        try:
            response = requests.get(API_URL, headers=HEADERS, params=search_body, timeout=15)
            print(f"  API Response Status (Pass 1): {response.status_code}")
            response.raise_for_status() # Check for HTTP errors
            results = response.json()
            current_batch = results.get("data", [])
            if current_batch:
                first_pass_results.extend(current_batch)
                print(f"  Found {len(current_batch)} items in this batch (Pass 1). Total: {len(first_pass_results)}")
            else:
                 print("  No more data found in this batch (Pass 1).")
                 break # Stop if no data or empty data list

            if len(current_batch) < limit:
                 print("  Reached end of results for Pass 1 criteria.")
                 break # Stop if fewer results than limit received
            offset += limit
        except requests.RequestException as e:
            print(f"  Error: First pass API search failed: {e}")
            api_error_pass1 = True
            break # Stop on API error for this pass
        except Exception as e:
            print(f"  Error: Unexpected error during first pass search: {e}")
            api_error_pass1 = True
            break
        # time.sleep(0.2) # Optional small delay

    print(f"Total results from Pass 1: {len(first_pass_results)}")
    if first_pass_results and not api_error_pass1:
        last_successful_pass = "First Pass"

    # Pass 2: Filter Pass 1 results by Design keyword in Title
    #------------------------------------------------------------
    if design and first_pass_results:
        print(f"\nPass 2: Filtering {len(first_pass_results)} items by Design='{design}' in title")
        # Refine common words list based on observations
        common_words_second_pass = {
            "shaped", "style", "design", "pattern", "feature", "pendant", "earring", "ring", "bracelet", "necklace",
             "small", "large", "big", "little", "tiny", "medium", "simple", "basic", "with", "and",
             "attached", "hanging", "placed", "shown", "metal", "colored", "silver", "gold", "white", "yellow", "rose"
        }
        design_words = design.split()
        # Filter out common words and very short words (like single letters unless explicitly handled)
        cleaned_design_words = [word for word in design_words if word not in common_words_second_pass and len(word) > 1]

        # Special handling for initials or numerals might be needed here if 'initial x' or 'numeral 3' is common in titles
        # Example: if re.match(r'initial\s[a-z]', design): cleaned_design_words = [design] # Keep 'initial x' together

        second_pass_filter_term = " ".join(cleaned_design_words)

        print(f"  Cleaned filter term (Pass 2): '{second_pass_filter_term}'")
        if second_pass_filter_term: # Only filter if we have a meaningful term
             second_pass_results = [
                 item for item in first_pass_results
                 if item.get("jew_title") and second_pass_filter_term in item["jew_title"].lower()
             ]
             print(f"  Results after Pass 2 filter: {len(second_pass_results)}")
             if second_pass_results:
                 last_successful_pass = "Second Pass"
             else:
                  print("  No items matched the design filter in Pass 2. Reverting to Pass 1 results.")
                  second_pass_results = first_pass_results # Keep Pass 1 results if filter yields nothing
                  # Don't update last_successful_pass here
        else:
             print("  Skipping Pass 2 filter as cleaned design term is empty.")
             second_pass_results = first_pass_results # Pass all results if filter term is empty

    else:
        # If no design keyword or no Pass 1 results, Pass 2 results are the same as Pass 1
        print("\nSkipping Pass 2 filter (No design keyword or no Pass 1 results).")
        second_pass_results = first_pass_results


    # Pass 3: Filter Pass 2 results by *other* significant words from caption
    #------------------------------------------------------------
    current_results_for_third_pass = second_pass_results # Start with results from previous stage

    if current_results_for_third_pass and initial_caption:
        print(f"\nPass 3: Filtering {len(current_results_for_third_pass)} items by other keywords from caption")
        caption_lower = initial_caption.lower()
        # Keywords already used in search/filtering (don't reuse them)
        used_keywords = set([c.lower() for c in categories if c] +
                            [d.lower() for d in design.split() if d] +
                            [material.lower(), jew_type.lower()])

        # More comprehensive common/stop words list
        common_words = {
            "a", "an", "the", "this", "that", "these", "those", "and", "or", "but", "of", "with", "for", "on", "at","its"
            "to", "from", "by", "as", "it", "is", "are", "was", "were", "be", "been", "has", "have", "had","no",
            "in", "out", "up", "down", "over", "under", "above", "below", "image", "photo", "picture", "view",
            "background", "surface", "display", "close-up", "shot", "features", "featuring", "depicts","present"
            "shaped", "style", "design", "pattern", "piece", "item", "accessory", "jewelry", "wearable",
            "made", "set", "against", "shown", "engraved", # Add words commonly used in descriptions
             "color", "colored", # Generic color words
            # Add material/type words again to ensure they are excluded if already used
             "metal", "gold", "silver", "white", "yellow", "rose", "sterling",
             "ring", "pendant", "earring", "necklace", "bracelet", "charm", "band", "stud", "hoop","center"
        } | used_keywords # Combine common words with already used keywords

        # Extract potential keywords from caption
        words = re.findall(r'\b[a-z]{3,}\b', caption_lower) # Get lowercase words (3+ letters)
        unexpected_keywords = []

        for word in words:
            if word not in common_words:
                unexpected_keywords.append(word)
                # Limit to maybe 1-2 significant unexpected words found
                if len(unexpected_keywords) >= 1:
                    break

        print(f"  Potential unexpected keywords found: {unexpected_keywords}")

        if unexpected_keywords:
            # Combine unexpected words for the filter term
            third_pass_filter_term = " ".join(unexpected_keywords)
            print(f"  Filter term (Pass 3): '{third_pass_filter_term}'")
            third_pass_results = [
                 item for item in current_results_for_third_pass
                 if item.get("jew_title") and third_pass_filter_term in item["jew_title"].lower()
             ]
            print(f"  Results after Pass 3 filter: {len(third_pass_results)}")
            if third_pass_results:
                last_successful_pass = "Third Pass"
            else:
                print("  No items matched the unexpected words filter. Reverting to previous results.")
                third_pass_results = current_results_for_third_pass # Keep previous results if filter yields nothing
        else:
            print("  No significant unexpected words found for Pass 3 filter.")
            third_pass_results = current_results_for_third_pass # No filtering applied
    else:
         print("\nSkipping Pass 3 filter (No previous results or no caption).")
         third_pass_results = current_results_for_third_pass


    # --- Final Results Selection ---
    print("\n--- Final Search Summary ---")
    final_results_data = []
    source_pass_name = "N/A" # Rename variable for clarity

    # Prioritize results from the latest successful pass
    if last_successful_pass == "Third Pass" and third_pass_results:
        final_results_data = third_pass_results[:4] # Take top 4
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
        # If even Pass 1 failed or yielded no results initially
         if api_error_pass1:
             print("Search failed due to API error in the first pass.")
             return {"error": "Failed to retrieve initial search results from API.", "data": [], "total_found": 0, "source_pass": "N/A"}
         else:
             print("No similar products found across all search passes.")
             # Return empty data but indicate search was attempted
             return {"data": [], "total_found": 0, "source_pass": "None"}


    print(f"Source of final results: {source_pass_name}")
    print(f"Number of items in final_results_data: {len(final_results_data)}")

    final_results = {
        "data": final_results_data,
        "total_found": len(final_results_data), # Report the count of items *returned*
        "source_pass": source_pass_name,
        # Optionally include intermediate counts for debugging:
        # "debug_counts": {
        #     "pass1": len(first_pass_results),
        #     "pass2": len(second_pass_results) if 'second_pass_results' in locals() else 0,
        #     "pass3": len(third_pass_results) if 'third_pass_results' in locals() else 0
        # }
    }
    # print(f"Final results structure: {json.dumps(final_results, indent=2)}")
    return final_results

# --- Example Usage (Only runs when test4.py is executed directly) ---
if __name__ == "__main__":
    print("Running test4.py directly...")

    # Ensure client and API config are loaded before proceeding
    if not groq_client or not all([API_URL, API_APP, API_KEY, API_SECRET]):
         print("Exiting due to missing Groq client or API configuration.")
    else:
        # Test Image URL
        # image_url = "https://meteor.stullercloud.com/das/119159229?$xlarge$" # Heart Mama pendant
        # image_url = "https://example.com/path/to/another/jewelry_image.jpg" # Replace with a valid URL
        image_url = input("Enter image URL to test: ") # Make it interactive

        if image_url:
            print("\nStep 1: Generating Caption...")
            test_caption = generate_caption(image_url)

            if test_caption:
                print("\nStep 2: Creating JSON from Caption...")
                test_json = create_json_from_caption(test_caption)

                if test_json:
                    print("\nStep 3: Searching for Similar Products...")
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