# chat_interface.py

import streamlit as st
import base64
import requests
import json
import time
import shared


# Importing necessary functions from model_selector.py
from .model_selector import show_model_selector, get_json, show_model_details


base_url = shared['api_endpoint']['url']

# Encodes images to base64 output as list
def images_to_base64(images):
    """Convert a list of image files to base64 encoding."""
    encoded_images = []
    for image_file in images:
        if image_file is not None:
            # Read the file and encode it
            file_bytes = image_file.getvalue()
            base64_encoded = base64.b64encode(file_bytes).decode("utf-8")
            encoded_images.append(base64_encoded)
    return encoded_images

@st.experimental_singleton
def get_models(base_url):
    try:
        response = requests.get(f"{base_url}/api/tags")
        response.raise_for_status()  # This will raise an exception for HTTP errors
        json_data = response.json()
        return [model['name'] for model in json_data.get('models', [])]
    except Exception as e:
        st.error(f"Failed to fetch models: {str(e)}")
        return []

# In the sidebar initialization
if 'model_names' not in st.session_state:
    st.session_state['model_names'] = get_models(base_url)

# Here we create the request for a chat completion at /api/generate
def stream_response(prompt, base_url, model_name, encoded_images=None):
    url = f'{base_url}/api/generate'
    payload = {
        "model": model_name,  # Using the selected model
        "prompt": prompt
    }
    if encoded_images:
        payload["images"] = encoded_images

    headers = {'Content-Type': 'application/json'}

    # Print statement to log the request details
    # Using separators to remove extra whitespaces in the list
    # Uncomment print statements below to show the request sent to Ollama
    # print(f"Requesting URL: {url}")
    # print(f"Headers: {headers}")
    # print(f"Payload: {json.dumps(payload, separators=(',', ':'), indent=4)}")

    with requests.post(url, json=payload, headers=headers, stream=True) as response:
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)
        else:
            print(f"Error: {response.status_code}")
            yield {"response": "Error in generating response"}

def show_chat_interface():
    st.title("Chat Interface")

    # Sidebar dropdown for Chat Options
    with st.sidebar:
        uploaded_images = st.file_uploader("Upload Images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        encoded_images = images_to_base64(uploaded_images)
        selected_model = st.selectbox("Select a Model", st.session_state['model_names'])
        chat_type = st.selectbox("Type of Chat", ["Generate completion", "Start a Conversation"])

    if st.button('Clear Chat History'):
        st.session_state.messages = []

# Display previous messages
for message in st.session_state.get('messages', []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input field
if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    if chat_type == "Generate completion":
        with st.chat_message("assistant"):
            with st.spinner('Processing...'):
                response = stream_response(prompt, base_url, selected_model, encoded_images)
                display_response(response)

def display_response(response_generator):
    full_response = ""
    for response_chunk in response_generator:
        if 'response' in response_chunk:
            assistant_response = response_chunk['response']
            typing_speed = 0.03 if chat_option == "Slow Typing Mode" else 0.008
            for char in assistant_response:
                full_response += char
                time.sleep(typing_speed)
                
    message_placeholder.markdown(full_response + "▌", unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    

# Function to manage and display continuous conversation with spinner
def handle_conversation(messages):
    with st.chat_message("assistant"):
        with st.spinner('Chatting...'):
            conversation_length = continuous_conversation(selected_model, base_url, messages)
            st.success(f"Conversation ended with {conversation_length} exchanges.")

            # Pass the list of encoded images to the stream_response function
            for response_chunk in stream_response(prompt, base_url, selected_model, encoded_images):
                if 'response' in response_chunk:
                    assistant_response = response_chunk['response']
                    typing_speed = 0.03 if chat_option == "Slow Typing Mode" else 0.008
                    for char in assistant_response:
                        full_response += char
                        time.sleep(typing_speed)
                        message_placeholder.markdown(full_response + "▌", unsafe_allow_html=True)

            message_placeholder.markdown(full_response, unsafe_allow_html=True)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
