// static/script.js

// Expose global functions for modal actions
window.closeModal = closeModal;
window.openModalWithDetails = openModalWithDetails; // Expose the new modal function

// Global variable (can keep or remove if not used elsewhere)
let lastQuery = ""; // Stores the last successful image URL query

/**
 * Close the details modal and clear its content.
 */
function closeModal() {
    const modal = document.getElementById("detailsModal");
    const modalDetails = document.getElementById("modalDetails");
    if (modal) {
        modal.style.display = "none";
    }
    if (modalDetails) {
        modalDetails.innerHTML = ""; // Clear content on close
    }
}

/**
 * Add a chat message bubble to the chat interface.
 * Handles both plain text and HTML content for bot messages.
 */
function addMessage(messageContent, isUser = false) {
    const chatMessages = document.getElementById("chatMessages");
    if (!chatMessages) return; // Exit if chat container not found

    // Create message container
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message");
    msgDiv.classList.add(isUser ? "user-message" : "bot-message");

    // Create avatar
    const avatarDiv = document.createElement("div");
    avatarDiv.classList.add("avatar");
    avatarDiv.classList.add(isUser ? "user-avatar" : "bot-avatar");
    const avatarIcon = document.createElement("i");
    avatarIcon.classList.add("fas");
    // Add user icon if user, otherwise robot icon
    avatarIcon.classList.add(isUser ? "fa-user" : "fa-robot"); // Ensure correct icons are added
    avatarDiv.appendChild(avatarIcon);

    // Create bubble
    const bubble = document.createElement("div");
    bubble.classList.add("bubble");
    bubble.classList.add(isUser ? "user-bubble" : "bot-bubble");

    // IMPORTANT: Render HTML content directly for bot messages (cards, errors with links etc.)
    // Use textContent for user messages to prevent XSS from user input
    if (isUser) {
        bubble.textContent = messageContent;
    } else {
        // Check if the content looks like HTML (contains '<'), otherwise treat as text
        if (typeof messageContent === 'string' && messageContent.includes('<')) {
            bubble.innerHTML = messageContent; // Render HTML from bot
            // If the bubble contains cards, remove default bubble padding/background
            if (bubble.querySelector('.jewelry-cards-in-chat')) {
                 // Apply styles defined in CSS :has selector if browser supports it,
                 // otherwise manually apply similar styles here as a fallback if needed.
                 // Modern browsers supporting :has should handle this via CSS.
                 // For older browser compatibility (if needed):
                 // bubble.style.padding = '0';
                 // bubble.style.background = 'transparent';
                 // bubble.style.border = 'none';
                 // bubble.style.maxWidth = '100%';
            } else if (messageContent.trim() === '...') {
                // Optional: Style the 'thinking' placeholder differently if desired
                bubble.style.fontStyle = 'italic';
                bubble.style.opacity = '0.8';
            }
        } else {
            bubble.textContent = messageContent; // Render plain text from bot
        }
    }

    // Append elements in the correct order
    if (isUser) {
        // User message: Bubble first, then Avatar
        msgDiv.appendChild(bubble);
        msgDiv.appendChild(avatarDiv);
    } else {
        // Bot message: Avatar first, then Bubble
        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(bubble);
    }

    chatMessages.appendChild(msgDiv);
    // Scroll to the bottom of the chat messages
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Update the text content and visibility of the search results bar.
 */
function updateSearchResultsBar(text) {
    const searchResultsBar = document.getElementById("search-results-bar");
    if (searchResultsBar) {
        searchResultsBar.textContent = text;
        // Show the bar only if there is text content
        searchResultsBar.style.display = text ? "block" : "none";
    }
}

/**
 * Check if a string is a plausible image URL.
 * Includes checks for common image domains and extensions.
 */
function isValidHttpUrl(string) {
  let url;
  try {
    // Require http:// or https://
    if (!string.startsWith('http://') && !string.startsWith('https://')) {
        console.log("URL doesn't start with http:// or https://");
        return false;
    }
    url = new URL(string);
  } catch (_) {
    console.log("Invalid URL format");
    return false;
  }
  // Basic check for http/https protocols
  const protocolOk = url.protocol === "http:" || url.protocol === "https:";
  if (!protocolOk) {
      console.log("Protocol is not http or https");
      return false;
  }

  // Check for common image extensions in the pathname
  const extensionOk = /\.(jpg|jpeg|png|gif|webp|bmp|svg|avif)(\?.*)?(#.*)?$/i.test(url.pathname);
  // Allow URLs without explicit extensions if they are from common image hosting/CDN domains
  // Expanded list - adjust as needed
  const servicePathOk = /stullercloud|cloudinary|shopify|cdn\.shopify\.com|amazon|aws|etsy|imgix|googleusercontent|gravatar|unsplash|pexels|pixabay|imgbb|postimg|imgur|media\.giphy\.com/i.test(url.hostname);

  console.log(`URL: ${string}, Extension OK: ${extensionOk}, Service Path OK: ${servicePathOk}`);

  // The URL must have a valid protocol AND either a recognized extension OR come from a recognized service domain
  // OR potentially just have a hostname if we want to be very lenient (might allow non-images)
  const isValid = protocolOk && (extensionOk || servicePathOk || url.hostname); // Be slightly more lenient

  if (!isValid) {
      console.log("URL failed extension and service path checks.");
  }
  return isValid;
}


/**
 * Parse jewelry data from the backend response and display results.
 */
function handleJewelryData(responseData) {
    // Expected structure: { data: [...], total_found: X, source_pass: '...', generated_caption: '...' }
    const jewelryData = responseData.data;
    const totalFound = responseData.total_found || 0; // Use total_found from response
    const sourcePass = responseData.source_pass || "N/A"; // Which search pass yielded results
    const generatedCaption = responseData.generated_caption; // Caption generated by vision model

    // Add the generated caption as a bot message first (if available)
    if (generatedCaption) {
         addMessage(`Okay, I see: "${generatedCaption}"`, false);
    } else {
         addMessage("I analyzed the image.", false); // Fallback message
    }


    if (!jewelryData || jewelryData.length === 0) {
        updateSearchResultsBar("No similar jewelry found.");
        addMessage("Sorry, I couldn't find any similar items based on that image.", false);
        return;
    }

    // Update search results bar - report the number *returned* (which is total_found in the current backend logic)
    updateSearchResultsBar(`Found ${totalFound} similar item(s). (Results from: ${sourcePass})`);

    // Build HTML for jewelry cards
    // Ensure using consistent class names defined in CSS
    let cardsHtml = `<div class="jewelry-cards-in-chat">`;

    for (const jewelry of jewelryData) {
        // Safely parse price and format it
        const price = parseFloat(jewelry.jew_sell_price);
        // Use 'en-US' for consistent formatting, adjust locale if needed
        const priceFormatted = !isNaN(price) ? formatPrice(price, jewelry.currency_sym || '$') : 'Price N/A';

        // Safely get image, title - provide fallbacks
        const imageUrl = jewelry.jew_default_img || 'static/placeholder.png'; // Ensure a placeholder exists
        const imageAlt = jewelry.jew_title || 'Jewelry Item';
        const title = jewelry.jew_title || 'Untitled Jewelry';

        // Safely stringify the object for the onclick handler, escaping quotes properly
        // Use JSON.stringify and then encode for HTML attribute context
        let jewelryObjString;
        try {
            jewelryObjString = JSON.stringify(jewelry);
        } catch (e) {
            console.error("Error stringifying jewelry data for modal:", e, jewelry);
            continue; // Skip this card if data is problematic
        }
        // Escape characters that would break the HTML attribute
        const escapedJewelryObjString = jewelryObjString
            .replace(/&/g, '&')
            .replace(/'/g, '')
            .replace(/"/g, '"')
            .replace(/</g, '<')
            .replace(/>/g, '>')

        // Card structure using CSS classes defined earlier
        cardsHtml += `
        <div class="jewelry-card-in-chat">
            <img src="${imageUrl}"
                 alt="${imageAlt}"
                 class="jewelry-card-image"
                 onerror="this.onerror=null; this.src='static/placeholder.png';"> {/* Handle image errors */}
            <div class="jewelry-card-content"> {/* Added wrapper for content below image */}
                <div class="jewelry-header">
                    <div class="jewelry-title" title="${title}">${title}</div>
                    <div class="jewelry-price">${priceFormatted}</div>
                </div>
                <button class="view-details-btn" onclick='openModalWithDetails(JSON.parse(this.dataset.jewelry))' data-jewelry='${escapedJewelryObjString}'>
                     View Details
                </button>
            </div>
        </div>
        `;
    }
    cardsHtml += `</div>`;

    // Display the generated cards HTML in a bot message bubble
    addMessage(cardsHtml, false);
}

/**
 * Helper function to format price, handling potential non-USD currency.
 */
function formatPrice(value, currencySymbol = '$') {
    try {
        // Use Intl.NumberFormat for potentially better locale support in the future
        const formatted = Number(value).toLocaleString('en-US', { // Force US locale for consistency for now
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        return `${currencySymbol}${formatted}`;
    } catch (e) {
        console.warn("Price formatting error:", e);
        // Fallback to simple prefixing
        return `${currencySymbol}${Number(value).toFixed(2)}`; // Ensure 2 decimal places in fallback
    }
}

/**
 * Open a modal window displaying detailed information about a jewelry item.
 * Expects a JavaScript object (already parsed).
 */
function openModalWithDetails(jewelry) {
    const modal = document.getElementById("detailsModal");
    const modalDetails = document.getElementById("modalDetails");
    if (!modal || !modalDetails || typeof jewelry !== 'object' || jewelry === null) {
        console.error("Modal elements not found or invalid jewelry data provided:", jewelry);
        return; // Exit if modal elements aren't found or data is bad
    }

    console.log("Opening modal with details:", jewelry); // Log the data being used

    // Safely parse and format the price
    const price = parseFloat(jewelry.jew_sell_price);
    const formattedPrice = !isNaN(price) ? formatPrice(price, jewelry.currency_sym || '$') : 'Price N/A';

    // Safely get other details with fallbacks
    const title = jewelry.jew_title || 'Jewelry Details';
    const mainImageUrl = jewelry.jew_default_img || 'static/placeholder.png';
    const sku = jewelry.jew_sku || 'N/A';
    const company = jewelry.jew_company || 'N/A';
    const status = jewelry.jew_status || 'N/A';
    const type = jewelry.jew_type || 'N/A';
    const categories = Array.isArray(jewelry.jew_categories) ? jewelry.jew_categories.join(', ') : 'N/A';
    const description = jewelry.jew_desc || ''; // Default to empty string
    const images = Array.isArray(jewelry.jew_images) ? jewelry.jew_images : [];
    const videos = Array.isArray(jewelry.jew_videos) ? jewelry.jew_videos : [];

    // Build the modal's inner HTML content
    let modalHtml = `
        <h2>${title}</h2>
        <div class="modal-layout">

            <div class="modal-image-section">
                 <img src="${mainImageUrl}"
                      alt="${title}"
                      class="jewelry-modal-image-main"
                      onerror="this.onerror=null; this.src='static/placeholder.png';">
                 ${images.length > 1 ? `
                     <div class="modal-thumbnails">
                         ${images.map(imgUrl =>
                             `<img src="${imgUrl}"
                                  class="thumbnail"
                                  alt="Thumbnail"
                                  onclick="document.querySelector('.jewelry-modal-image-main').src='${imgUrl}'"
                                  onerror="this.style.display='none';">` // Hide broken thumbnails
                         ).join('')}
                     </div>
                 ` : ''}
            </div>

             <div class="modal-details-section">
                <div class="diamond-specs-grid">
                    <p>Price: <strong>${formattedPrice}</strong></p>
                    <p>Type: <strong>${type}</strong></p>
                    <p>SKU: <strong>${sku}</strong></p>
                    <p>Company: <strong>${company}</strong></p>
                    <p>Status: <strong>${status}</strong></p>
                    <p>Categories: <strong>${categories || 'N/A'}</strong></p> {/* Handle empty string case */}
                </div>

                ${description ? `
                    <div class="jewelry-modal-desc">
                        <strong>Description:</strong>
                        <div>${description.replace(/\n/g, '<br>')}</div> {/* Render newlines as breaks */}
                    </div>
                ` : ''}
             </div>

             ${videos.length > 0 ? `
                 <div class="modal-video-column">
                     <div class="jewelry-modal-video-container">
                          <iframe
                              src="${videos[0]}" class="jewelry-modal-video"
                              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                              allowfullscreen
                              frameborder="0"
                              title="Jewelry Video"
                          ></iframe>
                     </div>
                     ${videos.length > 1 ? `<p style="text-align: center; font-size: 12px; margin-top: 5px;">Video 1 of ${videos.length}</p>` : ''}
                 </div>
             ` : ''}
        </div>
    `;

    // Set the generated HTML content into the modal details container
    modalDetails.innerHTML = modalHtml;
    // Display the modal
    modal.style.display = "flex";

    // Add event listener to close modal when clicking outside the content
    modal.addEventListener('click', function(event) {
        if (event.target === modal) { // Check if the click is on the modal backdrop itself
            closeModal();
        }
    }, { once: true }); // Remove listener after first click outside
}

/**
 * Initialize event listeners when the DOM is fully loaded.
 */
document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById("chatMessages");
    const sendButton = document.getElementById("sendButton");
    const userInput = document.getElementById("userInput");

    // Optional: Set initial chat message container height based on viewport
    if (chatMessages) {
        const calculatedHeight = Math.max(window.innerHeight * 0.4, 250); // Adjust multiplier/min height
        chatMessages.style.maxHeight = `${calculatedHeight}px`;
        console.log(`Chat max-height set based on viewport: ${calculatedHeight}px`);
    }

    // Setup Send Button Listener
    if (sendButton) {
        sendButton.addEventListener("click", sendMessage);
    } else {
        console.error("Send button not found!");
    }

    // Setup Enter Key Listener for the input field
    if (userInput) {
        userInput.addEventListener("keypress", function(event) {
            // Check if Enter key was pressed (and not Shift+Enter for potential multi-line input)
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault(); // Prevent default form submission or newline
                sendMessage();
            }
        });
    } else {
        console.error("User input field not found!");
    }

    // Add listener to close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const modal = document.getElementById("detailsModal");
            if (modal && modal.style.display === 'flex') {
                closeModal();
            }
        }
    });

    // Optional: Image Upload Listener (if functionality is added)
    /*
    const imageUploadInput = document.getElementById('imageUpload'); // Assume input type file exists
    const uploadButton = document.getElementById('uploadButton'); // Assume a button exists to trigger upload
    if (imageUploadInput && uploadButton) {
        uploadButton.addEventListener('click', () => imageUploadInput.click()); // Trigger file input
        imageUploadInput.addEventListener('change', handleImageUpload);
    }
    */
});

 /**
  * Optional: Handle image upload if input[type=file] is used
  * This requires backend changes to handle file uploads (e.g., using FormData)
  */
 /*
 function handleImageUpload(event) {
     const file = event.target.files[0];
     if (file) {
         // Basic file type check (optional but recommended)
         if (!file.type.startsWith('image/')) {
             addMessage('Please select an image file.', false);
             return;
         }
         // Basic size check (optional)
         if (file.size > 5 * 1024 * 1024) { // e.g., 5MB limit
             addMessage('Image file is too large (max 5MB).', false);
             return;
         }

         addMessage(`Preparing to upload image: ${file.name}`, true); // Show user the filename
         updateSearchResultsBar(`Analyzing uploaded image...`);
         addMessage("...", false); // Thinking placeholder

         const formData = new FormData();
         formData.append('imageFile', file); // Key must match backend expectation (e.g., request.files['imageFile'])

         // Send to a DIFFERENT backend endpoint designed for file uploads
         fetch('/find_similar_jewelry_upload', { // Ensure this endpoint exists in Flask
             method: 'POST',
             body: formData
             // No 'Content-Type' header needed; browser sets it correctly for FormData
         })
         .then(response => {
             if (!response.ok) {
                  // Try to parse error JSON, otherwise use status text
                  return response.json().then(errData => {
                      throw new Error(errData.error || `Upload failed: ${response.statusText} (Status: ${response.status})`);
                  }).catch(() => { // Catch if response is not JSON
                      throw new Error(`Upload failed: ${response.statusText} (Status: ${response.status})`);
                  });
             }
             return response.json();
         })
         .then(data => {
             removeThinkingPlaceholder(); // Remove "..."
             if (data.error) {
                  handleFetchError(new Error(data.error)); // Handle logical errors from backend
             } else if (data.data) {
                  handleJewelryData(data); // Process response same way as URL search
             } else {
                  handleFetchError(new Error("Received an unexpected response after upload."));
             }
         })
         .catch(err => {
              removeThinkingPlaceholder(); // Ensure "..." is removed on error
              handleFetchError(err); // Display error in chat
         });

         // Clear the file input for the next upload
         event.target.value = null;
     }
 }
 */


/**
 * Sends the image URL entered by the user to the backend for processing.
 */
function sendMessage() {
    const input = document.getElementById("userInput");
    if (!input) {
        console.error("User input field not found in sendMessage.");
        return;
    }

    const message = input.value.trim();
    if (!message) {
        // Maybe add a visual cue instead of a message? Or keep the message.
        // input.placeholder = "Please enter an image URL first!";
        addMessage("Please paste an image URL first.", false); // Inform user if input is empty
        return;
    }

    // Validate if the input looks like a plausible image URL
    if (!isValidHttpUrl(message)) {
         addMessage("Hmm, that doesn't look like a valid image URL. Please check and make sure it starts with http:// or https:// and points to an image file (e.g., .jpg, .png) or a known image service.", false);
         input.focus(); // Keep focus on input for easy correction
         return;
    }

    // Update UI: Show user message, clear input, show searching status
    addMessage(message, true); // Display the URL the user entered
    lastQuery = message; // Store the URL as the last query
    input.value = ""; // Clear the input field
    input.placeholder = "Paste another image URL..."; // Update placeholder
    updateSearchResultsBar(`Searching for jewelry similar to image...`);
    addMessage("...", false); // Add a "Thinking..." placeholder message

    // Send the image URL to the backend endpoint
    fetch("/find_similar_jewelry", { // Ensure this matches your Flask route
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json" // Indicate we expect JSON back
        },
        body: JSON.stringify({ image_url: message }) // Send the URL in JSON format
    })
    .then(response => {
        // Check if the response is successful (status code 200-299)
        if (!response.ok) {
             // Try to parse error JSON from backend for a better message
             return response.json().then(errData => {
                 // Use the error message from backend if present, otherwise use status text
                 throw new Error(errData.error || `Search failed: ${response.statusText} (Status: ${response.status})`);
             }).catch(() => {
                 // If response is not JSON or parsing fails, throw generic HTTP error
                 throw new Error(`Search failed: ${response.statusText} (Status: ${response.status})`);
             });
        }
        // If response is OK, parse the JSON body
        return response.json();
    })
    .then(data => {
        removeThinkingPlaceholder(); // Remove "..." before showing results or errors

        // Process the received data
        if (data.error) {
             // Handle logical errors reported by the backend (e.g., "Could not analyze image")
             handleFetchError(new Error(data.error));
        } else if (data.data !== undefined && data.total_found !== undefined) { // Check for expected data fields
             handleJewelryData(data); // Display results
        } else {
            // Handle cases where response is 2xx but data is missing/malformed
             console.error("Received unexpected data structure:", data);
             handleFetchError(new Error("Received an unexpected response from the server."));
        }
    })
    .catch(error => {
        // Catch network errors or errors thrown in .then() blocks
        removeThinkingPlaceholder(); // Ensure placeholder is removed on error
        handleFetchError(error);
    });
}

/**
* Removes the last bot message if it's the "Thinking..." placeholder.
*/
function removeThinkingPlaceholder() {
    const chatMessages = document.getElementById("chatMessages");
    if (chatMessages) {
        const lastMessage = chatMessages.querySelector('.message.bot-message:last-child');
        if (lastMessage) {
            const lastBubble = lastMessage.querySelector('.bubble');
            // Check if the last bot message contains only "..."
            if (lastBubble && lastBubble.textContent.trim() === '...') {
                lastMessage.remove();
            }
        }
    }
}


/**
 * Common function to handle and display fetch or application errors in the chat.
 */
 function handleFetchError(error) {
    console.error("Error during fetch or processing:", error);

    // Remove the "..." placeholder message if it exists, as the operation failed
    removeThinkingPlaceholder(); // Call this just in case

    // Display a user-friendly error message in the chat
    // Avoid showing overly technical details like stack traces directly to the user
    let displayMessage = "Sorry, I encountered an error. Please try again.";
    if (error && error.message) {
        // Sanitize message slightly - could be more robust
        const sanitizedMessage = error.message.replace(/</g, '<').replace(/>/g, '>');
        // Be selective about which error messages are user-friendly
        if (error.message.startsWith("Search failed:") || error.message.startsWith("Could not")) {
             displayMessage = `Sorry, an error occurred: ${sanitizedMessage}`;
        } else {
             displayMessage = `Sorry, something went wrong. Please try again later.`; // More generic
        }
    }

    addMessage(displayMessage, false);
    updateSearchResultsBar("Search failed."); // Update the status bar
 }