from flask import Flask, request, jsonify, render_template
from huggingface_hub import InferenceClient
from deep_translator import GoogleTranslator
import speech_recognition as sr
from dotenv import load_dotenv
import os
import re
import requests
from cloudinary.uploader import upload
import cloudinary
import cloudinary.uploader




app = Flask(__name__)
recognizer = sr.Recognizer()

# Load environment variables
load_dotenv()
huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
weather_api_key = os.getenv("WEATHER_API_KEY")

# Initialize Hugging Face Inference Client
client = InferenceClient(api_key=huggingface_api_token)

# Model names for Hugging Face
LLAMA_MODEL_NAME = "meta-llama/Llama-3.2-11B-Vision-Instruct"

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

def get_weather(location):
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={weather_api_key}&units=metric"
    response = requests.get(weather_url)
    if response.status_code == 200:
        data = response.json()
        temperature = data['main']['temp']
        description = data['weather'][0]['description']
        return f"The current temperature in {location} is {temperature}°C with {description}."
    else:
        return "I'm sorry, I couldn't retrieve the weather information for that location."

def is_weather_query(query):
    weather_keywords = ["weather", "temperature", "forecast", "rain", "humidity", "climate"]
    return any(keyword in query.lower() for keyword in weather_keywords)

#--------------------------------------------start query--------------------------------------
@app.route("/query", methods=["POST"])
def query():
    user_input = request.json.get("message", "")
    target_language = request.json.get("language", "en")  # User's preferred language (default: English)

    # Step 1: Translate user input to English if needed
    try:
        if target_language != "en":
            translated_input = GoogleTranslator(source="auto", target="en").translate(user_input)
        else:
            translated_input = user_input
    except Exception as e:
        return jsonify({"response": f"Error translating input: {str(e)}"})

    # Step 2: Check if the query is weather-related
    try:
        location_match = re.search(r"in (\w+)", translated_input)
        if is_weather_query(translated_input) and location_match:
            location = location_match.group(1)
            weather_info = get_weather(location)

            # Translate weather response back if necessary
            if target_language != "en":
                translated_weather_info = GoogleTranslator(source="en", target=target_language).translate(weather_info)
            else:
                translated_weather_info = weather_info

            return jsonify({"response": translated_weather_info})
    except Exception as e:
        return jsonify({"response": f"Error processing weather query: {str(e)}"})

    # Step 3: Process the query using the chatbot model
    try:
        # messages = [
        #     {"role": "user", "content": [{"type": "text", "text": translated_input}]}
        # ]



        messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an advanced AI assistant specializing in agriculture and farming, tailored specifically for South Africa. Your expertise includes South African markets, provinces, weather patterns, growing seasons, local measuring units, and sustainable agricultural methods. \
                    Your responses must be concise (3-4 sentences), actionable, and directly relevant to the user's query. Avoid unnecessary elaboration or topics unrelated to South African agriculture. \
                    Always reference South African-specific information and data in your answers, such as: \
                    1) South African seasons: Summer (December to February), Autumn (March to May), Winter (June to August), Spring (September to November). \
                    2) Measuring units like kilograms (kg), litres (L), hectares (ha), and the South African Rand (ZAR) as currency. \
                    3) Local farming practices, crop/livestock details, and market trends. \
                    Address key challenges faced by South African farmers, such as droughts, soil erosion, pest outbreaks, and market access. \
                    Your role is to support the following goals: \
                    1) Help South African farmers meet their unique demands by leveraging LLM technology, including providing precise weather forecasts, crop yield optimization, and local market insights. \
                    2) Identify essential features SmartFarmBot must include for sustainable agriculture, such as crop rotation, water management, and soil health monitoring. \
                    3) Empower farmers with localized advice on crop selection, market trends, and financial planning for better outcomes. \
                    If a query is outside your scope, politely inform the user that your expertise is specific to agriculture and farming in South Africa. Use practical examples like government programs, subsidies, or local organizations supporting farmers whenever applicable. \
                    Focus on delivering concise, practical, and actionable advice that aligns with South African agricultural realities."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": translated_input}  # User's input dynamically passed here
            ]
        }
    ]



        stream = client.chat.completions.create(
            model=LLAMA_MODEL_NAME,
            messages=messages,
            max_tokens=500,
            stream=True
        )
        # Collect streamed response
        response_text = "".join(chunk.choices[0].delta.content for chunk in stream)
    except Exception as e:
        return jsonify({"response": f"Error processing chatbot query: {str(e)}"})

    # Step 4: Translate the response back to the user's preferred language
    try:
        if target_language != "en":
            translated_response = GoogleTranslator(source="en", target=target_language).translate(response_text)
        else:
            translated_response = response_text
    except Exception as e:
        return jsonify({"response": f"Error translating response: {str(e)}"})

    return jsonify({"response": translated_response})




#-------------------------------------------vision query--------------------------------------------

@app.route("/vision_query", methods=["POST"])
def vision_query():
    try:


        # Check if an image file is uploaded
        if "image" not in request.files:
            return jsonify({"error": "No image file uploaded"}), 400

        image_file = request.files["image"]
        text_prompt = request.form.get("text", "")
        target_language = request.form.get("language", "en")  # User's preferred language (default: English)

        # Validate inputs
        if not text_prompt:
            return jsonify({"error": "Text prompt is required"}), 400

        # Upload image to Cloudinary
        try:
            upload_result = upload(image_file)
            image_url = upload_result.get("secure_url")
            if not image_url:
                return jsonify({"error": "Failed to upload image to Cloudinary"}), 500
        except Exception as e:
            return jsonify({"error": f"Cloudinary upload failed: {str(e)}"}), 500

        # Step 1: Translate the text prompt to English if necessary
        try:
            if target_language != "en":
                translated_prompt = GoogleTranslator(source="auto", target="en").translate(text_prompt)
            else:
                translated_prompt = text_prompt
        except Exception as e:
            return jsonify({"error": f"Error translating input: {str(e)}"}), 500

        # Prepare messages for the model
        # messages = [
        #     {
        #         "role": "user",
        #         "content": [
        #             {"type": "text", "text": translated_prompt},
        #             {"type": "image_url", "image_url": {"url": image_url}}
        #         ]
        #     }
        # ]


        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You are an advanced AI assistant specializing in agriculture and farming, tailored specifically for South Africa. Your expertise includes South African markets, provinces, weather patterns, growing seasons, local measuring units, and sustainable agricultural methods. \
                        Your responses must be concise (3-4 sentences), actionable, and directly relevant to the user's query. Avoid unnecessary elaboration or topics unrelated to South African agriculture. \
                        Always reference South African-specific information and data in your answers, such as: \
                        1) South African seasons: Summer (December to February), Autumn (March to May), Winter (June to August), Spring (September to November). \
                        2) Measuring units like kilograms (kg), litres (L), hectares (ha), and the South African Rand (ZAR) as currency. \
                        3) Local farming practices, crop/livestock details, and market trends. \
                        Tailor recommendations to address challenges faced by South African farmers, such as droughts, soil erosion, pest outbreaks, and market access. \
                        Your role is to support the following goals: \
                        1) Help South African farmers meet their unique demands by leveraging LLM technology, including providing precise weather forecasts, crop yield optimization, and local market insights. \
                        2) Identify essential features SmartFarmBot must include for sustainable agriculture, such as crop rotation, water management, and soil health monitoring. \
                        3) Empower farmers with localized advice on crop selection, market trends, and financial planning for better outcomes. \
                        If a query includes an image, analyze it in the context of agriculture (e.g., pest identification, crop health) and provide concise, actionable insights. \
                        If a query is outside your scope, politely inform the user that your expertise is specific to agriculture and farming in South Africa. Use practical examples like government programs, subsidies, or local organizations supporting farmers whenever applicable. \
                        Focus on delivering concise, practical, and actionable advice that aligns with South African agricultural realities."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": translated_prompt},  
                    {"type": "image_url", "image_url": {"url": image_url}}  
                ]
            }
        ]



        # Step 2: Use the chat completion API with streaming
        try:
            stream = client.chat.completions.create(
                model=LLAMA_MODEL_NAME,
                messages=messages,
                max_tokens=500,
                stream=True
            )
            # Collect the response
            response_text = "".join(chunk.choices[0].delta.content for chunk in stream)
        except Exception as e:
            return jsonify({"error": f"Error processing vision query: {str(e)}"}), 500

        # Step 3: Translate the response back to the user's preferred language
        try:
            if target_language != "en":
                translated_response = GoogleTranslator(source="en", target=target_language).translate(response_text)
            else:
                translated_response = response_text
        except Exception as e:
            return jsonify({"error": f"Error translating response: {str(e)}"}), 500

        # Return the translated response
        return jsonify({"response": translated_response})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

#----------------------------------------------------- voice to text---------------------------------------------- 
@app.route("/voice_to_text", methods=["POST"])
def voice_to_text():
    audio_file = request.files["audio"]

    # Save uploaded audio to temporary file
    audio_path = "temp_audio_file.wav"
    audio_file.save(audio_path)

    # Convert audio to text using Hugging Face Whisper model API
    with open(audio_path, "rb") as f:
        headers = {"Authorization": f"Bearer {huggingface_api_token}"}
        response = requests.post(
            "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo",
            headers=headers,
            data=f
        )
    os.remove(audio_path)  # Clean up the temporary file

    if response.status_code == 200:
        transcription = response.json().get("text", "Sorry, I couldn't transcribe the audio.")
    else:
        transcription = "Sorry, there was an error with the transcription service."

    return jsonify({"text": transcription})

if __name__ == "__main__":
    app.run()
