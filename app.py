from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from dotenv import load_dotenv
from groq import Groq
import json
import subprocess

# Load environment variables from .env file
load_dotenv()

# Flask app setup
app = Flask(__name__)

# Set the API keys from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Check if API keys are set
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the .env file")
if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN is not set in the .env file")

# Create the Groq client
client = Groq(api_key=GROQ_API_KEY)

# Create a state variable to track the conversation context
conversation_context = {}

# Route for serving the chatbot UI
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint to handle chat messages
@app.route('/chat', methods=['POST'])
def chat():
    global conversation_context
    try:
        # Get the user message
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'response': 'Please provide a valid input.'})

        # Initialize or reset the conversation context on greeting
        if "history" not in conversation_context or user_message.lower() in ["hi", "hello", "hey"]:
            conversation_context = {"history": []}  # Reset the context
            greeting_response = "Hi there! 👋 I'm Scoutie, your friendly AI assistant here to help you connect with TikTok influencers. How can I assist you today?"
            conversation_context["history"].append({"role": "assistant", "content": greeting_response})
            return jsonify({'response': greeting_response})

        # Append the user's message to the conversation history
        conversation_context["history"].append({"role": "user", "content": user_message})

        # Prepare messages for the API call, including a system prompt
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Scoutie, an AI assistant that helps users connect with TikTok influencers. "
                    "Engage in a friendly and professional conversation. "
                    "Subtly ask one question at a time to understand the user's needs and customer persona. "
                    "Provide meaningful and detailed responses, but limit your responses to a maximum of 4 to 5 sentences. "
                    "Do not ask all questions at once; instead, gradually guide the conversation based on the user's responses. "
                    "Make the conversations natural and engaging. "
                    "You only find influencers on TikTok, so subtly guide the client towards TikTok. "
                    "If the client says they want something else, politely mention that it's a beta product. "
                    "If you don't understand the user's input, politely ask for clarification. "
                    "If you don't know the answer to any question, be polite and tell the client."
                )
            }
        ] + conversation_context["history"]

        # Call the Groq API to get the assistant's response
        groq_response = client.chat.completions.create(
            model='llama3-8b-8192',
            messages=messages
        )

        # Extract the assistant's reply
        assistant_reply = groq_response.choices[0].message.content.strip()

        # Append the assistant's reply to the conversation history
        conversation_context["history"].append({"role": "assistant", "content": assistant_reply})

        # Check if the conversation has reached its end
        if user_message.lower() in ["no, that's all", "no", "that's all", "thanks", "thank you"]:
            # Generate the final summary
            final_summary = generate_summary(conversation_context["history"])
            # Save the summary to a file
            with open("summary.json", "w") as f:
                json.dump({"prompt": final_summary}, f)

            # Redirect to the summary page
            return jsonify({'response': assistant_reply, 'redirect': url_for('summary')})

        # Return the assistant's response
        return jsonify({'response': assistant_reply})

    except Exception as e:
        # Handle errors gracefully
        return jsonify({'response': f"An error occurred: {str(e)}"})

def generate_summary(conversation_history):
    # Extract relevant information from the conversation history
    user_inputs = [entry["content"] for entry in conversation_history if entry["role"] == "user"]
    summary = " ".join(user_inputs)
    return summary

# Route to display the summary and start processing
@app.route('/summary')
def summary():
    # Read the summary from the file
    with open("summary.json", "r") as f:
        data = json.load(f)
    prompt = data.get("prompt", "")

    # You can initiate the processing here or display the summary
    return render_template('summary.html', prompt=prompt)

# Add this import at the top
from flask import send_file

# Add this route in app.py
@app.route('/process', methods=['POST'])
def process():
    try:
        # Call the processing script
        subprocess.call(['python', 'process_summary.py'])

        # After processing, you can serve the CSV file or inform the user
        message = "Processing complete. The influencer data has been saved."

        return jsonify({'message': message})
    except Exception as e:
        return jsonify({'message': f"An error occurred during processing: {str(e)}"})


if __name__ == '__main__':
    app.run(debug=True)
