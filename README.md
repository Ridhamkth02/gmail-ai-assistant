# Gmail AI Assistant

A full‑stack web application that connects to Gmail and uses AI (Groq LLaMA 3.3) to help read, summarize, reply to, send, and delete emails via a chatbot‑style interface.

**Built as part of the technical assignment for Constructure AI.**

## Live Demo

- **Frontend (React, Vercel):** https://gmail-ai-assistant-eight.vercel.app/
- **Backend (FastAPI, Railway):** https://gmail-ai-assistant-production.up.railway.app/
- **Repository:** https://github.com/Ridhamkth02/gmail-ai-assistant

---

## Features

- Google OAuth 2.0 login with Gmail permissions to read, send, and delete emails.
- Authenticated session with redirect to chatbot dashboard after login.
- Chatbot dashboard that:
  - Greets the user using Google profile information.
  - Explains available capabilities on first load.
  - Shows a conversation thread of user and assistant messages.
- Email automation:
  - Fetch last 5 emails from inbox.
  - Show sender, subject, and AI‑generated summary (using Groq LLaMA 3.3, not simple truncation).
  - Generate context‑aware, professional reply drafts.
  - Confirm and send replies via Gmail, with success/failure status in chat.
  - Delete a specific email (by reference/index or keyword) with confirmation and result message.
- Deployed with proper CORS between frontend and backend, using environment variables for all secrets.

---

## Tech Stack

- **Frontend:** React.js SPA, deployed on Vercel.
- **Backend:** FastAPI (Python), deployed on Railway.
- **APIs & AI:**
  - Gmail API v1
  - Google OAuth 2.0
  - Groq AI (LLaMA 3.3‑70B) for summaries and reply generation
- **Auth & Security:** Google OAuth 2.0 with restricted Gmail scopes, bearer token between frontend and backend, environment variables for secrets.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js (LTS) and npm
- Google Cloud project with OAuth 2.0 Web Client ID
- Groq API key

### 1. Clone the Repository


git clone https://github.com/Ridhamkth02/gmail-ai-assistant.git
cd gmail-ai-assistant


---

## Backend Setup (FastAPI)

From the `backend` folder:


cd backend
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt


Create a `.env` file in `backend`:


GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GMAIL_API_SCOPES=https://www.googleapis.com/auth/gmail.modify
GROQ_API_KEY=your_groq_api_key
FRONTEND_URL=http://localhost:3000
JWT_SECRET=some_long_random_secret


Run the backend locally:


uvicorn main:app --reload --port 8000


In production (Railway), the same keys are configured as environment variables and `GOOGLE_REDIRECT_URI` / `FRONTEND_URL` point to the Railway and Vercel URLs.

---

## Frontend Setup (React)

From the `frontend` folder:



cd frontend
npm install


Create a `.env` in `frontend`:


REACT_APP_API_URL=http://localhost:8000


Run the frontend:

npm start


Open `http://localhost:3000` and click **Login with Google** to start the flow.

---

## Usage

After successful login, the user is redirected to the chatbot dashboard.

### Core flows

**Read last 5 emails**

- Type a command like “show my last 5 emails”.
- The app fetches 5 most recent inbox emails and displays sender, subject, and AI summary.

**Generate AI replies**

- For listed emails, request AI replies.
- The assistant generates context‑aware, professional reply drafts for each email.

**Send replies**

- Confirm a reply (e.g., “send reply for email 2”).
- The backend sends via Gmail API and the chatbot shows success or failure.

**Delete an email**

- Ask to delete a specific email (e.g., “delete email 3” or based on your implemented UX).
- The app asks for confirmation.
- On confirmation, it deletes through Gmail and reports the result in the conversation.

---

## Deployment

### Backend (Railway)

- Deployed from this GitHub repository with root directory set to `backend`.
- Uses a `Procfile` similar to:

web: uvicorn main:app --host 0.0.0.0 --port $PORT


- All secrets (Google credentials, Groq key, JWT secret, etc.) are configured as Railway environment variables (not committed to Git).

### Frontend (Vercel)

- Imported from this repository with root directory `frontend`.
- Environment variable:



REACT_APP_API_URL = https://gmail-ai-assistant-production.up.railway.app


- CORS on backend allows the Vercel domain `https://gmail-ai-assistant-eight.vercel.app`.

---

## Assumptions & Limitations

- This project is a single‑user demo and does not store long‑term user data in a database.
- Gmail scope used is `gmail.modify` so it can read, send, and delete emails; users must grant this during OAuth consent.
- Subject to limits and quotas of the Gmail API and Groq API.

