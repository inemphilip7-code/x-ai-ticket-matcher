import os
import logging
from typing import List, Dict, Any, Optional

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

class TwitterService:
    def __init__(self):
        self.client_id = os.getenv("TWITTER_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("TWITTER_CLIENT_SECRET", "").strip()
        self.api_key = os.getenv("TWITTER_API_KEY", "").strip()
        self.api_secret = os.getenv("TWITTER_API_SECRET", "").strip()
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
        self.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
        self._client: Optional[tweepy.Client] = None
        self._init_client()

    def _init_client(self):
        if (self.api_key and self.access_token) or self.bearer_token or self.access_token:
            try:
                self._client = tweepy.Client(
                    bearer_token=self.bearer_token or None,
                    consumer_key=self.api_key or None,
                    consumer_secret=self.api_secret or None,
                    access_token=self.access_token or None,
                    access_token_secret=self.access_token_secret or None,
                    wait_on_rate_limit=True
                )
                logger.info("Live Tweepy Client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Tweepy Client: {e}")
                self._client = None
        else:
            self._client = None

    def reload_credentials(
        self,
        api_key: str = "",
        api_secret: str = "",
        access_token: str = "",
        access_token_secret: str = "",
        bearer_token: str = "",
        client_id: str = "",
        client_secret: str = ""
    ):
        if api_key: self.api_key = api_key.strip()
        if api_secret: self.api_secret = api_secret.strip()
        if access_token: self.access_token = access_token.strip()
        if access_token_secret: self.access_token_secret = access_token_secret.strip()
        if bearer_token: self.bearer_token = bearer_token.strip()
        if client_id: self.client_id = client_id.strip()
        if client_secret: self.client_secret = client_secret.strip()
        self._init_client()

    def is_configured(self) -> bool:
        return self._client is not None and bool(self.access_token or self.bearer_token)

    def get_credential_status(self) -> Dict[str, Any]:
        return {
            "has_bearer_token": bool(self.bearer_token),
            "has_client_id": bool(self.client_id),
            "has_api_key": bool(self.api_key),
            "has_api_secret": bool(self.api_secret),
            "has_access_token": bool(self.access_token),
            "has_access_token_secret": bool(self.access_token_secret),
            "can_search": bool(self.bearer_token or self.api_key or self.access_token),
            "can_comment": bool(self.access_token)
        }

    # --- Dual OAuth Connect: OAuth 2.0 PKCE or OAuth 1.0a ---
    def generate_oauth_url(self, callback_url: str) -> Dict[str, str]:
        # 1. Prefer OAuth 2.0 PKCE if client_id is available (Standard on new X Developer accounts)
        if self.client_id:
            handler = tweepy.OAuth2UserHandler(
                client_id=self.client_id,
                redirect_uri=callback_url,
                scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
                client_secret=self.client_secret or None
            )
            auth_url = handler.get_authorization_url()
            # Cache handler by state parameter
            state = handler.new_state if hasattr(handler, 'new_state') else "default"
            _oauth2_handlers[state] = handler
            _oauth2_handlers["latest"] = handler
            return {"auth_url": auth_url, "type": "oauth2"}

        # 2. Or OAuth 1.0a if API Key & Secret are provided
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

    def exchange_oauth2_callback(self, full_redirect_url: str) -> Dict[str, str]:
        handler = _oauth2_handlers.get("latest")
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

    # --- Live Search with Targeted Intent Phrases ---
    def search_buyers(self, keyword: str, count: int = 10) -> List[Tweet]:
        if not self._client:
            raise RuntimeError("X API client not configured. Connect your X account or enter keys in Settings.")

        query = (
            f'("{keyword}") '
            f'("looking for ticket" OR "looking for tickets" OR "who has ticket" OR "who has tickets" OR '
            f'"who as ticket" OR "who has extra" OR "need ticket" OR "need tickets" OR "anyone selling" OR "wtb ticket") '
            f'-is:retweet -is:reply lang:en'
        )
        try:
            logger.info(f"Searching live X for buyers: {query}")
            response = self._client.search_recent_tweets(
                query=query,
                max_results=min(max(count, 10), 50),
                tweet_fields=["created_at", "author_id", "text"],
                expansions=["author_id"],
                user_fields=["username", "name"]
            )
            if not response or not response.data:
                return []
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
        except tweepy.errors.TweepyException as te:
            logger.error(f"Tweepy buyer search error: {te}")
            raise RuntimeError(f"X API Search Error: {te}")
        except Exception as e:
            logger.error(f"Unexpected error searching X buyers: {e}")
            raise RuntimeError(f"Failed to query X for buyers: {e}")

    def search_sellers(self, keyword: str, count: int = 10) -> List[Tweet]:
        if not self._client:
            raise RuntimeError("X API client not configured. Connect your X account or enter keys in Settings.")

        query = (
            f'("{keyword}") '
            f'("selling ticket" OR "selling tickets" OR "selling at discount" OR "extra ticket" OR "extra tickets" OR '
            f'"have extra" OR "wts ticket" OR "tickets available") '
            f'-is:retweet -is:reply lang:en'
        )
        try:
            logger.info(f"Searching live X for sellers: {query}")
            response = self._client.search_recent_tweets(
                query=query,
                max_results=min(max(count, 10), 50),
                tweet_fields=["created_at", "author_id", "text"],
                expansions=["author_id"],
                user_fields=["username", "name"]
            )
            if not response or not response.data:
                return []
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
        except tweepy.errors.TweepyException as te:
            logger.error(f"Tweepy seller search error: {te}")
            raise RuntimeError(f"X API Search Error: {te}")
        except Exception as e:
            logger.error(f"Unexpected error searching X sellers: {e}")
            raise RuntimeError(f"Failed to query X for sellers: {e}")

    # --- Comment Directly on Buyer's Tweet ---
    def post_comment_on_buyer_tweet(
        self,
        comment_text: str,
        buyer_tweet_id: str,
        buyer_username: str,
        seller_username: str,
        event_keyword: str
    ) -> Dict[str, Any]:
        if not self._client or not self.access_token:
            raise RuntimeError(
                "X commenting requires an authorized User Account. Please click 'Connect with 𝕏' or paste your User Access Token in Settings."
            )

        # Do NOT include buyer username in text because it's an in-reply-to comment directly under their post
        formatted_comment = comment_text.strip()
        if f"@{buyer_username}" in formatted_comment:
            formatted_comment = formatted_comment.replace(f"@{buyer_username}", "").strip()
            formatted_comment = formatted_comment.lstrip(",:;- ").strip()
            
        if len(formatted_comment) > 275:
            formatted_comment = formatted_comment[:270] + "..."

        try:
            logger.info(f"Posting direct comment on buyer tweet ID {buyer_tweet_id}: {formatted_comment}")
            res = self._client.create_tweet(
                text=formatted_comment,
                in_reply_to_tweet_id=int(buyer_tweet_id)
            )
            tweet_id = str(res.data["id"])
            return {
                "success": True,
                "post_type": "comment",
                "tweet_id": tweet_id,
                "message": f"Successfully commented directly on @{buyer_username}'s tweet! (Tweet ID: {tweet_id})"
            }
        except tweepy.errors.Forbidden as f_err:
            logger.error(f"X direct reply restricted (403: {f_err})")
            raise RuntimeError(
                f"X direct comment restricted (403: {f_err}). Check that your app permissions are set to 'Read and Write' in the X Developer Portal."
            )
        except Exception as e:
            logger.error(f"Error commenting on X: {e}")
            raise RuntimeError(f"Failed to comment on buyer tweet: {e}")

twitter_service = TwitterService()
