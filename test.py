import re
import requests
import time
import json
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# ----------------------
# Hugging Face Setup
# ----------------------
hf_client = InferenceClient(token=os.getenv("HF_TOKEN"))

# ----------------------
# Brilliance Hub API Setup
# ----------------------
API_URL = os.getenv("API_URL")
HEADERS = {
    "x-api-app": os.getenv("API_APP"),
    "x-api-key": os.getenv("API_KEY"),
    "x-api-secret": os.getenv("API_SECRET"),
    "Content-Type": "application/json"
}

# ----------------------
# Define STYLES_MAP
# ---------------------
STYLES_MAP = {
    "religious": "Religious",
    "crosses": "Crosses",
    "saints medals": "Saints Medals",
    "fashion": "Fashion",
    "halo": "Halo",
    "initials": "Initials",
    "solitaire": "Solitaire",
    "3 stone": "3 Stone",
    "personalized": "Personalized",
    "novelty": "Novelty",
    "cluster": "Cluster",
    "spiritual": "Spiritual",
    "circle": "Circle",
    "accented": "Accented",
    "zodiac": "Zodiac",
    "stars": "Stars",
    "geometric": "Geometric",
    "numerals": "Numerals",
    "infinity": "Infinity",
    "mother and child": "Mother and Child"
}

# ----------------------
# Define Number Words and Jewelry Types
# ----------------------
number_words = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10"
}

jewelry_types = {
    "Rings": ["ring", "rings"],
    "Earrings": ["earring", "earrings"],
    "Earring jackets": ["earring jacket", "earring jackets"],
    "Pendants": ["pendant", "pendants"],
    "Bracelets": ["bracelet", "bracelets"],
    "Necklaces": ["necklace", "necklaces"],
    "Charms": ["charm", "charms"],
    "Dangles": ["dangle", "dangles"],
    "Pins": ["pin", "pins"],
    "Cuff links": ["cuff link", "cuff links"],
    "Watch supplies": ["watch supply", "watch supplies"]
}

# ----------------------
# Define All Possible Categories
# ----------------------
ALL_CATEGORIES = [
    "rings", "no stones", "classic precious", "necklaces", "earrings",
    "pendants", "diamond", "metal", "gemstone", "chain",
    "fancy non-precious", "fancy precious", "studs", "dangles", "religious",
    "nature", "symbols", "metal rings", "bracelets", "hoops",
    "initials", "anniversary bands", "accented", "solitaire", "metal necklaces",
    "watch supplies", "matching bands", "gemstone rings", "cable", "crosses",
    "personalized", "religious necklaces", "enhancer", "bypass", "freeform",
    "stackable", "saints medals", "drops", "rope", "contour bands",
    "milled product", "packaging", "chain bracelets", "halo", "bulk chain",
    "chain per inch", "family", "box", "signet", "youth",
    "eternity bands", "with stones", "wheat", "line", "spiritual",
    "beads", "bar", "displays", "cabochon", "numerals",
    "curb", "charms", "classic non-precious", "top", "guard",
    "bangles", "cuffs", "geometric", "jackets", "utility",
    "novelty", "elongated cable", "religious earrings", "coin", "figaro",
    "negative space", "ring", "metal accessories", "rolo", "flat",
    "links", "round", "crucifixes", "engagement", "judaica",
    "3 stone", "station", "multi stone", "zodiac", "angels",
    "snake", "ash holders", "pins", "two stone", "laser wire",
    "single ring", "leather", "pad", "religious accessories", "link",
    "mens", "flap earring", "lockets", "mirror", "lapel pins",
    "cord necklaces", "climbers", "cluster", "insert", "settings",
    "strand", "anchor", "chastity", "religious bracelets", "rosary",
    "sellable products", "tray", "cuff links", "layout", "solder",
    "family accessories", "mother and child", "herringbone", "singapore", "dome",
    "gifts", "nugget", "peg setting", "layout bracelet", "straight", "double ring",
    "orthodox", "trim plated roses", "yellow gold", "plumb cadmium free", "stand", "omega",
    "vintage", "base", "repair cadmium free", "dangle", "wrap", "pattern",
    "communion medals", "pillow bracelet", "diamond accessories", "half round", "serpentine", "rubber",
    "tower base", "us mint", "confirmation medals", "general accessories", "dog tags", "multifunctional",
    "square", "enhancers", "id", "t-pad earring", "brooches", "cuff",
    "peg shank", "adapters", "cuff link part", "drop", "pillow", "stretch",
    "bezel", "raso", "words", "baptismal medals", "ear form",
    "gemstone and diamond", "money clips", "neckform", "popcorn", "ring roll", "classic",
    "gemstone accessories", "right hand", "signage", "tie bars", "twist", "cuff link components",
    "doves", "open shank", "standard", "heart", "hiyw", "jewelry cards",
    "jewelry supplies", "journey", "prototypes", "selling systems", "single stone with plain shank", "watch buckles", "watch components",
    "backboard", "book", "byzantine", "clip-ons", "foxtail", "full plated roses",
    "lariats", "mounting components", "royal canadian mint", "satin", "silk", "silvertowne",
    "states", "top setting", "triangle", "cord", "gallery", "key",
    "marketing media", "oval", "platinum", "roses displays", "single stone with side stones", "bails",
    "cable wire", "case", "cause for paws", "customer", "fancy bands", "fob bail",
    "ghi", "heart u back", "non-serialized diamond", "post", "rosary centers", "rose gold",
    "shank setting", "stuller", "tapered bail"
]

# ----------------------
# Helper Function to Detect Jewelry Type
# ----------------------
def detect_jewelry_type(caption_lower):
    for type_name, keywords in jewelry_types.items():
        if any(keyword in caption_lower for keyword in keywords):
            return type_name
    return "Pendants"  # Default

# ----------------------
# Function to Extract Styles
# ----------------------
def extract_styles_from_caption(caption):
    found_styles = []
    caption_lower = caption.lower()
    for style_key, style_value in STYLES_MAP.items():
        if style_key in caption_lower:
            found_styles.append(style_value)
    return found_styles

# ----------------------
# Generate Caption
# ----------------------
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

# ----------------------
# Create JSON Prompt
# ----------------------
def create_json_prompt(caption, image_url):
    if not caption:
        print("No caption provided. Cannot create JSON prompt.")
        return None

    caption_lower = caption.lower()

    # Detect jewelry type
    jew_type = detect_jewelry_type(caption_lower)

    # Material detection for search title
    material_terms = []
    if "silver" in caption_lower:
        material_terms.append("sterling silver")
    if "rose" in caption_lower:
        material_terms.append("rose")
    elif "yellow" in caption_lower or "gold" in caption_lower:
        material_terms.append("yellow")

    # Design detection with number word conversion
    design = ""
    target_design = None
    design_type = None

    m_number = re.search(r'number\s+(\w+)', caption_lower)
    if m_number:
        num_str = m_number.group(1)
        if num_str.isdigit():
            design = f"{num_str}"
            target_design = design
            design_type = "numeral"
        elif num_str in number_words:
            design = f"{number_words[num_str]}"
            target_design = design
            design_type = "numeral"

    m_letter = re.search(r'(?:\bletter\s+|\binitial\s+)([A-Za-z])\b', caption_lower)
    if not design and m_letter:
        letter = m_letter.group(1).upper()
        design = f"Initial {letter}"
        target_design = letter
        design_ype = "letter"
    elif not design:
        m_initial_word = re.search(r'\binitial\s+([A-Za-z]+)', caption_lower)
        if m_initial_word:
            candidate = m_initial_word.group(1)
            if len(candidate) == 1:
                letter = candidate.upper()
                design = f"Initial {letter}"
                target_design = letter
                design_type = "letter"
            else:
                design = candidate.capitalize()

    # Capture other design-related words, prioritizing "diamond" before shape
    if not design:
        design_keywords = []
        has_diamond = "diamond" in caption_lower
        shape_matches = re.findall(r'\b(heart|circle|square|oval|triangle|rectangle)\s+shaped\b|\b(heart|circle|square|oval|triangle|rectangle|shaped|round)\b', caption_lower)

        if has_diamond:
            design_keywords.append("Diamond")
            for match in shape_matches:
                if match[0]:
                    design_keywords.append(match[0].replace(" shaped", "").capitalize() + "-Shaped")
                elif match[1] and match[1] != "diamond": # Avoid adding diamond again
                    design_keywords.append(match[1].capitalize())
        else:
            for match in shape_matches:
                if match[0]:
                    design_keywords.append(match[0].replace(" shaped", "").capitalize() + "-Shaped")
                elif match[1]:
                    design_keywords.append(match[1].capitalize())

        other_matches = re.findall(r'\b(shape|design)\s+of\s+(\w+)\b', caption_lower)
        for match in other_matches:
            design_keywords.append(match[1].capitalize())

        if design_keywords:
            # Remove duplicates while preserving order as much as possible
            unique_design_keywords = []
            seen = set()
            for keyword in design_keywords:
                if keyword not in seen:
                    unique_design_keywords.append(keyword)
                    seen.add(keyword)
            design = " ".join(unique_design_keywords)

    # Set search title with design and material terms
    search_title = f"{' '.join(material_terms)} {design}".strip() if design else ' '.join(material_terms)

    # Material for display (jew_title)
    if "white" in caption_lower:
        material = "silver"
    elif "rose " in caption_lower:
        material = "Rose"
    elif "gold" in caption_lower:
        material = "Yellow"
    elif "silver" in caption_lower:
        material = "Sterling Silver"
    else:
        material = "Metal" # Default if no specific metal is found

    # Check for diamond mention
    has_diamond_title = "diamond" in caption_lower
    style = "Dog Tag" if "dog tag" in caption_lower else "Pendant"
    finish = "Polished"

    # Build jewellery title for display
    jew_title = f"{material} {design} {style}".strip() # Remove potential leading/trailing spaces

    # Base categories
    jew_categories = []
    if design.startswith("Numeral"):
        jew_categories.append("numerals")
    elif design.startswith("Initial"):
        jew_categories.append("initials")
    if has_diamond_title:
        jew_categories.append("diamond")
    if "dog tag" in caption_lower:
        jew_categories.append("dog tags")

    style_matches = extract_styles_from_caption(caption)
    jew_categories.extend(style_matches)

    # Add categories from the ALL_CATEGORIES list if found in caption
    for category in ALL_CATEGORIES:
        if re.search(rf'\b{re.escape(category)}\b', caption_lower):
            if category not in jew_categories:
                jew_categories.append(category)

    # Build jewellery description
    jew_desc_items = [
        f"<li><strong>Finish State:</strong> {finish}</li>",
        f"<li><strong>Product:</strong> {style}</li>",
        f"<li><strong>Material:</strong> {material}</li>",
        f"<li><strong>Design:</strong> {design}</li>"
    ]
    if has_diamond_title:
        jew_desc_items.append("<li><strong>Feature:</strong> Diamond Inlay</li>")
    jew_desc = f"<ol>{''.join(jew_desc_items)}</ol>"

    json_prompt = {
        "jew_title": jew_title,
        "jew_type": jew_type,
        "search_title": search_title,
        "jew_categories": jew_categories,
        "jew_desc": jew_desc,
        "jew_images": [image_url],
        "jew_videos": [],
        "jew_default_img": image_url,
        "jew_finish_level": finish,
        "target_design": target_design,
        "design_type": design_type,
        "material_terms": material_terms,
        "design": design
    }

    print("Generated JSON Prompt:")
    print(json.dumps(json_prompt, indent=4))
    return json_prompt
# ----------------------
# Filter Results (from your first code snippet)
# ----------------------
def filter_results(results, target_design, design_type, material_terms):
    if not results or "data" not in results:
        return None

    filtered_data = []
    pattern = re.compile(fr"\b{re.escape(target_design)}\b", re.IGNORECASE) if target_design else None

    for item in results["data"]:
        title = item.get("jew_title", "").lower()
        desc = item.get("jew_desc", "").lower()

        # Check if any material term is in title or description
        if not any(term.lower() in title or term.lower() in desc for term in material_terms):
            continue

        # Check if design pattern matches (if provided)
        if pattern and (pattern.search(title) or pattern.search(desc)):
            filtered_data.append(item)
        elif not pattern:
            filtered_data.append(item)

    return {"data": filtered_data} if filtered_data else None

# ----------------------
# Search Similar Products (from your first code snippet, adapted for Brilliance Hub API)
# ----------------------
def search_similar_products(json_prompt):
    if not json_prompt:
        print("Invalid JSON prompt. Cannot search for similar products.")
        return None

    jew_type = json_prompt["jew_type"]
    design = json_prompt["design"]  # Use the general 'design' here
    material_terms = json_prompt["material_terms"]
    categories = json_prompt.get("jew_categories", [])  # Get categories from prompt
    limit = 20
    max_attempts = 3
    all_results = []

    shape_words = ["shaped", "round", "heart", "circle", "square", "oval", "triangle", "rectangle"]

    # Combine material terms into a single query
    if material_terms:
        offset = 0
        combined_material = ' '.join(material_terms)  # e.g., "sterling silver rose"
        search_title = f"{combined_material} {design}".strip()
        print(f"Combined search title: {search_title}")

        # Replace space with hyphen between "diamond" and "shaped" if needed
        for shape in shape_words:
            search_title = re.sub(r"(?i)(\bdiamond\b)[\s\-]+(\bshaped\b)", r"\1-\2", search_title)

        while offset < max_attempts * limit:
            search_body = {
                "offset": offset,
                "limit": limit,
                "type": jew_type,
                "title": search_title,
                "style": categories  # Use categories as styles in the API request
            }
            print(f"Sending API request with params: {search_body}")
            try:
                response = requests.get(API_URL, headers=HEADERS, params=search_body)
                response.raise_for_status()
                results = response.json()
                print("Raw API Results:")
                print(json.dumps(results, indent=4))

                if "data" in results:
                    all_results.extend(results["data"])
                if len(results.get("data", [])) < limit:
                    break  # No more results to fetch
                offset += limit
            except requests.RequestException as e:
                print(f"Search failed: {e}")
                offset += limit

    if not all_results:
        print("No results found for the given criteria.")
        return None

    # Remove duplicates based on a unique identifier (e.g., jew_title)
    unique_results = {item["jew_title"]: item for item in all_results}.values()
    combined_results = {"data": list(unique_results)}

    # Filter combined results
    filtered_results = filter_results(
        combined_results,
        target_design=json_prompt.get("target_design"),  # Keep target_design for filtering initials/numerals
        design_type=json_prompt.get("design_type"),
        material_terms=material_terms
    )

    if filtered_results and filtered_results["data"]:
        filtered_results["data"] = filtered_results["data"][:2]  # Limit to 2 results as per original
        filtered_results["total_found"] = len(filtered_results["data"])
        return filtered_results

    print("No items matched the criteria after filtering.")
    return None


# ----------------------
# Main Function
# ----------------------
def find_similar_products(image_url):
    caption = generate_caption(image_url)
    if not caption:
        print("Failed to generate caption. Cannot proceed.")
        return

    json_prompt = create_json_prompt(caption, image_url)
    if not json_prompt:
        print("Failed to create JSON prompt. Cannot proceed.")
        return

    results = search_similar_products(json_prompt)
    if results:
        print("Search Results:")
        print(json.dumps(results, indent=4))
    else:
        print("No similar products found.")

# ----------------------
# Run Example
# ----------------------
if __name__ == "__main__":
    image_url = "https://meteor.stullercloud.com/das/78579355?$xlarge$"
    find_similar_products(image_url)