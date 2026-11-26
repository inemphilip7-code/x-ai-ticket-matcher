import os
import sys
import time
import requests

# Initialize system certificate store for Windows / macOS / Linux SSL handshakes
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

try:
    import certifi
    if not os.environ.get("SSL_CERT_FILE"):
        os.environ["SSL_CERT_FILE"] = certifi.where()
    if not os.environ.get("REQUESTS_CA_BUNDLE"):
        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
except Exception:
    pass

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, List
from dotenv import load_dotenv, set_key

load_dotenv()

SERVER_START_TIME = time.time()

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from database import (
    init_db, get_matches, get_match_by_id, update_match_status, delete_match,
    get_stats, get_monitored_keywords, add_monitored_keyword, remove_monitored_keyword,
    get_activity_logs, log_activity, get_setting, set_setting
)
from models import (
    ScanRequest, ScanResponse, MatchRecord, ApprovePostRequest, 
    PostResultResponse, SystemStatusResponse, MonitoredKeyword, AddKeywordRequest,
    ActivityLogRecord, ConfigUpdateRequest, AutonomousScannerConfig, SellerUsernameRequest
)
from twitter_service import twitter_service
from matcher import evaluate_pair
from autonomous_scanner import autonomous_scanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    existing_kws = get_monitored_keywords()
    if not existing_kws:
        for default_kw in ["Coldplay", "Oasis 2025", "Taylor Swift"]:
            add_monitored_keyword(default_kw)
            
    log_activity("info", "X AI Ticket-Matcher Realtime Service loaded.")
    autonomous_scanner.start()
    yield
    autonomous_scanner.stop()

app = FastAPI(
    title="X AI Ticket-Matcher Direct Comment Bot",
    description="Real-time X integration with dual OAuth, target seller promotion, and direct comment automation.",
    version="2.2.0",
    lifespan=lifespan
)

# Dynamic CORS configuration for local development + Vercel deployments
cors_origins_env = os.getenv("CORS_ORIGIN", "").strip()
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
if cors_origins_env:
    for o in cors_origins_env.split(","):
        clean_o = o.strip()
        if clean_o and clean_o not in allowed_origins:
            allowed_origins.append(clean_o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Automatically permit any Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_backend_url(request: Request) -> str:
    """
    Returns public base URL of the backend (e.g. https://my-backend.onrender.com).
    Uses BACKEND_URL env var if set, otherwise derives from request headers.
    """
    env_backend = os.getenv("BACKEND_URL", "").strip()
    if env_backend:
        return env_backend.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", f"localhost:{os.getenv('PORT', 8000)}"))
    return f"{proto}://{host}".rstrip("/")

def get_frontend_url(request: Request) -> str:
    """
    Returns public URL of the frontend (e.g. https://my-frontend.vercel.app).
    Uses FRONTEND_URL env var if set, otherwise derives from Referer / CORS_ORIGIN.
    """
    env_frontend = os.getenv("FRONTEND_URL", "").strip()
    if env_frontend:
        return env_frontend.rstrip("/")
    referer = request.headers.get("referer") or request.headers.get("origin")
    if referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return os.getenv("CORS_ORIGIN", "http://localhost:3000").split(",")[0].strip().rstrip("/")

@app.get("/api/debug/graphql")
def debug_graphql():
    if not twitter_service._graphql_client:
        return {"error": "No graphql client configured"}
    client = twitter_service._graphql_client
    debug_log = []
    
    auth_token = client.auth_token
    ct0 = client.ct0
    
    # Test setting cookies properly on requests.Session
    s = requests.Session()
    for d in [".x.com", ".twitter.com", "x.com", "twitter.com"]:
        s.cookies.set("auth_token", auth_token, domain=d)
        s.cookies.set("ct0", ct0, domain=d)
        
    headers = {
        "Authorization": f"Bearer {twitter_service._graphql_client._base_headers()['Authorization'].replace('Bearer ', '')}",
        "x-csrf-token": ct0,
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "en",
        "x-twitter-auth-type": "OAuth2Session",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://x.com/",
        "Origin": "https://x.com",
        "Accept": "*/*",
    }
    s.headers.update(headers)
    
    # 1. Test account verify endpoint
    try:
        r_me = s.get("https://api.twitter.com/1.1/account/verify_credentials.json", timeout=10)
        debug_log.append({
            "check": "verify_credentials",
            "status": r_me.status_code,
            "text": r_me.text[:200]
        })
    except Exception as e:
        debug_log.append({"check": "verify_credentials", "error": str(e)})

    # 2. Test SearchTimeline with exact query
    import json
    variables = {
        "rawQuery": "Coldplay",
        "count": 5,
        "querySource": "typed_query",
        "product": "Latest"
    }
    features = {
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": False,
        "responsive_web_enhance_cards_enabled": False
    }

    url = "https://x.com/i/api/graphql/BGd0T_j7oVwlW5U79tO_0A/SearchTimeline"
    try:
        r_search = s.get(url, params={"variables": json.dumps(variables), "features": json.dumps(features)}, timeout=15)
        debug_log.append({
            "check": "SearchTimeline BGd0T",
            "status": r_search.status_code,
            "text": r_search.text[:300]
        })
    except Exception as e:
        debug_log.append({"check": "SearchTimeline BGd0T", "error": str(e)})

    return {"debug": debug_log}

@app.get("/")
def root():
    return {
        "service": "X AI Ticket-Matcher Direct Commenter",
        "live_x_connected": twitter_service.is_configured(),
        "target_seller": get_setting("seller_username", ""),
        "autonomous_scanner_active": autonomous_scanner.is_running,
        "health_endpoint": "/health"
    }

# --- Uptime & Health Check API (for UptimeRobot, Render keepalive, monitoring) ---
@app.get("/health")
@app.get("/api/health")
@app.head("/health")
@app.head("/api/health")
def health_check():
    """
    Dedicated lightweight health API for UptimeRobot, Render, and monitors.
    Returns HTTP 200 with uptime stats to keep the Render server warm 24/7.
    """
    uptime_seconds = int(time.time() - SERVER_START_TIME)
    return {
        "status": "healthy",
        "service": "x-ai-ticket-matcher",
        "uptime_seconds": uptime_seconds,
        "uptime_human": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s",
        "timestamp": int(time.time()),
        "scanner_active": autonomous_scanner.is_running,
        "x_connected": twitter_service.is_configured(),
        "target_seller": get_setting("seller_username", "")
    }

# --- 1-Click "Connect with 𝕏" Dual OAuth (OAuth 2.0 PKCE & OAuth 1.0a) ---
@app.get("/api/auth/twitter/connect")
@app.post("/api/auth/twitter/connect")
def start_twitter_oauth(request: Request):
    """
    Initiates 1-Click OAuth with X. Dynamically generates callback URL using the current host/Render URL.
    """
    base_url = get_backend_url(request)
    callback_url = f"{base_url}/api/auth/twitter/callback"
    try:
        res = twitter_service.generate_oauth_url(callback_url)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"{e}"
        )

@app.get("/api/auth/twitter/callback")
def twitter_oauth_callback(
    request: Request,
    oauth_token: Optional[str] = Query(None),
    oauth_verifier: Optional[str] = Query(None),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None)
):
    """
    Handles redirect callback from X for both OAuth 2.0 and OAuth 1.0a.
    Saves tokens to .env and redirects back to the Vercel/local dashboard.
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    frontend_base = get_frontend_url(request)
    try:
        # OAuth 2.0 flow
        if code:
            full_url = str(request.url)
            tokens = twitter_service.exchange_oauth2_callback(full_url, state=state)
            access_token = tokens["access_token"]
            refresh_token = tokens.get("access_token_secret", "")
            
            os.environ["TWITTER_ACCESS_TOKEN"] = access_token
            set_key(env_path, "TWITTER_ACCESS_TOKEN", access_token)
            if refresh_token:
                os.environ["TWITTER_ACCESS_TOKEN_SECRET"] = refresh_token
                set_key(env_path, "TWITTER_ACCESS_TOKEN_SECRET", refresh_token)
                
            twitter_service.reload_credentials(access_token=access_token)
            log_activity("success", "Connected to 𝕏 via OAuth 2.0! Authorized user account saved.")
            return RedirectResponse(url=f"{frontend_base}/?connected=true")

        # OAuth 1.0a flow
        if oauth_token and oauth_verifier:
            tokens = twitter_service.exchange_oauth1_verifier(oauth_token, oauth_verifier)
            access_token = tokens["access_token"]
            access_token_secret = tokens["access_token_secret"]
            
            os.environ["TWITTER_ACCESS_TOKEN"] = access_token
            set_key(env_path, "TWITTER_ACCESS_TOKEN", access_token)
            os.environ["TWITTER_ACCESS_TOKEN_SECRET"] = access_token_secret
            set_key(env_path, "TWITTER_ACCESS_TOKEN_SECRET", access_token_secret)
            
            twitter_service.reload_credentials(
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            log_activity("success", "Connected to 𝕏 via OAuth 1.0a! Access tokens saved.")
            return RedirectResponse(url=f"{frontend_base}/?connected=true")

        raise RuntimeError("Missing OAuth authentication tokens from Twitter callback.")
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        log_activity("error", f"X OAuth connection failed: {e}")
        return RedirectResponse(url=f"{frontend_base}/?error={str(e)}")

@app.get("/api/status", response_model=SystemStatusResponse)
def get_system_status():
    ai_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("AI_API_KEY", "").strip()
    ai_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    cred_status = twitter_service.get_credential_status()
    stats = get_stats()
    seller_username = get_setting("seller_username", "").lstrip("@")
    
    return SystemStatusResponse(
        live_x_connected=twitter_service.is_configured(),
        can_search_x=cred_status["can_search"],
        can_post_x=cred_status["can_comment"],
        ai_configured=bool(ai_key),
        ai_model=ai_model,
        ai_status=f"Gemini Active ({ai_model})" if ai_key else "Rule-Based Fallback",
        target_seller_username=seller_username,
        autonomous_scanner=AutonomousScannerConfig(
            is_running=autonomous_scanner.is_running,
            interval_seconds=autonomous_scanner.interval_seconds,
            confidence_threshold=autonomous_scanner.confidence_threshold
        ),
        stats=stats,
        credentials=cred_status
    )

# --- Target Seller Username Endpoints ---
@app.get("/api/settings/seller")
def get_target_seller():
    seller = get_setting("seller_username", "").lstrip("@")
    return {"seller_username": seller}

@app.post("/api/settings/seller")
def update_target_seller(req: SellerUsernameRequest):
    seller = req.seller_username.strip().lstrip("@")
    set_setting("seller_username", seller)
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    os.environ["DEFAULT_SELLER_USERNAME"] = seller
    set_key(env_path, "DEFAULT_SELLER_USERNAME", seller)
    log_activity("info", f"Target seller username set to @{seller}. All buyer comments will promote this seller.")
    return {"success": True, "seller_username": seller}

@app.post("/api/scan", response_model=ScanResponse)
async def trigger_realtime_scan(req: ScanRequest):
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Event keyword cannot be empty.")
        
    if not twitter_service.is_configured():
        raise HTTPException(
            status_code=400,
            detail="X API credentials missing. Please click 'Connect with 𝕏' or enter keys in Settings."
        )

    await autonomous_scanner.run_scan_cycle_for_keyword(keyword)
    
    matches_data = get_matches(keyword=keyword, limit=req.count)
    matches_list = [MatchRecord(**m) for m in matches_data]
    auto_posted = sum(1 for m in matches_list if m.status == 'auto_posted')
    
    return ScanResponse(
        keyword=keyword,
        buyers_found=len(matches_list),
        sellers_found=len(matches_list),
        matches_created=len(matches_list),
        auto_posted_count=auto_posted,
        matches=matches_list
    )

@app.get("/api/matches", response_model=List[MatchRecord])
def list_matches(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200)
):
    rows = get_matches(status=status, keyword=keyword, limit=limit)
    return [MatchRecord(**row) for row in rows]

@app.post("/api/matches/{match_id}/post", response_model=PostResultResponse)
def manual_comment_on_buyer(match_id: int, req: ApprovePostRequest):
    record = get_match_by_id(match_id)
    if not record:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    reply_text = (req.reply_text or record["suggested_reply"]).strip()
    if not reply_text:
        raise HTTPException(status_code=400, detail="Comment text cannot be empty.")
        
    try:
        res = twitter_service.post_comment_on_buyer_tweet(
            comment_text=reply_text,
            buyer_tweet_id=record["buyer_tweet_id"],
            buyer_username=record["buyer_username"],
            seller_username=record["seller_username"],
            event_keyword=record["event_keyword"]
        )
        
        tweet_id = res.get("tweet_id", "")
        
        update_match_status(
            match_id=match_id,
            status="approved",
            post_type="comment",
            posted_tweet_id=tweet_id,
            reply_text=reply_text
        )
        
        log_activity("success", f"Direct comment posted on @{record['buyer_username']}'s tweet! ID: {tweet_id}")
        
        return PostResultResponse(
            success=True,
            match_id=match_id,
            post_type="comment",
            tweet_id=tweet_id,
            message=res.get("message", "Comment posted successfully."),
            posted_text=reply_text
        )
    except Exception as e:
        logger.error(f"Error commenting on match {match_id}: {e}")
        log_activity("error", f"Comment failed on @{record['buyer_username']}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/matches/{match_id}")
def remove_match(match_id: int):
    success = delete_match(match_id)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found.")
    return {"success": True, "message": f"Match {match_id} deleted."}

# Monitored Keywords
@app.get("/api/keywords", response_model=List[MonitoredKeyword])
def list_monitored_keywords():
    rows = get_monitored_keywords()
    return [MonitoredKeyword(id=r["id"], keyword=r["keyword"], is_active=bool(r["is_active"]), created_at=r["created_at"]) for r in rows]

@app.post("/api/keywords", response_model=MonitoredKeyword)
def add_keyword(req: AddKeywordRequest):
    kw = req.keyword.strip()
    if not kw:
        raise HTTPException(status_code=400, detail="Keyword cannot be empty.")
    success = add_monitored_keyword(kw)
    if not success:
        raise HTTPException(status_code=400, detail=f"Keyword '{kw}' is already monitored.")
    kws = get_monitored_keywords()
    added = next((k for k in kws if k["keyword"] == kw), None)
    return MonitoredKeyword(id=added["id"], keyword=added["keyword"], is_active=bool(added["is_active"]), created_at=added["created_at"])

@app.delete("/api/keywords/{keyword_id}")
def delete_keyword(keyword_id: int):
    success = remove_monitored_keyword(keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Keyword not found.")
    return {"success": True}

# Activity Logs
@app.get("/api/logs", response_model=List[ActivityLogRecord])
def fetch_activity_logs(limit: int = 50):
    rows = get_activity_logs(limit=limit)
    return [ActivityLogRecord(**r) for r in rows]

# Scanner Controls
@app.post("/api/scanner/toggle")
def toggle_autonomous_scanner():
    if autonomous_scanner.is_running:
        autonomous_scanner.stop()
    else:
        autonomous_scanner.start()
    return {
        "is_running": autonomous_scanner.is_running,
        "interval_seconds": autonomous_scanner.interval_seconds,
        "confidence_threshold": autonomous_scanner.confidence_threshold
    }

@app.post("/api/scanner/config")
def update_scanner_settings(interval: Optional[int] = Query(None), threshold: Optional[int] = Query(None)):
    autonomous_scanner.set_config(interval=interval, threshold=threshold)
    return {
        "is_running": autonomous_scanner.is_running,
        "interval_seconds": autonomous_scanner.interval_seconds,
        "confidence_threshold": autonomous_scanner.confidence_threshold
    }

# Live Credentials Update
@app.post("/api/config")
def update_credentials(req: ConfigUpdateRequest):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    if req.twitter_client_id is not None:
        os.environ["TWITTER_CLIENT_ID"] = req.twitter_client_id
        set_key(env_path, "TWITTER_CLIENT_ID", req.twitter_client_id)
    if req.twitter_client_secret is not None:
        os.environ["TWITTER_CLIENT_SECRET"] = req.twitter_client_secret
        set_key(env_path, "TWITTER_CLIENT_SECRET", req.twitter_client_secret)
    if req.twitter_api_key is not None:
        os.environ["TWITTER_API_KEY"] = req.twitter_api_key
        set_key(env_path, "TWITTER_API_KEY", req.twitter_api_key)
    if req.twitter_api_secret is not None:
        os.environ["TWITTER_API_SECRET"] = req.twitter_api_secret
        set_key(env_path, "TWITTER_API_SECRET", req.twitter_api_secret)
    if req.twitter_access_token is not None:
        os.environ["TWITTER_ACCESS_TOKEN"] = req.twitter_access_token
        set_key(env_path, "TWITTER_ACCESS_TOKEN", req.twitter_access_token)
    if req.twitter_access_token_secret is not None:
        os.environ["TWITTER_ACCESS_TOKEN_SECRET"] = req.twitter_access_token_secret
        set_key(env_path, "TWITTER_ACCESS_TOKEN_SECRET", req.twitter_access_token_secret)
    if req.twitter_bearer_token is not None:
        os.environ["TWITTER_BEARER_TOKEN"] = req.twitter_bearer_token
        set_key(env_path, "TWITTER_BEARER_TOKEN", req.twitter_bearer_token)
    if req.twitter_auth_token is not None:
        os.environ["TWITTER_AUTH_TOKEN"] = req.twitter_auth_token
        set_key(env_path, "TWITTER_AUTH_TOKEN", req.twitter_auth_token)
    if req.twitter_ct0 is not None:
        os.environ["TWITTER_CT0"] = req.twitter_ct0
        set_key(env_path, "TWITTER_CT0", req.twitter_ct0)
    if req.gemini_api_key is not None:
        os.environ["GEMINI_API_KEY"] = req.gemini_api_key
        set_key(env_path, "GEMINI_API_KEY", req.gemini_api_key)
    if req.gemini_api_key_fallback is not None:
        os.environ["GEMINI_API_KEY_FALLBACK"] = req.gemini_api_key_fallback
        set_key(env_path, "GEMINI_API_KEY_FALLBACK", req.gemini_api_key_fallback)
    if req.gemini_model is not None:
        os.environ["GEMINI_MODEL"] = req.gemini_model
        set_key(env_path, "GEMINI_MODEL", req.gemini_model)
    if req.ai_api_key is not None:
        os.environ["GEMINI_API_KEY"] = req.ai_api_key
        set_key(env_path, "GEMINI_API_KEY", req.ai_api_key)
    if req.ai_model is not None:
        os.environ["GEMINI_MODEL"] = req.ai_model
        set_key(env_path, "GEMINI_MODEL", req.ai_model)
    if req.seller_username is not None:
        clean_seller = req.seller_username.strip().lstrip("@")
        set_setting("seller_username", clean_seller)
        os.environ["DEFAULT_SELLER_USERNAME"] = clean_seller
        set_key(env_path, "DEFAULT_SELLER_USERNAME", clean_seller)
        
    twitter_service.reload_credentials(
        api_key=os.environ.get("TWITTER_API_KEY", ""),
        api_secret=os.environ.get("TWITTER_API_SECRET", ""),
        access_token=os.environ.get("TWITTER_ACCESS_TOKEN", ""),
        access_token_secret=os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", ""),
        bearer_token=os.environ.get("TWITTER_BEARER_TOKEN", ""),
        client_id=os.environ.get("TWITTER_CLIENT_ID", ""),
        client_secret=os.environ.get("TWITTER_CLIENT_SECRET", ""),
        auth_token=os.environ.get("TWITTER_AUTH_TOKEN", ""),
        ct0=os.environ.get("TWITTER_CT0", "")
    )
    
    if req.auto_scan_interval or req.auto_post_threshold:
        autonomous_scanner.set_config(interval=req.auto_scan_interval, threshold=req.auto_post_threshold)
        
    return {"success": True, "message": "Credentials updated successfully."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
