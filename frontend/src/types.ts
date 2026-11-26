export interface MatchRecord {
  id: number;
  event_keyword: string;
  buyer_tweet_id: string;
  buyer_username: string;
  buyer_text: string;
  buyer_timestamp: string;
  seller_tweet_id: string;
  seller_username: string;
  seller_text: string;
  seller_timestamp: string;
  confidence_score: number;
  ai_reasoning: string;
  suggested_reply: string;
  status: 'auto_posted' | 'approved' | 'pending' | 'failed';
  post_type: 'none' | 'reply' | 'standalone_post' | 'comment';
  posted_tweet_id?: string | null;
  posted_at?: string | null;
  created_at: string;
}

export interface MonitoredKeyword {
  id: number;
  keyword: string;
  is_active: boolean;
  created_at: string;
}

export interface ActivityLog {
  id: number;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
  details?: string | null;
  timestamp: string;
}

export interface SystemStatus {
  live_x_connected: boolean;
  can_search_x: boolean;
  can_post_x: boolean;
  ai_configured: boolean;
  ai_model: string;
  ai_status: string;
  target_seller_username: string;
  autonomous_scanner: {
    is_running: boolean;
    interval_seconds: number;
    confidence_threshold: number;
  };
  stats: {
    total_matches: number;
    auto_posted: number;
    manual_approved: number;
    posted: number;
    high_confidence: number;
    active_keywords: number;
  };
  credentials: {
    has_bearer_token: boolean;
    has_client_id?: boolean;
    has_twikit_cookies?: boolean;
    has_api_key: boolean;
    has_api_secret: boolean;
    has_access_token: boolean;
    has_access_token_secret: boolean;
    can_search: boolean;
    can_comment: boolean;
  };
}

export interface ScanResponse {
  keyword: string;
  buyers_found: number;
  sellers_found: number;
  matches_created: number;
  auto_posted_count: number;
  matches: MatchRecord[];
}

export interface PostResult {
  success: boolean;
  match_id: number;
  post_type: 'reply' | 'standalone_post' | 'comment';
  tweet_id: string;
  message: string;
  posted_text: string;
}
