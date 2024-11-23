document.addEventListener("DOMContentLoaded", function () {
    const sendBtn = document.getElementById("send-btn");
    const userInput = document.getElementById("user-input");
    const chatContent = document.getElementById("chat-content");
    const imageInput = document.getElementById("image-input");
    const thumbnailPreview = document.getElementById("thumbnail-preview");
    const imageUploadBtn = document.getElementById("image-upload-btn");
    const recordBtn = document.getElementById("record-btn");

    let selectedImageFile = null; // Store selected image file
    let isRecording = false; // Keep track of recording state
    let mediaRecorder;
    let audioChunks = [];

    // Add a message to the chat window
    function addMessage(content, sender, isImage = false) {
        const message = document.createElement("div");
        message.className = `message ${sender.toLowerCase()}`;
    
        if (isImage) {
            // For user image messages
            message.innerHTML = `
                <div class="label"><strong>${sender}:</strong></div>
                <div>
                    <img src="${content.imageSrc}" alt="Uploaded Image" class="chat-image">
                    <p>${content.text || ""}</p>
                </div>
            `;
        } else {
            // For text-only messages
            message.innerHTML = `<p><strong>${sender}:</strong> ${content}</p>`;
        }
    
        chatContent.appendChild(message);
        chatContent.scrollTop = chatContent.scrollHeight;
    }

    // Sending Text Messages Only to `/query`
    async function sendTextMessage(textMessage) {
        addMessage(textMessage, "User"); // Show user message in chat
        try {
            const response = await fetch("/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: textMessage }),
            });
            const data = await response.json();
            addMessage(data.response || "No response from the server.", "Bot");
        } catch (error) {
            addMessage("Error connecting to server.", "Bot");
        }
    }

    // Function to send image and text to `/vision_query`
    async function sendImageWithText(textMessage, imageFile) {
        addMessage(
            { imageSrc: URL.createObjectURL(imageFile), text: textMessage },
            "User",
            true
        );
        const formData = new FormData();
        formData.append("image", imageFile);
        formData.append("text", textMessage);

        try {
            const response = await fetch("/vision_query", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();
            addMessage(data.response || "No response from the server.", "Bot");
        } catch (error) {
            addMessage("Error connecting to server.", "Bot");
        }
    }

    // Handle send button click
    function handleSend() {
        const textMessage = userInput.value.trim();

        // If an image is selected, send to `/vision_query`
        if (selectedImageFile) {
            if (!textMessage) {
                alert("Please provide a description for the image.");
                return;
            }
            sendImageWithText(textMessage, selectedImageFile);
        } else {
            // No image: send text to `/query`
            if (!textMessage) {
                alert("Please type a message.");
                return;
            }
            sendTextMessage(textMessage);
        }

        // Reset inputs and hide thumbnail after sending
        userInput.value = "";
        selectedImageFile = null;
        thumbnailPreview.style.display = "none"; // Hide the thumbnail preview
        thumbnailPreview.innerHTML = ""; // Clear the thumbnail content
    }

    // Add event listener to send button
    sendBtn.addEventListener("click", handleSend);

    // Allow "Enter" key to trigger send button
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault(); // Prevent newline
            handleSend(); // Call send function
        }
    });

    // Open the file selector
    imageUploadBtn.addEventListener("click", () => {
        imageInput.click();
    });

    // Preview selected image
    imageInput.addEventListener("change", () => {
        const imageFile = imageInput.files[0];
        if (!imageFile) return;

        selectedImageFile = imageFile;

        // Clear previous content
        thumbnailPreview.innerHTML = "";

        // Add image preview
        const img = document.createElement("img");
        img.src = URL.createObjectURL(imageFile);
        thumbnailPreview.appendChild(img);

        // Add cancel button
        const cancelButton = document.createElement("button");
        cancelButton.className = "cancel-btn";
        cancelButton.innerHTML = "×";
        cancelButton.addEventListener("click", () => {
            selectedImageFile = null;
            thumbnailPreview.style.display = "none";
            thumbnailPreview.innerHTML = ""; // Clear the thumbnail preview
            imageInput.value = ""; // Reset the file input
        });
        thumbnailPreview.appendChild(cancelButton);

        thumbnailPreview.style.display = "flex"; // Show the preview
    });

// Event listener for the record button
recordBtn.addEventListener("click", async () => {
    const recordIcon = recordBtn.querySelector("i");
    if (!isRecording) {
        try {
            console.log("Starting recording...");
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start();
            audioChunks = []; // Clear previous audio chunks

            // Collect audio data
            mediaRecorder.addEventListener("dataavailable", (event) => {
                audioChunks.push(event.data);
            });

            // Handle stop recording and send to server
            mediaRecorder.addEventListener("stop", async () => {
                const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
                await sendAudioToServer(audioBlob); // Send the audio blob for processing
            });

            // Update recording state and UI
            recordIcon.classList.replace("fa-microphone", "fa-stop");
            isRecording = true;
        } catch (error) {
            console.error("Error starting recording:", error);
            alert("Could not start recording. Check your microphone permissions.");
        }
    } else {
        mediaRecorder.stop(); // Stop recording
        recordIcon.classList.replace("fa-stop", "fa-microphone");
        isRecording = false;
    }
});

// Function to send audio blob to the server and handle responses
async function sendAudioToServer(audioBlob) {
    const formData = new FormData();
    formData.append("audio", audioBlob);

    try {
        const response = await fetch("/voice_to_text", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();

        if (data.text) {
            // Fetch the bot's response using the transcribed text
            await sendTextMessage(data.text);
        } else {
            addMessage("Sorry, I couldn't process the audio.", "Bot");
        }
    } catch (error) {
        console.error("Error during voice-to-text processing:", error);
        addMessage("Error processing audio recording.", "Bot");
    }
}

});
