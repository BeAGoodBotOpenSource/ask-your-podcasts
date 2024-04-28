# from gpt_utils import test
import asyncio
import logging

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, disconnect

from ask_your_podcasts.context import get_context
from ask_your_podcasts.text import TextStreamer
from ask_your_podcasts.voice import VoiceStreamer
from config import debug_status, flowise_uri, whitelist_origins

logger = logging.getLogger(__name__)

if debug_status == "TRUE":
    logging.basicConfig(filename="logs/server.log", level=logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(app)
CORS(app, origins=whitelist_origins)

text_buffer = asyncio.Queue()

# voice_buffer = asyncio.Queue()
text_streamer = TextStreamer(text_buffer=text_buffer)
# voice_streamer = VoiceStreamer(voice_buffer=voice_buffer)


# Just for testing connection with backend; debugging purpose only
@app.route("/test", methods=["GET"])
def hello():
    return "Connected!!"


bot_endpoints = {
    "Lex Fridman": f"{flowise_uri}/api/v1/prediction/cf5c1864-6631-4837-a31b-e1f2614b7397",
    "Newsroom Robots": f"{flowise_uri}/api/v1/prediction/fa601a55-f805-44b5-aba6-b0886b0df978",
}


@app.route("/api-call", methods=["POST"])
def api_call():
    print("arrived")
    data = request.get_json()
    selected_bot = data.get("selectedBot")
    user_question = data.get("question")

    if selected_bot not in bot_endpoints:
        return jsonify({"error": "Invalid bot selected"}), 400
    response = query(bot_endpoints[selected_bot], user_question)
    print(response.json())
    return jsonify(response.json()), 200


def query(api_url, user_question):
    payload = {"question": user_question}
    response = requests.post(api_url, json=payload)
    return response


async def stream_response():
    """Emit responses as they are generated"""
    while True:
        response = await text_buffer.get()
        json_response = jsonify(response)
        socketio.emit("answer_human", json_response)

        if response["position"] == "end":
            disconnect()
            break


@socketio.on("ask_ai")
def ask_ai(data):
    """Add new human message to conversation"""
    human_prompt = data.get("human_prompt")
    logging.debug("human_prompt: %s", human_prompt)

    asyncio.run(text_streamer.stream_text(human_prompt))

    # TODO: disconnect web socket to free up resources once streaming is finished for a question.
    # disconnect()


@socketio.on("connect")
def handle_connect():
    """Set up background tasks on handshake"""
    socketio.start_background_task(stream_response)
    logging.debug("connection made.")


if __name__ == "__main__":
    app.run(debug=True, port=4000)
