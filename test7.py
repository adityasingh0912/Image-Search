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

    # Updated prompt for more detail, especially inscriptions/text
    prompt = """Describe this jewelry image concisely in one line. Highlight:
1.  Color (e.g., silver, gold, rose gold).
2.  Type (e.g., ring, pendant, earrings).
3.  Material if obvious (e.g., metal, pearl, diamond).
4.  Main shape or design (e.g., heart-shaped, floral, initial).
5.  Any text or specific words written/engraved on it (state the exact text if visible, e.g., 'engraved with "MAMA"'). If no text, do not mention it.
6.  Any prominent secondary features (e.g., 'with a central diamond', 'featuring blue gemstones').

Avoid generic words like 'jewelry'. Focus ONLY on the item itself, not the background."""


    try:
        # Ensure the model name is correct and available
        response = groq_client.chat.completions.create(
            model="llama-3.2-90b-vision-preview", # Using a capable model like llama-3.1-70b-versatile or llama-3.1-8b-instant might be sufficient
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]}
            ],
            max_tokens=150, # Slightly increased max_tokens
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
        return None

def create_json_from_caption(caption):
    """Use Groq's LLaMA to convert a jewelry caption into a JSON object, extracting only required info."""
    if not groq_client:
        print("Error: Groq client not initialized. Check API key.")
        return None

    print(f"Creating JSON from caption: {caption}")
    prompt = f"""
Given the following caption of a jewelry image, extract the following information and format it into a JSON object. Focus only on the jewelry item itself, ignoring background or irrelevant details. Extract only the most prominent and relevant features:

- **jewelry_type**: Possible values: Rings, Earrings, Pendants, Bracelets, Necklaces, Charms. Determine from context (e.g., 'pendant', 'ring'). Default to 'Pendants' if unclear.
- **material**: Identify the primary metal color or material mentioned (e.g., 'Sterling Silver', 'Yellow Gold', 'Rose Gold', 'White Gold', 'Diamond', 'Pearl'). Default to 'Sterling Silver' if only 'silver' or 'metal' is mentioned. Default to 'Yellow Gold' if only 'gold' is mentioned.
- **design**: Identify the primary shape or theme. Keep it concise (1-2 words):
    - Use 'heart' for heart shapes.
    - Use 'floral' for flower designs.
    - Use 'initial [letter]' for single letters (e.g., 'initial p' for 'P').
    - If specific text is mentioned (like "MAMA"), use that text (lowercase, e.g., 'mama').
    - Otherwise, provide a brief description (e.g., 'solitaire', 'geometric', 'cross'). Default to 'Abstract' if very unclear.
- **categories**: List up to 3 relevant tags representing key features or style. Include the main design/shape. Also include specific elements like 'diamond', 'pearl', 'engraved', 'gemstone' if mentioned. Examples: ['heart', 'diamond'], ['floral', 'pearl'], ['initial p', 'personalized'], ['mama', 'engraved', 'heart'].

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


# --- [UPDATED FUNCTION] ---
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
- Caption: "This silver-colored heart-shaped pendant features a central diamond." Used: [silver, heart, pendant, diamond]. Output: "" (no other *specific* unused feature)
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

    # Priority 1: Quoted text after specific verbs/nouns, allowing intervening words
    # Uses non-greedy matching .*? to find the *first* quote after the keyword
    # Searches for keywords like: inscribed, engraved, word, words, text
    # followed by potentially some words (like 'design of angels and the')
    # then the quoted text.
    inscription_match = re.search(r'(?:inscribed|engraved|word|words|text)[\s\w]*?["\']([^"\']+)["\']', caption_lower)
    if inscription_match:
        words = inscription_match.group(1).strip().split()
        # Return only the first few words if it's a long phrase, focus on core
        # If it looks like a common phrase, maybe keep more? Heuristic needed.
        # For now, keep first 3.
        keyword = " ".join(words[:3])
        # Basic check to avoid returning overly common stop-words if they were somehow captured alone
        if keyword in ["the", "a", "is", "of", "us", "me"]:
             return "" # Avoid returning just a stop word
        print(f"  DEBUG: Inscription regex matched: '{inscription_match.group(1)}', using: '{keyword}'") # Debug print
        return keyword

    # Priority 2: "initial X" where X is a single letter
    initial_match = re.search(r'initial\s+([a-z])', caption_lower)
    if initial_match:
        print(f"  DEBUG: Initial regex matched: 'initial {initial_match.group(1)}'") # Debug print
        return "initial " + initial_match.group(1) # Keep "initial" for clarity

    # Priority 3: Specific known phrases like "st. christopher"
    if "saint christopher" in caption_lower:
        print("  DEBUG: Found 'saint christopher'") # Debug print
        return "st. christopher" # Standardize

    # Priority 4: Fallback - Unquoted text immediately after verbs (less reliable)
    # Try to capture 1 or 2 words following the verb
    fallback_match = re.search(r'(?:inscribed|engraved)\s+([a-z]+(?:\s+[a-z]+)?)', caption_lower)
    if fallback_match:
        potential_keyword = fallback_match.group(1).strip()
        # Avoid generic words often following 'engraved' like 'design', 'pattern', 'text'
        if potential_keyword not in ["text", "words", "detail", "design", "pattern", "with", "on", "style"]:
            print(f"  DEBUG: Fallback regex matched: '{potential_keyword}'") # Debug print
            return potential_keyword
        else:
            print(f"  DEBUG: Fallback regex matched generic term '{potential_keyword}', ignoring.") # Debug print


    print("  DEBUG: No specific inscription pattern matched.") # Debug print
    return ""
# --- [UPDATED FUNCTION] ---
def search_similar_products(json_prompt, initial_caption):
    """Searches the Brilliance Hub API based on extracted JSON criteria using a multi-pass approach."""
    if not json_prompt or not isinstance(json_prompt, dict):
        print("Invalid JSON prompt provided to search function.")
        return {"error": "Invalid search criteria generated.", "data": [], "total_found": 0, "source_pass": "N/A"}
    if not HEADERS:
         print("Error: API headers not configured.")
         return {"error": "API configuration error.", "data": [], "total_found": 0, "source_pass": "N/A"}

    # --- Extract Core Criteria ---
    jew_type = json_prompt.get("jewelry_type", "Pendants").lower()
    design = json_prompt.get("design", "").lower().strip()
    # Handle potential "initial x" in design - just use the letter for broader matching?
    # design_for_filter = design.split()[-1] if design.startswith("initial ") and len(design.split()) == 2 else design
    design_for_filter = design # Keep full design for now, can refine later
    material = json_prompt.get("material", "Sterling Silver").lower().strip() # Defaulted to Sterling Silver as per JSON prompt
    # Normalize material names slightly for API title search if needed
    material_search_term = material.replace("sterling silver", "silver") # API titles might just say "Silver"
    categories = [cat.lower().strip() for cat in json_prompt.get("categories", []) if cat]

    print(f"\n--- Starting Search ---")
    print(f"Criteria: Type='{jew_type}', Design='{design}', Material='{material}', Categories={categories}")
    print(f"Initial Caption: '{initial_caption}'") # Print caption for context

    limit = 500 # Limit per API call
    max_total_results = 5000 # Max results to process overall
    first_pass_results = []
    second_pass_results = []
    third_pass_results = []
    last_successful_pass_data = [] # Store the actual data from the last successful pass
    source_pass_name = "N/A"

    # --- Pass 1: Broad API Search (Material/Color in Title + Categories in Style + Type) ---
    # Use categories from JSON directly for style filter
    search_style = [cat.capitalize() for cat in categories if cat]
    # Use normalized material for title search
    first_pass_title_term = material_search_term.capitalize()

    print(f"\nPass 1: Title='{first_pass_title_term}', Style={search_style}, Type={jew_type.capitalize() if jew_type else 'Any'}")
    offset = 0
    api_error_pass1 = False
    total_fetched_pass1 = 0
    while total_fetched_pass1 < max_total_results:
        batch_limit = min(limit, max_total_results - total_fetched_pass1)
        if batch_limit <= 0: break
        search_body = {
            "offset": offset, "limit": batch_limit, "title": first_pass_title_term, "style": search_style
        }
        # Only add type if it's specific (not 'any' or empty)
        if jew_type and jew_type != 'any':
            search_body["type"] = jew_type.capitalize()

        print(f"  API Request (Pass 1): {search_body}")
        try:
            response = requests.get(API_URL, headers=HEADERS, params=search_body, timeout=20) # Increased timeout
            print(f"  API Response Status (Pass 1): {response.status_code}")
            response.raise_for_status()
            results = response.json()
            current_batch = results.get("data", [])
            if not current_batch: # No more results
                print("  No more items found in this batch (Pass 1).")
                break

            first_pass_results.extend(current_batch)
            total_fetched_pass1 += len(current_batch)
            print(f"  Found {len(current_batch)} items in this batch (Pass 1). Total fetched: {total_fetched_pass1}")

            # Stop if we received fewer items than requested (means we reached the end for this query)
            if len(current_batch) < batch_limit:
                break

            offset += batch_limit # Prepare for next batch
            time.sleep(0.1) # Small delay between batches

        except requests.exceptions.Timeout:
            print(f"  Error: First pass API search timed out. Proceeding with fetched results.")
            api_error_pass1 = True # Mark as partial success
            break
        except requests.RequestException as e:
            print(f"  Error: First pass API search failed: {e}")
            api_error_pass1 = True
            break # Stop fetching on error
        except Exception as e:
            print(f"  Error: Unexpected error during first pass search: {e}")
            api_error_pass1 = True
            break # Stop fetching on unexpected error

    print(f"Total results collected from Pass 1: {len(first_pass_results)}")
    if first_pass_results:
        last_successful_pass_data = first_pass_results
        source_pass_name = "First Pass"

       # --- Pass 2: Filter Pass 1 results by Primary Design Keyword OR Specific Category ---
    current_results_for_filter = first_pass_results
    if design and current_results_for_filter: # Check design is not empty
        # Define generic design keywords that should be deprioritized for filtering
        generic_designs = {"engraved", "text", "personalized", "abstract", "metal", "geometric", "pattern"} # Add more if needed

        filter_term_pass2 = ""
        filter_source_pass2 = ""

        # Check if the main design is generic
        if design_for_filter in generic_designs:
            print(f"  Primary design '{design_for_filter}' is generic. Looking for specific category...")
            # Find the first category that is NOT generic and NOT the same as the design
            specific_category = next((cat for cat in categories if cat not in generic_designs and cat != design_for_filter), None)
            if specific_category:
                filter_term_pass2 = specific_category
                filter_source_pass2 = "Specific Category"
                print(f"  Using '{filter_term_pass2}' (from Categories) for Pass 2 filter.")
            else:
                # Fallback to the generic design if no better category found
                filter_term_pass2 = design_for_filter
                filter_source_pass2 = "Generic Design (Fallback)"
                print(f"  No specific category found. Falling back to generic design '{filter_term_pass2}' for Pass 2 filter.")
        else:
            # Use the specific design keyword if it's not generic
            filter_term_pass2 = design_for_filter
            filter_source_pass2 = "Primary Design"
            print(f"  Using primary design '{filter_term_pass2}' for Pass 2 filter.")

        # Perform the filtering using filter_term_pass2
        if filter_term_pass2:
            print(f"\nPass 2: Filtering {len(current_results_for_filter)} items based on {filter_source_pass2} '{filter_term_pass2}' in title/desc.")
            second_pass_results = [
                item for item in current_results_for_filter
                if item.get("jew_title") and filter_term_pass2 in item["jew_title"].lower()
                # Optionally add description check:
                # or (item.get("jew_desc") and filter_term_pass2 in item["jew_desc"].lower())
            ]
            print(f"  Results after Pass 2 filter: {len(second_pass_results)}")
            if second_pass_results:
                last_successful_pass_data = second_pass_results
                source_pass_name = "Second Pass"
            else:
                print(f"  Pass 2 filter with '{filter_term_pass2}' yielded no results. Keeping Pass 1 results.")
                second_pass_results = current_results_for_filter # Carry over Pass 1 results
        else:
             print("  No valid filter term determined for Pass 2. Skipping filter.")
             second_pass_results = current_results_for_filter # Pass results through

    else:
        print("\nSkipping Pass 2 filter (No design keyword specified or no Pass 1 results).")
        second_pass_results = current_results_for_filter # Pass results through

    # --- Pass 3: Refined Filter using Inscription, Secondary Category, or Fallback AI Keyword ---
    # (Pass 3 logic remains largely the same, but should now receive better input from Pass 2
    # and better inscription keyword from the updated extraction function)
    current_results_for_filter = second_pass_results # Results to filter in this pass
    if current_results_for_filter and initial_caption:
        print(f"\nPass 3: Refining {len(current_results_for_filter)} items using specific features...")
        third_pass_filter_term = ""
        filter_source = ""

        # 1. Check for Inscription (using updated function)
        inscription_keyword = extract_inscription_from_caption(initial_caption)
        if inscription_keyword:
            # Use the extracted inscription (already limited to ~3 words)
            third_pass_filter_term = inscription_keyword
            filter_source = "Inscription"
            print(f"  Using {filter_source} keyword for filtering: '{third_pass_filter_term}'")
            # Potential refinement: if inscription has > 1 word, also try searching only the last N-1 words?
            # E.g. "our guardian angel" -> try "guardian angel"? For now, use extracted keyword.

        # 2. Check for Secondary Category (if no inscription found)
        if not third_pass_filter_term:
            print(f"  No inscription found or extracted term was invalid. Checking for secondary category...")
            # Find categories NOT matching the primary design *used in Pass 2 filter*
            pass2_term_used = filter_term_pass2 # The term actually used in pass 2
            secondary_categories = [
                cat for cat in categories
                if cat != pass2_term_used and cat not in generic_designs # Exclude generic and the one used in Pass 2
            ]
            if secondary_categories:
                priority_cats = [cat for cat in secondary_categories if cat in ['diamond', 'pearl', 'gemstone', 'cz', 'cubic zirconia']]
                if priority_cats:
                   third_pass_filter_term = priority_cats[0]
                else:
                    third_pass_filter_term = secondary_categories[0] # Use the first non-generic, non-pass2 term
                filter_source = "Secondary Category"
                print(f"  Using {filter_source} keyword for filtering: '{third_pass_filter_term}'")
            else:
                print("  No suitable secondary category found.")


        # 3. Fallback to LLM Suggestion (if nothing found yet)
        if not third_pass_filter_term:
            print("  No inscription or distinct secondary category suitable for Pass 3. Trying LLM fallback...")
            # (LLM fallback logic remains the same)
            # ... rest of LLM fallback code ...

        # Apply the filter if a term was found
        if third_pass_filter_term:
             print(f"  Applying Pass 3 filter ({filter_source}): '{third_pass_filter_term}'")
             # Apply filter (check title first, maybe description as fallback)
             third_pass_results = [
                item for item in current_results_for_filter
                if item.get("jew_title") and third_pass_filter_term in item["jew_title"].lower()
                 # Optionally add description check:
                 # or (item.get("jew_desc") and third_pass_filter_term in item["jew_desc"].lower())
            ]
             # **** ADDED LOGIC: If exact phrase fails, try core words ****
             if not third_pass_results and filter_source == "Inscription" and len(third_pass_filter_term.split()) > 1:
                 core_terms = third_pass_filter_term.split()[1:] # Try without the first word (e.g., "guardian angel" from "our guardian angel")
                 core_term_filter = " ".join(core_terms)
                 if core_term_filter and core_term_filter != third_pass_filter_term: # Ensure it's different and not empty
                     print(f"  Initial Pass 3 filter failed. Retrying with core inscription term: '{core_term_filter}'")
                     third_pass_results = [
                         item for item in current_results_for_filter
                         if item.get("jew_title") and core_term_filter in item["jew_title"].lower()
                     ]

             print(f"  Results after Pass 3 ({filter_source}) filter: {len(third_pass_results)}")
             if third_pass_results:
                 last_successful_pass_data = third_pass_results
                 source_pass_name = "Third Pass"
             else:
                 print(f"  Pass 3 filter with '{third_pass_filter_term}' (and potential core terms) yielded no matches. Reverting to previous results.")
                 third_pass_results = current_results_for_filter # Carry over
        else:
            print("  No specific filter term found for Pass 3. Skipping filter.")
            third_pass_results = current_results_for_filter # Pass results through

    else:
         print("\nSkipping Pass 3 refinement (No previous results or no caption).")
         third_pass_results = current_results_for_filter # Pass results through

    # --- Final Results Selection ---

    # --- Final Results Selection ---
    print("\n--- Final Search Summary ---")
    # Use the data from the latest pass that yielded results (stored in last_successful_pass_data)
    final_results_data = last_successful_pass_data[:4] # Return top 4

    if final_results_data:
         print(f"Using results from {source_pass_name}. Found {len(last_successful_pass_data)}, returning top {len(final_results_data)}.")
    else:
         # Handle cases where even Pass 1 failed or returned nothing
         if api_error_pass1 and not first_pass_results:
             print("Search failed due to API error in the first pass and no results were fetched.")
             return {"error": "Failed to retrieve initial search results from API.", "data": [], "total_found": 0, "source_pass": "N/A"}
         elif not first_pass_results:
              print("No products found matching the initial criteria in Pass 1.")
              return {"data": [], "total_found": 0, "source_pass": "None"}
         else:
              # This case means Pass 1 worked, but subsequent filters removed everything.
              print("Filters in Pass 2 or 3 removed all results. No similar products found matching all criteria.")
              # Optionally, return Pass 1 results here as a fallback?
              # final_results_data = first_pass_results[:4]
              # source_pass_name = "First Pass (Fallback)"
              # print(f"Falling back to results from {source_pass_name}. Found {len(first_pass_results)}, returning top {len(final_results_data)}.")
              # If strict filtering is desired, return empty:
              return {"data": [], "total_found": 0, "source_pass": source_pass_name} # source_pass reflects the last *attempted* filter stage


    print(f"Source of final results: {source_pass_name}")
    print(f"Number of items in final_results_data: {len(final_results_data)}")

    final_results = {
        "data": final_results_data,
        "total_found": len(final_results_data), # Report the number returned
        "source_pass": source_pass_name,
        # Optionally include total found before limiting to 4
        "total_found_before_limit": len(last_successful_pass_data)
    }
    return final_results


# --- [Example Usage (_main_ block) - SAME AS BEFORE] ---
if __name__ == "__main__":
    print("Running test4.py directly...")

    if not groq_client or not HEADERS:
         print("Exiting due to missing Groq client or API configuration.")
    else:
        # Default URL for faster testing, uncomment input for interactive use
        # image_url = "https://www.overnightmountings.com/gemfind/library/Images_And_Videos/30925/30925.jpg"
        # image_url = "https://meteor.stullercloud.com/das/119159229?$xlarge$"
        image_url = input("Enter image URL to test: ")


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
                    # Pass the original caption to the search function
                    test_results = search_similar_products(test_json, test_caption)
                    print(f"Search time: {time.time() - start_time:.2f}s")


                    print("\n--- Final Test Results ---")
                    if test_results:
                        # Print total found before limit if available
                        total_before_limit = test_results.get('total_found_before_limit')
                        if total_before_limit is not None:
                            print(f"Total items found by '{test_results.get('source_pass', 'N/A')}': {total_before_limit}")

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