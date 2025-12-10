from fastapi import FastAPI, Request, Header
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import base64
import re
from groq import Groq
import os
import requests
import json
from datetime import datetime

load_dotenv()

app = FastAPI()


# Config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
TOKEN_FILE = "token.json"

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # Dynamic from env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ========== PYDANTIC MODELS ==========
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str

class DeleteRequest(BaseModel):
    email_id: str


# Helpers
def save_token(data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f)

def load_token():
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except:
        return None

def get_access_token():
    token_data = load_token()
    if not token_data:
        return None
    return token_data.get('access_token')

# AUTH ENDPOINTS
@app.get("/auth/google/login")
def google_login():
    scope = (
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/gmail.modify "
        "https://www.googleapis.com/auth/gmail.labels "
        "openid email profile"
    )
    redirect_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return RedirectResponse(redirect_url)

@app.get("/auth/google/callback")
def google_callback(code: str = None):
    if not code:
        return RedirectResponse(f"{FRONTEND_URL}?error=no_code")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        response = requests.post(token_url, data=data)
        token_data = response.json()

        if "error" in token_data:
            return RedirectResponse(f"{FRONTEND_URL}?error={token_data['error']}")

        save_token(token_data)
        access_token = token_data.get('access_token')
        return RedirectResponse(f"{FRONTEND_URL}?token={access_token}")
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}?error=callback_failed")

# USER PROFILE
@app.get("/me")
def get_user_profile(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    token = authorization.replace("Bearer ", "")

    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers=headers
        )
        user_data = response.json()
        return {
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "picture": user_data.get("picture")
        }
    except:
        return JSONResponse({"error": "Failed to fetch profile"}, status_code=400)

# EMAIL OPERATIONS
@app.get("/read-emails")
def read_emails(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    token = authorization.replace("Bearer ", "")

    try:
        headers = {"Authorization": f"Bearer {token}"}

        # Get last 5 emails
        response = requests.get(
            "https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=5",
            headers=headers
        )
        messages = response.json().get("messages", [])

        emails = []
        for msg in messages:
            msg_id = msg["id"]
            msg_res = requests.get(
                f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers
            )
            msg_data = msg_res.json()

            headers_list = msg_data["payload"].get("headers", [])
            email_obj = {
                "id": msg_id,
                "sender": next((h["value"] for h in headers_list if h["name"] == "From"), "Unknown"),
                "subject": next((h["value"] for h in headers_list if h["name"] == "Subject"), "(No Subject)"),
                "snippet": msg_data.get("snippet", "")[:100]
            }
            emails.append(email_obj)

        return {"emails": emails}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ========== AI CLIENT ==========
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize_email(subject, body):
    """Use Groq to summarize email in 2-3 sentences"""
    try:
        message = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize this email in 2-3 sentences:\n\nSubject: {subject}\n\nBody: {body}"
                }
            ]
        )
        return message.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def generate_reply(subject, sender, body):
    """Use Groq to generate professional reply"""
    try:
        message = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"Write a professional, polite reply email to this message. Keep it concise (under 100 words):\n\nFrom: {sender}\nSubject: {subject}\n\nMessage:\n{body}\n\nReply:"
                }
            ]
        )
        return message.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ========== SUMMARIZE ENDPOINT ==========
@app.post("/summarize-email")
def summarize_email_endpoint(
        email_id: str,
        authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    token = authorization.replace("Bearer ", "")

    try:
        headers = {"Authorization": f"Bearer {token}"}

        # Get email
        response = requests.get(
            f"https://www.googleapis.com/gmail/v1/users/me/messages/{email_id}",
            headers=headers
        )
        msg_data = response.json()

        # Extract subject and body
        headers_list = msg_data["payload"].get("headers", [])
        subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "(No Subject)")

        # Get body
        if "parts" in msg_data["payload"]:
            body = msg_data["payload"]["parts"][0].get("body", {}).get("data", "")
        else:
            body = msg_data["payload"].get("body", {}).get("data", "")

        if body:
            body = base64.urlsafe_b64decode(body).decode("utf-8")

        summary = summarize_email(subject, body[:500])  # Limit body to 500 chars

        return {"summary": summary}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# ========== GENERATE REPLY ENDPOINT ==========
@app.post("/generate-reply")
def generate_reply_endpoint(
        email_id: str,
        authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    token = authorization.replace("Bearer ", "")

    try:
        headers = {"Authorization": f"Bearer {token}"}

        # Get email
        response = requests.get(
            f"https://www.googleapis.com/gmail/v1/users/me/messages/{email_id}",
            headers=headers
        )
        msg_data = response.json()

        # Extract info
        headers_list = msg_data["payload"].get("headers", [])
        subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "(No Subject)")
        sender = next((h["value"] for h in headers_list if h["name"] == "From"), "Unknown")

        # Get body
        if "parts" in msg_data["payload"]:
            body = msg_data["payload"]["parts"][0].get("body", {}).get("data", "")
        else:
            body = msg_data["payload"].get("body", {}).get("data", "")

        if body:
            body = base64.urlsafe_b64decode(body).decode("utf-8")

        reply = generate_reply(subject, sender, body[:500])

        return {"reply": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# ========== SEND EMAIL ENDPOINT ==========
@app.post("/send-email")
@app.post("/send-email")
def send_email_endpoint(
        request: EmailRequest,
        authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    token = authorization.replace("Bearer ", "")

    try:
        headers = {"Authorization": f"Bearer {token}"}

        # Create email message
        message = f"From: me\nTo: {request.to}\nSubject: {request.subject}\n\n{request.body}"
        raw_message = base64.urlsafe_b64encode(message.encode("utf-8")).decode("utf-8")

        # Send email
        response = requests.post(
            "https://www.googleapis.com/gmail/v1/users/me/messages/send",
            headers=headers,
            json={"raw": raw_message}
        )

        if response.status_code == 200:
            return {"success": True, "message": "Email sent!"}
        else:
            return JSONResponse({"error": response.text}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ========== DELETE EMAIL ENDPOINT ==========
@app.post("/delete-email")
@app.post("/delete-email")
def delete_email_endpoint(
        request: DeleteRequest,
        authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    token = authorization.replace("Bearer ", "")

    try:
        headers = {"Authorization": f"Bearer {token}"}

        # Delete email
        response = requests.delete(
            f"https://www.googleapis.com/gmail/v1/users/me/messages/{request.email_id}",
            headers=headers
        )

        if response.status_code == 204:
            return {"success": True, "message": "Email deleted!"}
        else:
            return JSONResponse({"error": response.text}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# HEALTH CHECK
@app.get("/")
def root():
    return {"status": "ok", "service": "Gmail AI Assistant"}
