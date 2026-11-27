import os
import asyncio
import logging
import json
import time
import re
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

import requests

# Allow OAuth 2.0 PKCE over http:// for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Inject operating system certificate store for Windows/Mac SSL verification
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

import tweepy
from models import Tweet

logger = logging.getLogger("twitter_service")

# In-memory stores for pending OAuth handshakes
_oauth1_request_tokens: Dict[str, str] = {}
_oauth2_handlers: Dict[str, tweepy.OAuth2UserHandler] = {}

# ─────────────────────────────────────────────────────────────────────────────
# X GraphQL Cookie Client — bypasses ClientTransaction entirely
# Works from any IP (including datacenter IPs like Render/AWS) using
# the public web bearer token + auth_token + ct0 cookies.
# ─────────────────────────────────────────────────────────────────────────────

# X's public web bearer token (the one used by x.com in the browser)
_WEB_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# GraphQL query IDs — dynamically extracted from live x.com client bundles
_SEARCH_QUERY_IDS = [
    "vLHjqbDv7TPFMBkIIO1nOA",   # Verified live active on x.com
    "BGd0T_j7oVwlW5U79tO_0A",
    "gkjsKepM6gl_HmFWoWKfgg",
    "nK1dw4oV3k4w5TdtcAdSww",
]
_CREATE_TWEET_QUERY_IDS = [
    "l4hk8uVGvR-a8kzQ4nOhPA",   # Verified live active on x.com
    "wUgPBh9hEKhMMGlg8uDuFw",
    "oB-5XsHNAbjvARJEc8CZFw",
]

_cached_search_qid: Optional[str] = None
_cached_create_qid: Optional[str] = None


def _fetch_live_query_id(operation: str) -> Optional[str]:
    """
    Scrape x.com's webpack bundle to get the current live GraphQL queryId
    for a given operation name (e.g. 'SearchTimeline', 'CreateTweet').
    Returns None if unreachable or not found.
    """
    try:
        resp = requests.get(
            "https://x.com/",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                )
            },
            timeout=15,
        )
        # Find main JS bundle URL
        js_urls = re.findall(r'src="(https://abs\.twimg\.com/[^"]+\.js)"', resp.text)
        if not js_urls:
            js_urls = re.findall(r'"(https://abs\.twimg\.com/x-web[^"]+\.js)"', resp.text)

        for js_url in js_urls[:5]:
            try:
                js_resp = requests.get(js_url, timeout=15)
                # Pattern: queryId:"<id>",operationName:"SearchTimeline"
                pattern = rf'queryId:"([^"]+)",operationName:"{re.escape(operation)}"'
                match = re.search(pattern, js_resp.text)
                if match:
                    return match.group(1)
            except Exception:
                continue
    except Exception:
        pass
    return None


class XGraphQLClient:
    """
    Direct X GraphQL client using browser cookies.
    Does NOT use twikit/twifork — no ClientTransaction required.
    Makes raw HTTPS requests identical to what x.com sends in the browser.
    """

    def __init__(self, auth_token: str, ct0: str):
        self.auth_token = auth_token.strip()
        self.ct0 = ct0.strip()
        self._session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        # Set cookies on cookie jar for all relevant domains
        for domain in [".x.com", ".twitter.com", "x.com", "twitter.com"]:
            self._session.cookies.set("auth_token", self.auth_token, domain=domain)
            self._session.cookies.set("ct0", self.ct0, domain=domain)

        self._session.headers.update(self._base_headers())

    def _base_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {_WEB_BEARER}",
            "x-csrf-token": self.ct0,
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "x-twitter-auth-type": "OAuth2Session",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://x.com/",
            "Origin": "https://x.com",
            # Also include explicit Cookie header for servers that inspect it directly
            "Cookie": f"auth_token={self.auth_token}; ct0={self.ct0}",
        }

    def _refresh_headers(self):
        """Refresh cookies in headers and cookie jar (call after ct0 update)."""
        self._setup_session()

    def search_tweets(self, query: str, count: int = 20) -> List[Dict[str, Any]]:
        """Search tweets via X's internal GraphQL SearchTimeline endpoint.
        Uses POST request as required by X's web application bundle."""
        global _cached_search_qid

        variables = {
            "rawQuery": query,
            "count": min(count, 20),
            "querySource": "typed_query",
            "product": "Latest",
        }
        features = {
            "rweb_video_screen_enabled": False,
            "rweb_cashtags_enabled": True,
            "profile_label_improvements_pcf_label_in_post_enabled": True,
            "responsive_web_profile_redirect_enabled": False,
            "rweb_tipjar_consumption_enabled": False,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "premium_content_api_read_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
            "responsive_web_grok_analyze_post_followups_enabled": True,
            "responsive_web_jetfuel_frame": True,
            "responsive_web_grok_share_attachment_enabled": True,
            "responsive_web_grok_annotations_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "content_disclosure_indicator_enabled": True,
            "content_disclosure_ai_generated_indicator_enabled": True,
            "responsive_web_grok_show_grok_translated_post": True,
            "responsive_web_grok_analysis_button_from_backend": True,
            "post_ctas_fetch_enabled": True,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": False,
            "responsive_web_enhance_cards_enabled": False,
        }

        qids_to_try = []
        if _cached_search_qid:
            qids_to_try.append(_cached_search_qid)
        for qid in _SEARCH_QUERY_IDS:
            if qid not in qids_to_try:
                qids_to_try.append(qid)

        last_error = None
        for qid in qids_to_try:
            payload = {
                "variables": variables,
                "features": features,
                "queryId": qid,
            }
            url = f"https://x.com/i/api/graphql/{qid}/SearchTimeline"
            try:
                resp = self._session.post(url, json=payload, timeout=25)
                if resp.status_code == 403:
                    self._refresh_headers()
                    resp = self._session.post(url, json=payload, timeout=25)
                if resp.status_code == 404:
                    last_error = f"HTTP 404 for queryId {qid}"
                    continue
                resp.raise_for_status()
                data = resp.json()
                results = self._parse_search_results(data)
                _cached_search_qid = qid
                return results
            except RuntimeError:
                raise
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                if status == 404:
                    last_error = f"HTTP 404 for queryId {qid}"
                    continue
                raise RuntimeError(f"X GraphQL search HTTP {status}: {e}")
            except Exception as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"X GraphQL search failed. Last: {last_error}")

    def _parse_search_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Extract tweet objects from SearchTimeline GraphQL response."""
        tweets = []
        try:
            instructions = (
                data.get("data", {})
                .get("search_by_raw_query", {})
                .get("search_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
            )
            for instruction in instructions:
                entries = instruction.get("entries", [])
                for entry in entries:
                    # Standard tweet entry
                    item_content = (
                        entry.get("content", {})
                        .get("itemContent", {})
                    )
                    tweet_result = item_content.get("tweet_results", {}).get("result", {})
                    parsed = self._extract_tweet(tweet_result)
                    if parsed:
                        tweets.append(parsed)

                    # Module entries (grouped tweets)
                    items = entry.get("content", {}).get("items", [])
                    for item in items:
                        item_c = item.get("item", {}).get("itemContent", {})
                        tr = item_c.get("tweet_results", {}).get("result", {})
                        parsed2 = self._extract_tweet(tr)
                        if parsed2:
                            tweets.append(parsed2)
        except Exception as e:
            logger.warning(f"Error parsing GraphQL search results: {e}")
        return tweets

    def _extract_tweet(self, result: Dict) -> Optional[Dict[str, Any]]:
        """Extract a single tweet dict from a tweet_results.result object."""
        if not result:
            return None
        # Handle tweet wrapper
        if result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet", result)
        if result.get("__typename") not in ("Tweet", None) and result.get("__typename"):
            return None

        try:
            legacy = result.get("legacy", {})
            core = result.get("core", {})
            user_result = core.get("user_results", {}).get("result", {})
            user_core = user_result.get("core", {})
            user_legacy = user_result.get("legacy", {})

            tweet_id = legacy.get("id_str") or result.get("rest_id", "")
            text = legacy.get("full_text") or legacy.get("text", "")
            username = (
                user_core.get("screen_name")
                or user_legacy.get("screen_name")
                or user_result.get("screen_name", "unknown")
            )
            name = (
                user_core.get("name")
                or user_legacy.get("name")
                or user_result.get("name", username)
            )
            created_at = legacy.get("created_at", "")

            if not tweet_id or not text:
                return None

            # Skip retweets and replies
            if text.startswith("RT @") or legacy.get("in_reply_to_status_id_str"):
                return None

            return {
                "id": tweet_id,
                "text": text,
                "username": username,
                "name": name,
                "created_at": created_at,
            }
        except Exception:
            return None

    def create_tweet(self, text: str, reply_to_id: Optional[str] = None) -> str:
        """Post a tweet or reply via X's internal CreateTweet GraphQL endpoint."""
        global _cached_create_qid

        variables: Dict[str, Any] = {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
        }
        if reply_to_id:
            variables["reply"] = {
                "in_reply_to_tweet_id": reply_to_id,
                "exclude_reply_user_ids": [],
            }

        features = {
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "tweetypie_unmention_optimization_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "interactive_text_enabled": True,
            "responsive_web_text_conversations_enabled": False,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_enhance_cards_enabled": False,
        }

        # Try known queryIds
        qids_to_try = []
        if _cached_create_qid:
            qids_to_try.append(_cached_create_qid)
        for qid in _CREATE_TWEET_QUERY_IDS:
            if qid not in qids_to_try:
                qids_to_try.append(qid)

        last_error = None
        for qid in qids_to_try:
            payload = {
                "variables": variables,
                "features": features,
                "queryId": qid,
            }
            for host in ["x.com", "twitter.com"]:
                url = f"https://{host}/i/api/graphql/{qid}/CreateTweet"
                try:
                    resp = self._session.post(url, json=payload, timeout=30)
                    if resp.status_code == 403:
                        self._refresh_headers()
                        resp = self._session.post(url, json=payload, timeout=30)
                    if resp.status_code == 404:
                        last_error = f"HTTP 404 for queryId {qid} on {host}"
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    tweet_id = (
                        data.get("data", {})
                        .get("create_tweet", {})
                        .get("tweet_results", {})
                        .get("result", {})
                        .get("rest_id", "")
                    )
                    if not tweet_id:
                        raise RuntimeError("CreateTweet: no tweet ID in response")
                    _cached_create_qid = qid
                    return tweet_id
                except RuntimeError:
                    raise
                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response is not None else "?"
                    body = ""
                    try:
                        body = e.response.text[:300]
                    except Exception:
                        pass
                    if status == 404:
                        last_error = f"HTTP 404 for queryId {qid} on {host}"
                        continue
                    raise RuntimeError(f"X GraphQL CreateTweet HTTP {status}: {body}")
                except Exception as e:
                    last_error = str(e)
                    continue

        # Try live discovery
        live_qid = _fetch_live_query_id("CreateTweet")
        if live_qid:
            payload = {"variables": variables, "features": features, "queryId": live_qid}
            for host in ["x.com", "twitter.com"]:
                url = f"https://{host}/i/api/graphql/{live_qid}/CreateTweet"
                try:
                    resp = self._session.post(url, json=payload, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                    tweet_id = (
                        data.get("data", {}).get("create_tweet", {})
                        .get("tweet_results", {}).get("result", {}).get("rest_id", "")
                    )
                    if not tweet_id:
                        raise RuntimeError("CreateTweet: no tweet ID in response")
                    _cached_create_qid = live_qid
                    return tweet_id
                except Exception as e:
                    last_error = str(e)
                    continue

        raise RuntimeError(f"X GraphQL CreateTweet failed — all queryIds returned 404. Last: {last_error}")

    def verify_session(self) -> bool:
        """Quick check that the cookies are valid."""
        for url in [
            "https://api.twitter.com/1.1/account/verify_credentials.json",
            "https://api.x.com/1.1/account/verify_credentials.json",
        ]:
            try:
                resp = self._session.get(url, timeout=15)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main TwitterService
# ─────────────────────────────────────────────────────────────────────────────

class TwitterService:
    def __init__(self):
        self.client_id = os.getenv("TWITTER_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("TWITTER_CLIENT_SECRET", "").strip()
        self.api_key = os.getenv("TWITTER_API_KEY", "").strip()
        self.api_secret = os.getenv("TWITTER_API_SECRET", "").strip()
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
        self.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
        self.auth_token = os.getenv("TWITTER_AUTH_TOKEN", "").strip()
        self.ct0 = os.getenv("TWITTER_CT0", "").strip()

        # Smart Auto-Detection: If user pasted OAuth 2.0 Client ID into API Key field
        self._normalize_credentials()
        self._client: Optional[tweepy.Client] = None
        self._search_client: Optional[tweepy.Client] = None
        self._graphql_client: Optional[XGraphQLClient] = None
        self._is_oauth2: bool = False
        self._init_client()

    def _normalize_credentials(self):
        """Auto-detects if an OAuth 2.0 Client ID was entered into API Key field."""
        if not self.client_id and self.api_key and (":" in self.api_key or self.api_key.endswith(":ci") or len(self.api_key) > 30):
            logger.info("Auto-detected OAuth 2.0 Client ID passed in API Key field! Promoting to client_id.")
            self.client_id = self.api_key
            if not self.client_secret and self.api_secret:
                self.client_secret = self.api_secret
            self.api_key = ""
            self.api_secret = ""

    def _init_client(self):
        self._is_oauth2 = bool(self.access_token and not self.api_key)

        if self._is_oauth2 and self.access_token:
            try:
                self._client = tweepy.Client(
                    bearer_token=self.access_token,
                    wait_on_rate_limit=True
                )
                logger.info("Live Tweepy Client initialized (OAuth 2.0 User Context).")
            except Exception as e:
                logger.error(f"Failed to initialize OAuth 2.0 Tweepy Client: {e}")
                self._client = None
        elif (self.api_key and self.access_token) or self.bearer_token or self.access_token:
            try:
                self._client = tweepy.Client(
                    bearer_token=self.bearer_token or None,
                    consumer_key=self.api_key or None,
                    consumer_secret=self.api_secret or None,
                    access_token=self.access_token or None,
                    access_token_secret=self.access_token_secret or None,
                    wait_on_rate_limit=True
                )
                logger.info("Live Tweepy Client initialized (OAuth 1.0a / Bearer).")
            except Exception as e:
                logger.error(f"Failed to initialize Tweepy Client: {e}")
                self._client = None
        else:
            self._client = None

        if self.bearer_token:
            try:
                self._search_client = tweepy.Client(
                    bearer_token=self.bearer_token,
                    wait_on_rate_limit=True
                )
            except Exception:
                self._search_client = self._client
        else:
            self._search_client = self._client

        # Initialize GraphQL cookie client (replaces twifork/twikit)
        if self.auth_token and self.ct0:
            try:
                self._graphql_client = XGraphQLClient(self.auth_token, self.ct0)
                logger.info("X GraphQL cookie client initialized (auth_token + ct0).")
            except Exception as e:
                logger.error(f"Failed to initialize GraphQL cookie client: {e}")
                self._graphql_client = None
        else:
            self._graphql_client = None

    def reload_credentials(
        self,
        api_key: str = "",
        api_secret: str = "",
        access_token: str = "",
        access_token_secret: str = "",
        bearer_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        auth_token: str = "",
        ct0: str = ""
    ):
        if api_key: self.api_key = api_key.strip()
        if api_secret: self.api_secret = api_secret.strip()
        if access_token: self.access_token = access_token.strip()
        if access_token_secret: self.access_token_secret = access_token_secret.strip()
        if bearer_token: self.bearer_token = bearer_token.strip()
        if client_id: self.client_id = client_id.strip()
        if client_secret: self.client_secret = client_secret.strip()
        if auth_token: self.auth_token = auth_token.strip()
        if ct0: self.ct0 = ct0.strip()
        self._normalize_credentials()
        self._init_client()

    def is_configured(self) -> bool:
        has_official = self._client is not None and bool(self.access_token or self.bearer_token)
        has_graphql = self._graphql_client is not None
        return has_official or has_graphql

    def get_credential_status(self) -> Dict[str, Any]:
        has_graphql = self._graphql_client is not None
        return {
            "has_bearer_token": bool(self.bearer_token),
            "has_client_id": bool(self.client_id),
            "has_api_key": bool(self.api_key),
            "has_api_secret": bool(self.api_secret),
            "has_access_token": bool(self.access_token),
            "has_access_token_secret": bool(self.access_token_secret),
            "has_twikit_cookies": has_graphql,
            "can_search": bool(self.bearer_token or self.api_key or self.access_token or has_graphql),
            "can_comment": bool(self.access_token or has_graphql)
        }

    # --- Dual OAuth Connect: OAuth 2.0 PKCE or OAuth 1.0a ---
    def generate_oauth_url(self, callback_url: str) -> Dict[str, str]:
        # 1. Prefer OAuth 2.0 PKCE if client_id is available
        if self.client_id:
            handler = tweepy.OAuth2UserHandler(
                client_id=self.client_id,
                redirect_uri=callback_url,
                scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
                client_secret=self.client_secret or None
            )
            auth_url = handler.get_authorization_url()
            state = handler.new_state if hasattr(handler, 'new_state') else "default"
            _oauth2_handlers[state] = handler
            _oauth2_handlers["latest"] = handler
            return {"auth_url": auth_url, "type": "oauth2"}

        # 2. OAuth 1.0a fallback
        if self.api_key and self.api_secret:
            try:
                auth = tweepy.OAuth1UserHandler(
                    consumer_key=self.api_key,
                    consumer_secret=self.api_secret,
                    callback=callback_url
                )
                url = auth.get_authorization_url()
                if auth.request_token and "oauth_token" in auth.request_token:
                    _oauth1_request_tokens[auth.request_token["oauth_token"]] = auth.request_token["oauth_token_secret"]
                return {"auth_url": url, "type": "oauth1"}
            except tweepy.errors.TweepyException as e:
                err_msg = str(e)
                if "401" in err_msg or "Could not authenticate you" in err_msg:
                    raise RuntimeError(
                        "X rejected your API Key or API Secret (401 Unauthorized). "
                        "Please go to developer.x.com -> Keys and Tokens tab, click 'Regenerate' under Consumer Keys, "
                        "and make sure 'User authentication settings' is enabled with 'Read and write' permissions."
                    )
                raise RuntimeError(f"Twitter OAuth error: {err_msg}")
            except Exception as e:
                raise RuntimeError(f"OAuth connection error: {e}")

        raise RuntimeError(
            "To connect with 𝕏, please enter your Client ID (or API Key & Secret) in Settings first, then click Connect."
        )

    def exchange_oauth2_callback(self, full_redirect_url: str, state: Optional[str] = None) -> Dict[str, str]:
        handler = None
        if state and state in _oauth2_handlers:
            handler = _oauth2_handlers[state]
        if not handler:
            handler = _oauth2_handlers.get("latest")

        if not handler and self.client_id:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(full_redirect_url)
                base_callback = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                handler = tweepy.OAuth2UserHandler(
                    client_id=self.client_id,
                    redirect_uri=base_callback,
                    scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
                    client_secret=self.client_secret or None
                )
            except Exception as e:
                logger.warning(f"Failed to reconstruct OAuth2 handler: {e}")

        if not handler:
            raise RuntimeError("OAuth2 session expired. Please click 'Connect with 𝕏' again.")

        token_data = handler.fetch_token(full_redirect_url)
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        return {
            "access_token": access_token,
            "access_token_secret": refresh_token
        }

    def exchange_oauth1_verifier(self, oauth_token: str, oauth_verifier: str) -> Dict[str, str]:
        oauth_token_secret = _oauth1_request_tokens.get(oauth_token)
        if not oauth_token_secret:
            raise RuntimeError("OAuth1 session expired. Please click 'Connect with 𝕏' again.")
        auth = tweepy.OAuth1UserHandler(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret
        )
        auth.request_token = {
            "oauth_token": oauth_token,
            "oauth_token_secret": oauth_token_secret
        }
        access_token, access_token_secret = auth.get_access_token(oauth_verifier)
        return {
            "access_token": access_token,
            "access_token_secret": access_token_secret
        }

    # --- GraphQL cookie search ---
    def _graphql_search(self, query: str, role: str, count: int = 20) -> List[Tweet]:
        if not self._graphql_client:
            raise RuntimeError("GraphQL cookie client (auth_token + ct0) not configured.")

        logger.info(f"Using X GraphQL cookie search ({role}): {query}")
        raw = self._graphql_client.search_tweets(query, count=count)

        tweets = []
        for t in raw:
            tweets.append(Tweet(
                id=t["id"],
                text=t["text"],
                author_username=t["username"],
                author_name=t["name"],
                created_at=t["created_at"],
                role=role
            ))
        return tweets

    # --- GraphQL cookie reply ---
    def _graphql_reply(self, text: str, reply_to_id: str, buyer_username: str) -> Dict[str, Any]:
        if not self._graphql_client:
            raise RuntimeError("GraphQL cookie client (auth_token + ct0) not configured.")

        tweet_id = self._graphql_client.create_tweet(text=text, reply_to_id=reply_to_id)
        return {
            "success": True,
            "post_type": "comment",
            "tweet_id": tweet_id,
            "message": f"Successfully commented on @{buyer_username}'s tweet via GraphQL! (Tweet ID: {tweet_id})"
        }

    # --- Live Search with Targeted Intent Phrases ---
    def search_buyers(self, keyword: str, count: int = 10) -> List[Tweet]:
        if not self._client and not self._graphql_client:
            raise RuntimeError("X client not configured. Connect your X account or add auth_token + ct0 cookies in Settings.")

        # Multilingual buyer search query strictly requiring ticket terms with the keyword
        query = (
            f'"{keyword}" '
            f'(ticket OR tickets OR tix OR pass OR passes OR entrada OR entradas OR boleta OR boletas OR billet OR billets OR place OR places OR karte OR karten OR biglietto OR biglietti OR ingresso OR ingressos) '
            f'(need OR looking OR want OR buy OR wtb OR spare OR extra OR anyone OR who OR busco OR compro OR cherche OR suche OR cerco OR procuro) '
            f'-RT'
        )

        # 1. Prefer GraphQL cookie search if cookies are configured (Free, no rate limits, works without paid tier)
        if self._graphql_client:
            try:
                return self._graphql_search(query, "buyer", count)
            except Exception as e:
                logger.warning(f"GraphQL cookie search failed ({e}), attempting official API fallback...")

        # 2. Fallback: Official API (requires Basic/Pro tier for search)
        client = self._search_client or self._client
        if client:
            try:
                logger.info(f"Searching live X for buyers (official API): {query}")
                use_oauth1 = not getattr(self, "_is_oauth2", False) and not self.bearer_token
                response = client.search_recent_tweets(
                    query=query,
                    max_results=min(max(count, 10), 50),
                    tweet_fields=["created_at", "author_id", "text"],
                    expansions=["author_id"],
                    user_fields=["username", "name"],
                    user_auth=use_oauth1
                )
                if response and response.data:
                    users_map = {u.id: u for u in (response.includes.get("users", []) if response.includes else [])}
                    tweets = []
                    for t in response.data:
                        user = users_map.get(t.author_id)
                        uname = user.username if user else f"user_{t.author_id}"
                        name = user.name if user else uname
                        created = t.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if t.created_at else ""
                        tweets.append(Tweet(
                            id=str(t.id),
                            text=t.text,
                            author_username=uname,
                            author_name=name,
                            created_at=created,
                            role="buyer"
                        ))
                    return tweets
                return []
            except Exception as te:
                logger.error(f"Tweepy buyer search error: {te}")
                raise RuntimeError(self._format_search_error(te))

        return []

    def _format_search_error(self, te: Exception) -> str:
        err_str = str(te)
        if "401" in err_str or "403" in err_str:
            user_valid = False
            try:
                if self._client:
                    me = self._client.get_me(user_auth=not getattr(self, "_is_oauth2", False))
                    if me and me.data:
                        user_valid = True
            except Exception:
                pass

            if user_valid:
                return (
                    f"X API Search blocked ({err_str}). Your @account OAuth 2.0 login IS valid, "
                    "but X's Free Developer tier does NOT include Tweet Search (/2/tweets/search/recent). "
                    "To enable live search: add auth_token + ct0 cookies in Settings -> Tab 3."
                )
            elif not self.bearer_token:
                return (
                    f"X API Search Error ({err_str}). Add your auth_token + ct0 cookies in Settings -> Tab 3 "
                    "to enable free GraphQL search."
                )
        return f"X API Search Error: {err_str}"

    def search_sellers(self, keyword: str, count: int = 10) -> List[Tweet]:
        if not self._client and not self._graphql_client:
            raise RuntimeError("X client not configured. Connect your X account or add auth_token + ct0 cookies in Settings.")

        # Multilingual seller search query strictly requiring ticket terms with the keyword
        query = (
            f'"{keyword}" '
            f'(ticket OR tickets OR tix OR pass OR passes OR entrada OR entradas OR billet OR billets OR karte OR karten OR biglietto OR biglietti OR ingresso OR ingressos) '
            f'("selling" OR "have extra" OR "spare" OR "wts" OR "available" OR "vendo" OR "vends" OR "verkaufe") '
            f'-RT'
        )

        # 1. Prefer GraphQL cookie search if cookies are configured
        if self._graphql_client:
            try:
                return self._graphql_search(query, "seller", count)
            except Exception as e:
                logger.warning(f"GraphQL cookie seller search failed ({e}), attempting official API fallback...")

        # 2. Fallback: Official API
        client = self._search_client or self._client
        if client:
            try:
                logger.info(f"Searching live X for sellers (official API): {query}")
                use_oauth1 = not getattr(self, "_is_oauth2", False) and not self.bearer_token
                response = client.search_recent_tweets(
                    query=query,
                    max_results=min(max(count, 10), 50),
                    tweet_fields=["created_at", "author_id", "text"],
                    expansions=["author_id"],
                    user_fields=["username", "name"],
                    user_auth=use_oauth1
                )
                if response and response.data:
                    users_map = {u.id: u for u in (response.includes.get("users", []) if response.includes else [])}
                    tweets = []
                    for t in response.data:
                        user = users_map.get(t.author_id)
                        uname = user.username if user else f"user_{t.author_id}"
                        name = user.name if user else uname
                        created = t.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if t.created_at else ""
                        tweets.append(Tweet(
                            id=str(t.id),
                            text=t.text,
                            author_username=uname,
                            author_name=name,
                            created_at=created,
                            role="seller"
                        ))
                    return tweets
                return []
            except Exception as te:
                logger.error(f"Tweepy seller search error: {te}")
                raise RuntimeError(self._format_search_error(te))

        return []

    # --- Comment Directly on Buyer's Tweet ---
    def post_comment_on_buyer_tweet(
        self,
        comment_text: str,
        buyer_tweet_id: str,
        buyer_username: str,
        seller_username: str,
        event_keyword: str
    ) -> Dict[str, Any]:
        if (not self._client or not self.access_token) and not self._graphql_client:
            raise RuntimeError(
                "X commenting requires an authorized User Account or auth_token + ct0 cookies in Settings."
            )

        formatted_comment = comment_text.strip()
        if f"@{buyer_username}" in formatted_comment:
            formatted_comment = formatted_comment.replace(f"@{buyer_username}", "").strip()
            formatted_comment = formatted_comment.lstrip(",:;- ").strip()

        if len(formatted_comment) > 275:
            formatted_comment = formatted_comment[:270] + "..."

        # Try official Tweepy first
        if self._client and self.access_token:
            try:
                logger.info(f"Posting direct comment on buyer tweet ID {buyer_tweet_id}: {formatted_comment}")
                res = self._client.create_tweet(
                    text=formatted_comment,
                    in_reply_to_tweet_id=int(buyer_tweet_id),
                    user_auth=not getattr(self, "_is_oauth2", False)
                )
                tweet_id = str(res.data["id"])
                return {
                    "success": True,
                    "post_type": "comment",
                    "tweet_id": tweet_id,
                    "message": f"Successfully commented directly on @{buyer_username}'s tweet! (Tweet ID: {tweet_id})"
                }
            except tweepy.errors.Forbidden as f_err:
                if not self._graphql_client:
                    logger.error(f"X direct reply restricted (403: {f_err})")
                    raise RuntimeError(
                        f"X direct comment restricted (403: {f_err}). Check that your app permissions are set to 'Read and Write' in the X Developer Portal."
                    )
                logger.warning(f"Official X reply 403 ({f_err}); falling back to GraphQL cookie client.")
            except Exception as e:
                err_str = str(e)
                if self._graphql_client and ("402" in err_str or "401" in err_str or "403" in err_str or "credits" in err_str.lower()):
                    logger.warning(f"Official X reply unavailable ({err_str}); falling back to GraphQL cookie client.")
                else:
                    logger.error(f"Error commenting on X: {e}")
                    raise RuntimeError(f"Failed to comment on buyer tweet: {e}")

        # Fallback: GraphQL cookie client
        if self._graphql_client:
            return self._graphql_reply(formatted_comment, buyer_tweet_id, buyer_username)

        raise RuntimeError("No X posting client configured.")


twitter_service = TwitterService()
