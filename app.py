# app.py
import os
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Import the core logic functions from test4.py
# Make sure test4.py is in the same directory
try:
    from test5 import generate_caption, create_json_from_caption, search_similar_products
except ImportError:
    print("Error: Could not import functions from test4.py. Make sure it exists in the same directory.")
    # Optionally exit or raise a more specific error
    exit(1)


# Load environment variables from .env file
# This is still useful for Flask configuration or if test4.py doesn't load them itself.
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# --- Flask Routes ---

@app.route('/')
def index():
    """Serve the main HTML page."""
    # Ensure your index.html is in a 'templates' subfolder
    return render_template('index.html')

@app.route('/find_similar_jewelry', methods=['POST'])
def find_similar_jewelry_route():
    """Endpoint to handle image URL and return similar jewelry by calling functions from test4.py."""
    data = request.get_json()
    if not data or 'image_url' not in data:
        print("Error: Missing 'image_url' in request payload.")
        return jsonify({"error": "Missing 'image_url' in request."}), 400

    image_url = data['image_url']
    print(f"\nReceived request for image URL: {image_url}")

    # --- Call the processing pipeline functions imported from test4.py ---
    try:
        print("Step 1: Calling generate_caption from test4.py")
        caption = generate_caption(image_url) # Function from test4.py
        if not caption:
            print("Failed to generate caption using test4.generate_caption.")
            # Provide a user-friendly error message back to the frontend
            return jsonify({"error": "Could not analyze the image. Please try a different image or URL.", "data": [], "total_found": 0}), 500

        print(f"Step 2: Calling create_json_from_caption from test4.py with caption: {caption}")
        json_prompt = create_json_from_caption(caption) # Function from test4.py
        if not json_prompt:
            print("Failed to create JSON prompt using test4.create_json_from_caption.")
            return jsonify({"error": "Could not understand the features of the jewelry in the image.", "data": [], "total_found": 0}), 500

        print(f"Step 3: Calling search_similar_products from test4.py with JSON prompt: {json_prompt}")
        # Assuming search_similar_products returns a dict, potentially with an 'error' key
        results = search_similar_products(json_prompt, caption) # Function from test4.py

        # Check if the search function itself indicated an error
        if isinstance(results, dict) and results.get("error"):
             print(f"Error reported by search_similar_products: {results['error']}")
             # Pass the specific error message to the frontend if available
             return jsonify({"error": results.get("error", "Search failed."), "data": [], "total_found": 0}), 500

        # Ensure results is a dictionary before adding the caption
        if not isinstance(results, dict):
             print("Error: search_similar_products did not return a dictionary.")
             return jsonify({"error": "Internal server error during search.", "data": [], "total_found": 0}), 500

    except Exception as e:
        # Catch any unexpected errors during the calls to test4 functions
        print(f"An unexpected error occurred during processing: {e}")
        # Log the full traceback for debugging if needed
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred. Please check server logs.", "data": [], "total_found": 0}), 500
    # --- End processing pipeline ---

    # Add the generated caption to the results sent back to the frontend
    # (Do this only if processing was successful and results is a dict)
    results['generated_caption'] = caption

    print("Processing complete. Sending results back to frontend.")
    # print(f"Final results being sent: {json.dumps(results, indent=2)}") # Optional: log final results
    return jsonify(results)

if __name__ == '__main__':
    # Make sure DEBUG is False in production
    # Use host='0.0.0.0' to make it accessible on your network if needed
    app.run(debug=True, port=5001, host='0.0.0.0')