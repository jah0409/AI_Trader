from flask import Flask, request, jsonify
import base64
import anthropic
import os
import json
import re
import time
import requests as http_req

app = Flask(__name__)

SUPABASE_URL    = os.environ.get("SUPABASE_URL",         "https://qbzbbrfooscngonzpzmz.supabase.co")
SUPABASE_SVC    = os.environ.get("SUPABASE_SERVICE_KEY", "")
WALLET_BEP20    = "0x38621289ac44502529758704689a5a1afa4e9fd0"
WALLET_TRC20    = "TC8aiK8V1wteKL9yN8BgPw6s2Pnb26MKGU"
WALLET_ADDRESS  = WALLET_BEP20  # kept for backward compatibility
ADMIN_EMAIL     = "mohammadjaved0409@gmail.com"
SESSION_MS      = 24 * 60 * 60 * 1000   # 24 h in ms

NETWORKS = {
    "bep20": {
        "label":   "BEP-20 (Binance Smart Chain)",
        "address": WALLET_BEP20,
        "hint":    "EVM-style address starting with 0x, BSC explorer (bscscan)",
    },
    "trc20": {
        "label":   "TRC-20 (Tron)",
        "address": WALLET_TRC20,
        "hint":    "Tron address starting with T, Tron explorer (tronscan)",
    },
}

SYSTEM_PROMPT = (
    "You are an elite Forex and Stock trader with 20 years of experience. "
    "When given a chart image, analyze it: identify the trend, support/resistance levels, "
    "and candlestick patterns. Give a clear recommendation (BUY/SELL/HOLD) and a brief reason. "
    "After your analysis, always end with: 'Are you confused about anything? Feel free to ask me!' "
    "When the user asks follow-up questions, answer them clearly and professionally, "
    "drawing on the chart context you already analyzed. "
    "When given a new chart mid-conversation, analyze it fully and reference the previous discussion if relevant."
)


def claude():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set.")
    return anthropic.Anthropic(api_key=key)


def sb_hdrs():
    return {
        "apikey":        SUPABASE_SVC,
        "Authorization": f"Bearer {SUPABASE_SVC}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """Extract first JSON object from Claude's response."""
    raw = raw.strip()
    match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}


# ── 1. Chart analysis ─────────────────────────────────────────────────────────

@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        file = request.files.get("image")
        if not file:
            return jsonify({"error": "No image uploaded."}), 400

        img_b64   = base64.b64encode(file.read()).decode()
        media_typ = file.content_type or "image/png"

        msg = claude().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_typ, "data": img_b64}},
                    {"type": "text",  "text":   "Please analyze this chart and give me your trading recommendation."},
                ],
            }],
        )
        return jsonify({"response": msg.content[0].text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 2. Follow-up chat ─────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body."}), 400

        history    = data.get("history", [])
        question   = data.get("question", "").strip()
        image_data = data.get("image_data")
        image_type = data.get("image_type", "image/png")

        if not question and not image_data:
            return jsonify({"error": "No question or image."}), 400

        if image_data:
            user_content = [
                {"type": "image", "source": {"type": "base64", "media_type": image_type, "data": image_data}},
                {"type": "text",  "text": question or "Here is a new chart. Analyze it and reference our previous conversation."},
            ]
        else:
            user_content = question

        history.append({"role": "user", "content": user_content})

        msg = claude().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        return jsonify({"response": msg.content[0].text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 3. Payment screenshot validation ─────────────────────────────────────────

@app.route("/api/validate-payment", methods=["POST"])
def validate_payment():
    try:
        data = request.get_json() or {}
        img_data   = data.get("image_data", "")
        img_type   = data.get("image_type", "image/png")
        user_email = data.get("email", "").strip().lower()
        network    = (data.get("network") or "bep20").strip().lower()

        if not img_data:
            return jsonify({"valid": False, "reason": "No screenshot provided."}), 400

        net_cfg = NETWORKS.get(network, NETWORKS["bep20"])
        expected_address = net_cfg["address"]
        net_label        = net_cfg["label"]
        net_hint         = net_cfg["hint"]

        # Accept the *other* network as a "wrong chain" failure rather than silent
        other_addresses = [v["address"] for k, v in NETWORKS.items() if k != network]

        prompt = f"""You are a strict payment fraud-detection system for a trading platform.

The user claims they sent USDT on the {net_label} network. The expected recipient wallet for this network is:
{expected_address}
({net_hint})

Carefully examine the screenshot and verify ALL of the following:
1. Is this a real cryptocurrency wallet/exchange transaction screen (Binance, Trust Wallet, MetaMask, TronLink, OKX, Bybit, Bitget, Coinbase, etc.)?
2. Is the transaction status COMPLETED, SUCCESSFUL, or CONFIRMED? (not pending, not failed, not rejected)
3. Is the recipient wallet address exactly or partially matching: {expected_address} ?
   (If instead it matches one of these other-chain addresses, the user sent on the WRONG network and you must reject: {', '.join(other_addresses)})
4. Is the token USDT (Tether)?
5. Is the amount at least 5 USDT?
6. Is the network on the screenshot {net_label}? (If the screenshot clearly shows a different chain, reject.)

If ANY check fails → valid = false. Be especially strict about the wallet address — partial match is OK but it must clearly be the same address.

Respond ONLY with a raw JSON object (no markdown, no extra text):
{{"valid": true, "reason": "USDT transfer on {net_label} confirmed to correct wallet"}}
or
{{"valid": false, "reason": "exact reason it failed"}}"""

        msg = claude().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": img_type, "data": img_data}},
                    {"type": "text",  "text": prompt},
                ],
            }],
        )

        result = _parse_json(msg.content[0].text)
        if not result:
            result = {"valid": False, "reason": "Could not read the screenshot. Please upload a clear transaction confirmation."}

        if result.get("valid"):
            expires_at = int(time.time() * 1000) + SESSION_MS
            result["expires_at"] = expires_at

            # Record in Supabase
            if SUPABASE_SVC and user_email:
                try:
                    http_req.post(
                        f"{SUPABASE_URL}/rest/v1/payment_history",
                        headers=sb_hdrs(),
                        json={
                            "user_email":         user_email,
                            "screenshot_verdict": "approved",
                            "verdict_reason":     result.get("reason", ""),
                            "status":             "active",
                            "amount":             f"$5 USDT · {net_label}",
                            "expires_at":         expires_at,
                        },
                        timeout=6,
                    )
                except Exception:
                    pass  # don't block unlock if DB write fails

        return jsonify(result)

    except Exception as e:
        return jsonify({"valid": False, "reason": f"Server error: {str(e)}"}), 500


# ── 4. Check if user has active paid session ──────────────────────────────────

@app.route("/api/check-access", methods=["POST"])
def check_access():
    try:
        data  = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        if not email:
            return jsonify({"hasAccess": False}), 400

        # Admin always has unlimited access
        if email == ADMIN_EMAIL.lower():
            return jsonify({"hasAccess": True, "isAdmin": True, "expiresAt": None})

        if not SUPABASE_SVC:
            return jsonify({"hasAccess": False})

        now = int(time.time() * 1000)
        resp = http_req.get(
            f"{SUPABASE_URL}/rest/v1/payment_history",
            headers=sb_hdrs(),
            params={
                "user_email": f"eq.{email}",
                "status":     "eq.active",
                "expires_at": f"gt.{now}",
                "order":      "expires_at.desc",
                "limit":      1,
            },
            timeout=6,
        )
        records = resp.json()
        if isinstance(records, list) and records:
            return jsonify({"hasAccess": True, "isAdmin": False, "expiresAt": records[0]["expires_at"]})

        return jsonify({"hasAccess": False, "isAdmin": False})

    except Exception as e:
        return jsonify({"hasAccess": False, "error": str(e)}), 500


# ── 5. Admin — full payment history ──────────────────────────────────────────

@app.route("/api/admin/payments", methods=["GET"])
def admin_payments():
    try:
        caller = request.headers.get("X-Admin-Email", "").strip().lower()
        if caller != ADMIN_EMAIL.lower():
            return jsonify({"error": "Unauthorized"}), 403

        if not SUPABASE_SVC:
            return jsonify({"error": "DB not configured"}), 500

        resp = http_req.get(
            f"{SUPABASE_URL}/rest/v1/payment_history",
            headers=sb_hdrs(),
            params={"order": "created_at.desc", "limit": 200},
            timeout=8,
        )
        return jsonify(resp.json())

    except Exception as e:
        return jsonify({"error": str(e)}), 500
