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


# --- [Core Functions: image_to_base64, generate_caption, create_json_from_caption, get_additional_keywords_with_llm, extract_inscription_from_caption - SAME AS BEFORE] ---
def image_to_base64(image_path_or_url):
    """
    Fetches an image from a URL or reads from a local path,
    and converts it to base64.
    """
    content = None
    is_url = image_path_or_url.startswith('http://') or image_path_or_url.startswith('https://')

    if is_url:
        print(f"  Fetching image from URL: {image_path_or_url}")
        try:
            response = requests.get(image_path_or_url, timeout=15) # Slightly longer timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            content = response.content
        except requests.exceptions.Timeout:
            print(f"  Error: Timeout while fetching image URL: {image_path_or_url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"  Error: Failed to download or access image URL: {image_path_or_url}. Error: {e}")
            return None
        except Exception as e:
            print(f"  Error: Unexpected error fetching URL {image_path_or_url}: {e}")
            return None
    else:
        # Assume it's a local file path
        print(f"  Reading image from local path: {image_path_or_url}")
        try:
            # Check if file exists before opening
            if not os.path.exists(image_path_or_url):
                 print(f"  Error: File not found at path: {image_path_or_url}")
                 return None
            # Open in binary read mode
            with open(image_path_or_url, 'rb') as image_file:
                content = image_file.read()
        except IOError as e:
            print(f"  Error: Could not read file at path: {image_path_or_url}. Error: {e}")
            return None
        except Exception as e:
            print(f"  Error: Unexpected error reading file {image_path_or_url}: {e}")
            return None

    # Proceed with base64 encoding if content was successfully obtained
    if content:
        try:
            base64_encoded = base64.b64encode(content).decode('utf-8')
            print(f"  Successfully converted image source '{os.path.basename(image_path_or_url)}' to base64.")
            return base64_encoded
        except Exception as e:
            print(f"  Error converting image content to base64: {e}")
            return None
    else:
        # This case should theoretically be caught by earlier checks, but as a fallback
        print(f"  Error: Failed to obtain image content for {image_path_or_url}")
        return None

def generate_caption(image_path_or_url): # Rename parameter for clarity
    """Send base64 image to LLaMA Vision model for captioning."""
    if not groq_client:
        print("Error: Groq client not initialized. Check API key.")
        return None

    print(f"Attempting to generate caption for source: {image_path_or_url}")
    # Call the updated image_to_base64 function
    image_base64 = image_to_base64(image_path_or_url)
    if not image_base64:
        print("Image conversion to base64 failed.")
        return None # Return None if base64 conversion failed

    # Updated prompt for more detail, especially inscriptions/text (SAME AS BEFORE)
    prompt = """Describe this jewelry image concisely in 1-2 lines. Highlight:
1.  Color (e.g., silver, gold, rose gold).
2.  Type (e.g., ring, pendant, earrings).
3.  Material if obvious (e.g., metal, pearl, diamond).
4.  Main shape or design (e.g., heart-shaped, floral, initial).
5.  Any text or specific words written/engraved on it (state the exact text if visible, e.g., 'engraved with "MAMA"'). If no text, do not mention it.
6.  Any prominent secondary features (e.g., 'with a central diamond', 'featuring blue gemstones').

Avoid generic words like 'jewelry'. Do NOT focus on the backgroud of the item. Only include the features that directly relate to the jewelry item itself."""

    try:
        # Ensure the model name is correct and available (SAME AS BEFORE)
        response = groq_client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}} # Keep format as jpeg for simplicity unless specific need arises
                ]}
            ],
            max_tokens=150,
            temperature=0.1
        )

        caption = response.choices[0].message.content.strip()
        print(f"Generated Caption: {caption}")
        return caption

    except Exception as e:
        print(f"Error in LLaMA vision request: {e}")
        if "rate limit" in str(e).lower():
             print("Rate limit likely exceeded. Waiting before retry...")
        # Consider adding retries or specific error handling here
        return None # Return None on LLM error as well

def create_json_from_caption(caption):
    """Use Groq's LLaMA to convert a jewelry caption into a JSON object, extracting only required info."""
    if not groq_client:
        print("Error: Groq client not initialized. Check API key.")
        return None

    print(f"Creating JSON from caption: {caption}")
    prompt = f"""
Given the following caption of a jewelry image, extract the following information and format it into a JSON object. Focus only on the jewelry item itself, ignoring background or irrelevant details. Extract only the most prominent and relevant features:

- **jewelry_type**: Possible values: Rings, Earrings, Pendants, Bracelets, Necklaces, Charms. Determine from context (e.g., 'pendant', 'ring'). Default to 'Pendants' if unclear.
- **material**: Identify the primary metal color or material mentioned (e.g., 'Sterling Silver', 'Yellow', 'Rose', 'Diamond', 'Pearl'). Default to 'Sterling Silver' if only 'silver' or 'metal' is mentioned. Default to 'Yellow' if only 'gold' is mentioned.
- **design**: Identify the primary shape or theme. Keep it concise (1-2 words):
    - Use 'heart' for heart shapes.
    - Use 'floral' for flower designs.
    - Use 'initial [letter]' for single letters (e.g., 'initial p' for 'P').
    - If specific text is mentioned (like "MAMA"), use that text (lowercase, e.g., 'mama').
    - Otherwise, provide a brief description (e.g., 'solitaire', 'geometric', 'cross', 'angel'). Default to 'Abstract' if very unclear.
- **categories**: List up to 3 relevant tags representing key features or style. Include the main design/shape. Also include specific elements like 'diamond', 'pearl', 'engraved', 'gemstone' if mentioned. Examples: ['heart', 'diamond'], ['floral', 'pearl'], ['initial p', 'personalized'], ['mama', 'engraved', 'heart'], ['angel', 'engraved', 'text'].

Provide the response STRICTLY as a JSON object only, without any introductory text or markdown formatting like ```json.

Caption: "{caption}"
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Use a capable text model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        llm_output = response.choices[0].message.content.strip()

        print("Raw LLM Output (should be JSON):")
        print(llm_output)

        # Attempt to clean potential markdown ```json ``` artifacts before parsing
        cleaned_llm_output = re.sub(r'^```json\s*|\s*```$', '', llm_output, flags=re.MULTILINE | re.DOTALL).strip()

        json_data = json.loads(cleaned_llm_output)
        print("Parsed JSON data:", json_data)
        return json_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Problematic LLM Output (raw): {llm_output}")
        print(f"Problematic LLM Output (cleaned): {cleaned_llm_output}")
        # Attempt a fallback parse if simple cleaning didn't work
        try:
            # Find the first '{' and last '}'
            start = cleaned_llm_output.find('{')
            end = cleaned_llm_output.rfind('}')
            if start != -1 and end != -1 and start < end:
                json_str = cleaned_llm_output[start:end+1]
                json_data = json.loads(json_str)
                print("Parsed JSON data (after fallback cleaning):", json_data)
                return json_data
            else:
                print("Fallback JSON cleaning failed.")
                return None
        except json.JSONDecodeError as e2:
            print(f"Fallback JSON Decode Error: {e2}")
            return None
    except Exception as e:
        print(f"Error in LLaMA JSON creation request: {e}")
        return None


def get_additional_keywords_with_llm(caption, used_keywords_set):
    """
    Fallback function: Use LLM to suggest 1 additional keyword from caption,
    focusing on specific features *if* inscription/category methods failed.
    """
    if not groq_client:
        print("Error: Groq client not initialized for additional keyword extraction.")
        return ""

    print("    Attempting AI suggestion for Pass 3 keywords (Fallback)...")
    # Convert set to a readable list for the prompt
    used_keywords_list = ", ".join(filter(None, used_keywords_set)) # Filter out potential None or empty strings

    # Revised prompt focusing on specific features as a fallback
    prompt = f"""
Analyze the following jewelry caption:
"{caption}"

The following keywords have already been considered or used for searching:
[{used_keywords_list}]

Identify exactly one *additional specific feature* keyword from the caption that is NOT in the list above and is NOT a generic filler/common word (like 'a', 'the', 'is', 'with', 'set', 'image', 'background', 'features', 'center', 'shaped', 'pendant', 'ring', 'metal', 'color'). Focus on words describing:
- Specific stone types (e.g., sapphire, emerald, ruby)
- Specific patterns (e.g., filigree, hammered)
- Other distinct visual elements not already covered.

Return ONLY the identified keyword as a single lowercase word, or return an empty string if no suitable additional specific keyword is found. Do not add any explanation.

Examples:
- Caption: "Gold ring with intricate filigree pattern and a central ruby." Used: [gold, ring, ruby, pattern]. Output: filigree
- Caption: "Silver pendant showing a hammered texture." Used: [silver, pendant, texture]. Output: hammered
- Caption: "This silver-colored heart-shaped pendant features a central diamond." Used: [silver, heart, pendant, diamond]. Output: "diamond"
- Caption: "A delicate bracelet with a floral design with blue gemstone." Used: [delicate, bracelet, floral]. Output: "blue"
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant", # Use a fast model for this refinement task
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20, # Expect short output
            temperature=0.1,
            stop=["\n"] # Stop generation early if needed
        )
        keywords = response.choices[0].message.content.strip().lower()

        # Basic cleaning: remove potential quotes or extra formatting
        keywords = keywords.replace('"', '').replace("'", "").strip()

        # Validate the keyword is not empty and not obviously generic
        generic_fallback_words = {"central", "main", "small", "large", "intricate", "detailed"}
        if keywords and keywords not in used_keywords_set and keywords not in generic_fallback_words:
            print(f"    AI suggested fallback keyword: '{keywords}'")
            return keywords
        else:
            print(f"    AI fallback did not suggest a suitable new keyword ('{keywords}').")
            return "" # Return empty if suggestion is bad or empty

    except Exception as e:
        print(f"    Error during AI fallback keyword suggestion: {e}")
        return "" # Return empty on error


def extract_inscription_from_caption(caption):
    """
    Attempt to extract inscription details from the caption.
    Prioritizes quoted text after 'inscribed', 'engraved', 'word(s)', 'text'.
    Allows intervening words between the verb/noun and the quote.
    Also handles 'initial X' and 'st. christopher'.
    Returns a lowercase keyword/phrase (max 3 words) or empty string.
    """
    caption_lower = caption.lower()
    print("  DEBUG: Starting inscription extraction...") # Added debug start

    # Priority 1: Quoted text after specific verbs/nouns, allowing intervening words
    inscription_match = re.search(r'(?:inscribed|engraved|word|words|text)[\s\w]*?["\']([^"\']+)["\']', caption_lower)
    if inscription_match:
        words = inscription_match.group(1).strip().split()
        keyword = " ".join(words[:3])
        if keyword in ["the", "a", "is", "of", "us", "me"]:
             print(f"  DEBUG: Inscription regex matched stop-word only: '{inscription_match.group(1)}', ignoring.") # Debug print
             return ""
        print(f"  DEBUG: Inscription regex matched: '{inscription_match.group(1)}', using: '{keyword}'") # Debug print
        return keyword

    # Priority 2: "initial X" where X is a single letter
    initial_match = re.search(r'initial\s+([a-z])', caption_lower)
    if initial_match:
        print(f"  DEBUG: Initial regex matched: 'initial {initial_match.group(1)}'") # Debug print
        return "initial " + initial_match.group(1)

    # Priority 3: Specific known phrases like "st. christopher"
    if "saint christopher" in caption_lower:
        print("  DEBUG: Found 'saint christopher'") # Debug print
        return "st. christopher"

    # Priority 4: Fallback - Unquoted text immediately after verbs (less reliable)
    fallback_match = re.search(r'(?:inscribed|engraved)\s+([a-z]+(?:\s+[a-z]+)?)', caption_lower)
    if fallback_match:
        potential_keyword = fallback_match.group(1).strip()
        if potential_keyword not in ["text", "words", "detail", "design", "pattern", "with", "on", "style"]:
            print(f"  DEBUG: Fallback regex matched: '{potential_keyword}'") # Debug print
            return potential_keyword
        else:
            print(f"  DEBUG: Fallback regex matched generic term '{potential_keyword}', ignoring.") # Debug print

    print("  DEBUG: No specific inscription pattern matched.") # Debug print
    return ""

def extract_additional_color(caption):
    """
    Extracts a color mentioned in the caption that is not one of the standard colors:
    'gold', 'silver', or 'rose'. Returns the first non-standard color found,
    or an empty string if none are found.
    """
    # Define standard colors (all in lowercase)
    standard_colors = {"gold", "silver", "rose"}
    # Define a simple list of common color names
    common_colors = {"red", "blue", "green", "black", "purple", "pink", "orange", "brown", "gray", "grey"}
    # Search for color words in the caption
    colors_found = re.findall(r'\b(' + '|'.join(common_colors) + r')\b', caption.lower())
    for color in colors_found:
        if color not in standard_colors:
            return color
    return ""

def search_similar_products(json_prompt, initial_caption, desired_limit=10):
    """
    Searches the Brilliance Hub API based on extracted JSON criteria using a multi-pass approach.
    If the jewelry type is 'Pendants', searches both 'Pendants' and 'Necklaces'.
    Attempts to return a specific number of results (desired_limit) by backfilling from less specific passes.
    """
    if not json_prompt or not isinstance(json_prompt, dict):
        print("Invalid JSON prompt provided to search function.")
        return {"error": "Invalid search criteria generated.", "data": [], "total_found": 0, "source_pass": "N/A"}
    if not HEADERS:
        print("Error: API headers not configured.")
        return {"error": "API configuration error.", "data": [], "total_found": 0, "source_pass": "N/A"}

    # Extract criteria from JSON prompt
    jew_type = json_prompt.get("jewelry_type", "Pendants").lower()
    design = json_prompt.get("design", "").lower().strip()
    design_for_filter = design
    material = json_prompt.get("material", "Sterling Silver").lower().strip()
    material_search_term = material.replace("sterling silver", "silver")
    categories = [cat.lower().strip() for cat in json_prompt.get("categories", []) if cat]
    generic_designs = {"engraved", "text", "personalized", "abstract", "metal", "geometric", "pattern", "solitaire", "circular", "round", "gemstone"}

    print(f"\n--- Starting Search ---")
    print(f"Desired Results: {desired_limit}")
    print(f"Criteria: Type='{jew_type}', Design='{design}', Material='{material}', Categories={categories}")
    print(f"Initial Caption: '{initial_caption}'")

    limit_per_call = 500
    max_total_results_fetch = 5000
    first_pass_results = []
    second_pass_results = []
    third_pass_results = []
    api_error_pass1 = False

    # --- Determine Search Types ---
    if jew_type == "pendants":
        search_types = ["Pendants", "Necklaces"]
        print(f"Searching for both 'Pendants' and 'Necklaces' since jewelry type is 'Pendants'.")
    else:
        search_types = [jew_type.capitalize()]
        print(f"Searching for '{search_types[0]}'.")

    # --- Pass 1: Broad API Search Across Search Types ---
    search_style = [cat.capitalize() for cat in categories if cat]
    first_pass_title_term = material_search_term.capitalize()
    added_ids = set()

    for search_type in search_types:
        print(f"Fetching results for type '{search_type}'...")
        offset = 0
        while len(first_pass_results) < max_total_results_fetch:
            batch_limit = min(limit_per_call, max_total_results_fetch - len(first_pass_results))
            if batch_limit <= 0:
                break
            search_body = {
                "offset": offset,
                "limit": batch_limit,
                "title": first_pass_title_term,
                "style": search_style,
                "type": search_type
            }
            print(f"  API Request (Pass 1, Type={search_type}): {search_body}")
            try:
                response = requests.get(API_URL, headers=HEADERS, params=search_body, timeout=20)
                print(f"  API Response Status (Pass 1, Type={search_type}): {response.status_code}")
                response.raise_for_status()
                results = response.json()
                current_batch = results.get("data", [])
                if not current_batch:
                    break
                for item in current_batch:
                    item_id = item.get("id")
                    if item_id and item_id not in added_ids:
                        first_pass_results.append(item)
                        added_ids.add(item_id)
                        if len(first_pass_results) >= max_total_results_fetch:
                            break
                if len(current_batch) < batch_limit or len(first_pass_results) >= max_total_results_fetch:
                    break
                offset += batch_limit
                time.sleep(0.1)
            except requests.exceptions.Timeout:
                print(f"  Error: Pass 1 API search timed out for type '{search_type}'. Proceeding with {len(first_pass_results)} fetched results.")
                api_error_pass1 = True
                break
            except requests.RequestException as e:
                print(f"  Error: Pass 1 API search failed for type '{search_type}': {e}")
                api_error_pass1 = True
                break
            except Exception as e:
                print(f"  Error: Unexpected error during Pass 1 for type '{search_type}': {e}")
                api_error_pass1 = True
                break
    print(f"Total unique results collected from Pass 1: {len(first_pass_results)}")

    # --- Pass 2: Filter Pass 1 results by an Additional Color (if available) or by Primary Design/Specific Category ---
    pass2_input_results = first_pass_results
    used_filter_term_pass2 = ""
    filter_source_pass2 = ""

    # First, try to extract an additional color from the caption
    additional_color = extract_additional_color(initial_caption)
    if additional_color:
        used_filter_term_pass2 = additional_color
        filter_source_pass2 = "Additional Color"
        print(f"\nPass 2: Using additional color '{used_filter_term_pass2}' for filtering.")
    elif design:
        # If design is generic, try to pick a specific category from the categories list.
        if design_for_filter in generic_designs:
            print(f"\nPass 2: Primary design '{design_for_filter}' is generic. Looking for specific category...")
            specific_category = next((cat for cat in categories if cat not in generic_designs and cat != design_for_filter), None)
            if specific_category:
                used_filter_term_pass2 = specific_category
                filter_source_pass2 = "Specific Category"
                print(f"Pass 2: Using '{used_filter_term_pass2}' (from Categories) for filtering.")
            else:
                used_filter_term_pass2 = design_for_filter
                filter_source_pass2 = "Generic Design (Fallback)"
                print(f"Pass 2: No specific category found. Falling back to generic design '{used_filter_term_pass2}' for filtering.")
        else:
            used_filter_term_pass2 = design_for_filter
            filter_source_pass2 = "Primary Design"
            print(f"\nPass 2: Using primary design '{used_filter_term_pass2}' for filtering.")
    else:
        print("\nPass 2: No design keyword or additional color provided; skipping Pass 2 filtering.")
        used_filter_term_pass2 = ""

    if used_filter_term_pass2:
        print(f"Pass 2: Filtering {len(pass2_input_results)} items based on {filter_source_pass2} '{used_filter_term_pass2}'...")
        second_pass_results = [
            item for item in pass2_input_results
            if item.get("jew_title") and used_filter_term_pass2 in item["jew_title"].lower()
        ]
        print(f"  Results after Pass 2 filter: {len(second_pass_results)}")
    else:
        second_pass_results = pass2_input_results


    # --- Pass 3: Refined Filter Using a New Filter Term (avoiding Pass 2's term) ---
    # If Pass 2 returned no results, use Pass 1 results.
    if not second_pass_results:
        print("No results found in Pass 2; using Pass 1 results for Pass 3 filtering.")
        pass3_input_results = first_pass_results
    else:
        pass3_input_results = second_pass_results

    third_pass_filter_term = ""
    filter_source_pass3 = ""
    if pass3_input_results and initial_caption:
        print(f"\nPass 3: Refining {len(pass3_input_results)} items using specific features...")

        # 1. Check for a non-standard color in the caption
        color_keyword = extract_additional_color(initial_caption)
        if color_keyword and color_keyword != used_filter_term_pass2:
            third_pass_filter_term = color_keyword
            filter_source_pass3 = "Non-standard Color"
            print(f"  Using {filter_source_pass3} keyword for filtering: '{third_pass_filter_term}'")

        # 2. If no valid color found, check for inscription
        if not third_pass_filter_term:
            inscription_keyword = extract_inscription_from_caption(initial_caption)
            if inscription_keyword and inscription_keyword != used_filter_term_pass2:
                third_pass_filter_term = inscription_keyword
                filter_source_pass3 = "Inscription"
                print(f"  Using {filter_source_pass3} keyword for filtering: '{third_pass_filter_term}'")

        # 3. If still nothing, check Secondary Category (skipping term used in Pass 2)
        if not third_pass_filter_term:
            print("  No color or inscription found/valid. Checking secondary category...")
            secondary_categories = [cat for cat in categories if cat != used_filter_term_pass2 and cat not in generic_designs]
            if secondary_categories:
                third_pass_filter_term = secondary_categories[0]
                filter_source_pass3 = "Secondary Category"
                print(f"  Using {filter_source_pass3} keyword for filtering: '{third_pass_filter_term}'")
            else:
                print("  No suitable secondary category found.")

        # 4. Fallback to LLM if still no filter term
        if not third_pass_filter_term:
            print("  No specific filter term found. Trying LLM fallback...")
            used_keywords = set([c.lower() for c in categories if c] +
                                [d.lower() for d in design.split() if d] +
                                [material.lower(), jew_type.lower(), material_search_term.lower()] +
                                [used_filter_term_pass2])
            common_words_for_ai = {
                "a", "an", "the", "this", "that", "these", "those", "and", "or", "but", "of", "with", "for", "on", "at", "its",
                "to", "from", "by", "as", "it", "is", "are", "was", "were", "be", "been", "has", "have", "had", "no",
                "in", "out", "up", "down", "image", "photo", "picture", "view", "background", "surface", "display",
                "features", "shaped", "style", "design", "pattern", "piece", "item", "accessory", "jewelry", "wearable",
                "made", "set", "against", "shown", "engraved", "center"
            }
            full_exclusion_set = used_keywords.union(common_words_for_ai)
            llm_keyword = get_additional_keywords_with_llm(initial_caption, full_exclusion_set)
            if llm_keyword and llm_keyword != used_filter_term_pass2:
                third_pass_filter_term = llm_keyword
                filter_source_pass3 = "AI Fallback"
                print(f"  Using {filter_source_pass3} keyword for filtering: '{third_pass_filter_term}'")

        # Final check: if the term for Pass 3 is identical to Pass 2's term, skip Pass 3 filtering.
        if third_pass_filter_term == used_filter_term_pass2:
            print(f"  Pass 3 filter term '{third_pass_filter_term}' is identical to Pass 2 filter term; skipping Pass 3 filtering.")
            third_pass_results = pass3_input_results
        else:
            if third_pass_filter_term:
                print(f"  Applying Pass 3 filter ({filter_source_pass3}): '{third_pass_filter_term}'")
                temp_results = [
                    item for item in pass3_input_results
                    if item.get("jew_title") and third_pass_filter_term in item["jew_title"].lower()
                ]
                third_pass_results = temp_results
                print(f"  Results after Pass 3 ({filter_source_pass3}) filter: {len(third_pass_results)}")
            else:
                print("  No specific filter term found for Pass 3. Skipping filter.")
                third_pass_results = pass3_input_results
    else:
         print("\nSkipping Pass 3 refinement (No previous results or no caption).")
         third_pass_results = pass3_input_results

    # --- Final Results Combination and Selection ---
    print("\n--- Combining and Selecting Final Results ---")
    combined_results = []
    added_ids = set()
    source_pass_name = "None"
    total_found_before_limit_primary = 0

    def add_unique(items_list, limit):
        count_added = 0
        for item in items_list:
            item_id = item.get("id")
            if item_id and item_id not in added_ids and len(combined_results) < limit:
                combined_results.append(item)
                added_ids.add(item_id)
                count_added += 1
        return count_added

    if third_pass_results:
        print(f"Adding up to {desired_limit - len(combined_results)} from Pass 3 ({len(third_pass_results)} available)...")
        add_unique(third_pass_results, desired_limit)
        source_pass_name = "Third Pass"
        total_found_before_limit_primary = len(third_pass_results)
    if len(combined_results) < desired_limit and second_pass_results:
        print(f"Adding up to {desired_limit - len(combined_results)} from Pass 2 ({len(second_pass_results)} available)...")
        added_count = add_unique(second_pass_results, desired_limit)
        if added_count > 0 and source_pass_name == "None":
            source_pass_name = "Second Pass"
            total_found_before_limit_primary = len(second_pass_results)
    if len(combined_results) < desired_limit and first_pass_results:
        print(f"Adding up to {desired_limit - len(combined_results)} from Pass 1 ({len(first_pass_results)} available)...")
        added_count = add_unique(first_pass_results, desired_limit)
        if added_count > 0 and source_pass_name == "None":
            source_pass_name = "First Pass"
            total_found_before_limit_primary = len(first_pass_results)

    print("\n--- Final Search Summary ---")
    if combined_results:
         print(f"Returning {len(combined_results)} combined results (Desired: {desired_limit}).")
         print(f"Primary source pass contributing results: {source_pass_name} (found {total_found_before_limit_primary} items before combining).")
    else:
         if api_error_pass1 and not first_pass_results:
             print("Search failed due to API error in the first pass and no results were fetched.")
             return {"error": "Failed to retrieve initial search results from API.", "data": [], "total_found": 0, "source_pass": "N/A"}
         elif not first_pass_results:
              print("No products found matching the initial criteria in Pass 1.")
              return {"data": [], "total_found": 0, "source_pass": "None"}
         else:
              print("No products found matching any criteria across all passes.")
              return {"data": [], "total_found": 0, "source_pass": source_pass_name if source_pass_name != "None" else "Filters Failed"}

    print(f"Source Pass indicated: {source_pass_name}")
    print(f"Number of items in final_results_data: {len(combined_results)}")

    final_results = {
        "data": combined_results,
        "total_found": len(combined_results),
        "source_pass": source_pass_name,
        "total_found_by_primary_source": total_found_before_limit_primary
    }
    return final_results

# --- [Example Usage (_main_ block)] ---
if __name__ == "__main__":
    print("Running test4.py directly...")

    if not groq_client or not HEADERS:
         print("Exiting due to missing Groq client or API configuration.")
    else:
        image_url = input("Enter image URL to test: ")
        desired_num_results = 10 # Set your desired number of results here

        if image_url:
            print("\nStep 1: Generating Caption...")
            start_time = time.time()
            test_caption = generate_caption(image_url)
            print(f"Caption generation time: {time.time() - start_time:.2f}s")

            if test_caption:
                print("\nStep 2: Creating JSON from Caption...")
                start_time = time.time()
                test_json = create_json_from_caption(test_caption)
                print(f"JSON creation time: {time.time() - start_time:.2f}s")

                if test_json:
                    print("\nStep 3: Searching for Similar Products...")
                    start_time = time.time()
                    # Pass the desired limit to the search function
                    test_results = search_similar_products(test_json, initial_caption=test_caption, desired_limit=desired_num_results)
                    print(f"Search time: {time.time() - start_time:.2f}s")

                    print("\n--- Final Test Results ---")
                    if test_results and "error" not in test_results:
                        # Print total found by the primary source if available
                        total_primary = test_results.get('total_found_by_primary_source')
                        source_p = test_results.get('source_pass', 'N/A')
                        if total_primary is not None and source_p != "None":
                             print(f"Total items found by primary source '{source_p}': {total_primary}")

                        print(json.dumps(test_results, indent=4))
                        print(f"\nTotal items returned: {test_results.get('total_found', 0)} (aimed for {desired_num_results})")
                        print(f"Primary Source Pass: {source_p}")
                    elif test_results and "error" in test_results:
                         print(f"Search Error: {test_results['error']}")
                    else:
                        print("Search function returned None or an unexpected structure.")
                else:
                    print("\nFailed to create JSON prompt.")
            else:
                print("\nFailed to generate caption.")
        else:
            print("No image URL provided.")