import mss
import base64
import anthropic
import time
import os

# --- CONFIGURATION ---
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set. Run: export ANTHROPIC_API_KEY='your-key-here'")

# Set your screen coordinates (Top, Left, Width, Height)
SCREEN_REGION = {"top": 200, "left": 200, "width": 800, "height": 600}

# Initialize the Claude Client
client = anthropic.Anthropic(api_key=API_KEY)

# Keep conversation history so Claude remembers context
conversation_history = []

SYSTEM_PROMPT = (
    "You are an elite Forex and Stock trader with 20 years of experience. "
    "When given a chart image, analyze it: identify the trend, support/resistance levels, "
    "and candlestick patterns. Give a clear recommendation (BUY/SELL/HOLD) and a brief reason. "
    "After your analysis, always end with: 'Are you confused about anything? Feel free to ask me!' "
    "When the user asks follow-up questions, answer them clearly and professionally, "
    "drawing on the chart context you already analyzed."
)


def capture_screen():
    """Takes a screenshot of the defined region."""
    with mss.mss() as sct:
        screenshot = sct.grab(SCREEN_REGION)
        img_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
        return img_bytes


def analyze_chart(image_bytes):
    """Sends the chart screenshot to Claude for analysis. Starts a fresh turn."""
    global conversation_history

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    # New chart analysis — add it as a user message with the image
    conversation_history.append({
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64_image,
                },
            },
            {
                "type": "text",
                "text": "Please analyze this chart and give me your trading recommendation."
            }
        ]
    })

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=conversation_history,
    )

    reply = message.content[0].text

    # Store Claude's reply so follow-up questions have context
    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    return reply


def ask_followup(user_question):
    """Sends the user's follow-up question to Claude using the existing conversation."""
    global conversation_history

    conversation_history.append({
        "role": "user",
        "content": user_question
    })

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=conversation_history,
    )

    reply = message.content[0].text

    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    return reply


def chat_session():
    """After each chart analysis, let the user ask follow-up questions."""
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
        except EOFError:
            break

        if not user_input:
            print("\n[Resuming chart monitoring in 10 seconds...]\n")
            break

        print("\n🤖 Mentor: Thinking...\n")
        try:
            answer = ask_followup(user_input)
            print(f"🤖 Mentor: {answer}")
            print("-" * 40)
        except Exception as e:
            print(f"[Error getting response] {e}")


# --- MAIN LOOP ---
print("=" * 50)
print("   ELITE TRADER AI MENTOR — STARTED")
print(f"   Monitoring region: {SCREEN_REGION}")
print("   Press Ctrl+C to stop.")
print("=" * 50)

try:
    while True:
        print("\n📊 [AI] Capturing chart and analyzing...")

        try:
            # 1. Capture screen
            img = capture_screen()

            # 2. Send to Claude for chart analysis
            advice = analyze_chart(img)

            # 3. Print the analysis
            print("\n" + "=" * 40)
            print("🤖 ELITE TRADER MENTOR SAYS:")
            print("=" * 40)
            print(advice)
            print("=" * 40)

            # 4. Open Q&A — user can ask anything or press Enter to skip
            print("\n(Type your question and press Enter, or just press Enter to skip)")
            chat_session()

        except Exception as e:
            print(f"[Error] {e}")

        print("[Next chart scan in 10 seconds...]")
        time.sleep(10)

except KeyboardInterrupt:
    print("\n\nBot stopped. Good trading! 📈")
