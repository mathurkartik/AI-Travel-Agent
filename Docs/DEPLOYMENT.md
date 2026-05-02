# Hosting & Deployment Guide

This guide covers how to deploy the AI Travel Planner to the web.

## Option 1: The Easiest Path (PaaS)
This is the recommended approach for most developers. It separates the frontend and backend for better scalability and performance.

### 1. Backend (FastAPI) on Render/Railway
1. **Push your code to GitHub.**
2. Create an account on [Render](https://render.com) or [Railway](https://railway.app).
3. Create a **New Web Service** and connect your GitHub repository.
4. **Root Directory**: `backend`
5. **Build Command**: `pip install -r requirements.txt`
6. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. **Environment Variables**:
   - `GROQ_API_KEY`: Your Groq API key.
   - `CORS_ORIGINS`: Your frontend URL (e.g., `https://ai-travel-planner.vercel.app`) once you have it.

### 2. Frontend (React/Vite) on Vercel/Netlify
1. Create an account on [Vercel](https://vercel.com) or [Netlify](https://netlify.com).
2. Connect your GitHub repository.
3. **Framework Preset**: Vite
4. **Root Directory**: `frontend`
5. **Build Command**: `npm run build`
6. **Output Directory**: `dist`
7. **Environment Variables**:
   - `VITE_API_URL`: Your backend URL (e.g., `https://ai-travel-backend.onrender.com/api`).

---

## Option 2: Docker Deployment (VPS)
If you have a VPS (DigitalOcean, AWS, etc.), you can use Docker.

1. **Install Docker & Docker Compose** on your server.
2. **Clone the repo** to the server.
3. Create a `.env` file in the root with:
   ```env
   GROQ_API_KEY=your_key
   VITE_API_URL=http://your-server-ip:8000/api
   ```
4. **Run**: `docker compose up -d --build`

---

## Post-Deployment Checklist
- [ ] Update `CORS_ORIGINS` in the backend to match your frontend domain.
- [ ] Ensure the `VITE_API_URL` includes the `/api` suffix.
- [ ] Test the "Check Backend Health" button to verify connectivity.
