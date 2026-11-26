# 𝕏 AI Ticket-Matcher Bot (Real-Time Autonomous Edition)

A 100% real-time, production-clean full-stack application that connects to **live X (Twitter)**, searches for secondary market ticket **buyers** and **sellers**, performs **AI anti-fraud verification and compatibility evaluation**, and **automatically publishes replies or standalone tweets to X without requiring manual approval**.

---

## ⚡ What Changed

1. **Zero Demo Data**:
   - All mock data generation (`demo_data.py`, simulated fallback records, mock tweet IDs) has been completely removed.
   - The SQLite database now exclusively contains real live events, live tweets, and real-time logs.

2. **Real-Time Live X API Connection**:
   - Uses Tweepy v2 to directly query live X search endpoints for ticket buyers and sellers.
   - Live posting support: Attempts direct replies to buyer tweets; if X returns a `403 Forbidden` summoned reply policy restriction, it automatically falls back to posting a public standalone match tweet tagging both `@buyer` and `@seller`.

3. **Autonomous Background Engine (No Approval Needed)**:
   - Continuously sweeps X for active monitored keywords on a configurable interval (30s, 60s, 2m, 5m).
   - Instant AI evaluation of buyer-seller pairs.
   - **Autonomous Auto-Posting**: When confidence &ge; threshold (default 70%), the bot directly dispatches the reply tweet to live X immediately.
   - Anti-duplication guarantee: Unique database constraints prevent re-evaluating or duplicate posting identical tweet pairs.

4. **Live Activity Stream & In-App Key Management**:
   - Real-time terminal log in the UI displaying live sweeps, discovered tweets, AI scores, and posted tweet IDs.
   - In-app **Settings / Keys** modal to view and update X API keys (`TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`, `TWITTER_BEARER_TOKEN`) and `AI_API_KEY` live without restarting the server.

---

## 🚀 Running the App

### Backend (Port 8000)
```powershell
cd backend
.\venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000
```
Swagger UI: [`http://localhost:8000/docs`](http://localhost:8000/docs)

### Frontend (Port 3000)
```powershell
cd frontend
npm run start -- -p 3000
```
Dashboard: [`http://localhost:3000`](http://localhost:3000)

---

## ☁️ Cloud Deployment Guide (Render + Vercel + UptimeRobot)

### 1. Deploy Frontend on Vercel
1. Import the repository into [Vercel](https://vercel.com).
2. Set the **Root Directory** to `frontend`.
3. Add the following Environment Variable in Vercel:
   ```env
   NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
   ```
4. Deploy! Your dashboard will be live at `https://your-app.vercel.app`.

### 2. Deploy Backend on Render
1. Create a new **Web Service** on [Render](https://render.com) pointing to your repo.
2. Configure settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add Environment Variables in Render:
   ```env
   BACKEND_URL=https://your-backend.onrender.com
   FRONTEND_URL=https://your-frontend.vercel.app
   CORS_ORIGIN=https://your-frontend.vercel.app
   AUTO_SCAN_ENABLED=true
   AUTO_SCAN_INTERVAL_SECONDS=1500
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-1.5-flash
   DEFAULT_SELLER_USERNAME=your_x_handle
   ```

### 3. Keep Backend Awake 24/7 with UptimeRobot
Render free-tier instances sleep after 15 minutes of inactivity. To keep your 25-minute autonomous ticket scanner running non-stop 24/7 without sleeping:
1. Go to [UptimeRobot.com](https://uptimerobot.com) (free account).
2. Click **+ Add New Monitor**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `X Ticket Matcher Keepalive`
   - **URL / IP**: `https://your-backend.onrender.com/health`
   - **Monitoring Interval**: `5 minutes`
3. Click **Create Monitor**. UptimeRobot will ping `/health` every 5 minutes, keeping Render warm and returning HTTP 200 with live uptime stats!
