# Trinethra Deployment Guide 🚀

This guide explains how to deploy the **Trinethra Supervisor Feedback Analyzer** to the web.

## Option 1: Render.com (Recommended & Free)

Render is the easiest way to host this project.

### Step 1: Prepare your Repo
1. Push your code to **GitHub**.
2. Make sure `backend/requirements.txt` is updated.

### Step 2: Deploy Backend
1. Go to [Render.com](https://render.com) and create a **Web Service**.
2. Connect your GitHub repository.
3. Use the following settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add **Environment Variables**:
   - `OLLAMA_URL`: URL of your hosted LLM (e.g., from Groq or OpenRouter if not using local Ollama).
   - `DATABASE_URL`: (Optional) For persistent DB beyond SQLite.

### Step 3: Deploy Frontend
1. Create a **Static Site** on Render.
2. Select the same repo.
3. Use these settings:
   - **Build Command**: (Leave empty)
   - **Publish Directory**: `frontend`
4. Update `frontend/script.js`:
   - Change `const API_BASE_URL = "http://localhost:8005"` to your Render Backend URL.

---

## Option 2: Docker Deployment

If you have a VPS (DigitalOcean, AWS), use Docker:

```bash
# Build the project
docker build -t trinethra-ai .

# Run it
docker run -p 8005:8005 trinethra-ai
```

---

## Option 3: Local "Real World" Run
Just run the master script:
```bash
python run.py
```
This handles cleanup, installations, and launches everything in one go.
