from flask import Flask, request, jsonify
import base64
import anthropic
import os

app = Flask(__name__)

SYSTEM_PROMPT = (
    "You are an elite Forex and Stock trader with 20 years of experience. "
    "When given a chart image, analyze it: identify the trend, support/resistance levels, "
    "and candlestick patterns. Give a clear recommendation (BUY/SELL/HOLD) and a brief reason. "
    "After your analysis, always end with: 'Are you confused about anything? Feel free to ask me!' "
    "When the user asks follow-up questions, answer them clearly and professionally, "
    "drawing on the chart context you already analyzed."
)


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in environment variables.")
    return anthropic.Anthropic(api_key=api_key)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        file = request.files.get("image")
        if not file:
            return jsonify({"error": "No image uploaded."}), 400

        image_bytes = file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        media_type = file.content_type if file.content_type else "image/png"

        client = get_client()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Please analyze this chart and give me your trading recommendation.",
                        },
                    ],
                }
            ],
        )

        return jsonify({"response": message.content[0].text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body received."}), 400

        history = data.get("history", [])
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "No question provided."}), 400

        history.append({"role": "user", "content": question})

        client = get_client()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history,
        )

        reply = message.content[0].text
        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
