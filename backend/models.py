from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Tweet(BaseModel):
    id: str
    text: str
    author_username: str
    author_name: Optional[str] = None
    created_at: str
    role: str

class MatchEvaluation(BaseModel):
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    suggested_reply: str
    is_match: bool = True

class MatchRecord(BaseModel):
    id: int
    event_keyword: str
    buyer_tweet_id: str
    buyer_username: str
    buyer_text: str
    buyer_timestamp: str
    seller_tweet_id: str
    seller_username: str
    seller_text: str
    seller_timestamp: str
    confidence_score: int
    ai_reasoning: str
    suggested_reply: str
    status: str
    post_type: str
    posted_tweet_id: Optional[str] = None
    posted_at: Optional[str] = None
    created_at: str

class MonitoredKeyword(BaseModel):
    id: int
    keyword: str
    is_active: bool
    created_at: str

class AddKeywordRequest(BaseModel):
    keyword: str

class ScanRequest(BaseModel):
    keyword: str
    count: int = 10

class ScanResponse(BaseModel):
    keyword: str
    buyers_found: int
    sellers_found: int
    matches_created: int
    auto_posted_count: int
    matches: List[MatchRecord]

class ApprovePostRequest(BaseModel):
    reply_text: Optional[str] = None

class PostResultResponse(BaseModel):
    success: bool
    match_id: int
    post_type: str
    tweet_id: str
    message: str
    posted_text: str

class ActivityLogRecord(BaseModel):
    id: int
    level: str
    message: str
    details: Optional[str] = None
    timestamp: str

class AutonomousScannerConfig(BaseModel):
    is_running: bool
    interval_seconds: int
    confidence_threshold: int

class SellerUsernameRequest(BaseModel):
    seller_username: str

class ConfigUpdateRequest(BaseModel):
    twitter_client_id: Optional[str] = None
    twitter_client_secret: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_api_key_fallback: Optional[str] = None
    gemini_model: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None
    seller_username: Optional[str] = None
    auto_scan_interval: Optional[int] = None
    auto_post_threshold: Optional[int] = None

class SystemStatusResponse(BaseModel):
    live_x_connected: bool
    can_search_x: bool
    can_post_x: bool
    ai_configured: bool
    ai_model: str
    ai_status: str
    target_seller_username: str
    autonomous_scanner: AutonomousScannerConfig
    stats: Dict[str, Any]
    credentials: Dict[str, bool]
