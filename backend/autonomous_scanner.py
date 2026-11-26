import asyncio
import logging
import os
from datetime import datetime
from typing import Optional
from database import (
    get_monitored_keywords, pair_already_processed, insert_match, 
    log_activity, record_scan, get_setting, set_setting
)
from models import Tweet
from twitter_service import twitter_service
from matcher import evaluate_pair

logger = logging.getLogger("autonomous_scanner")

class AutonomousScanner:
    def __init__(self):
        self.is_running = get_setting("auto_scan_enabled", os.getenv("AUTO_SCAN_ENABLED", "true")).lower() in ("true", "1", "yes")
        self.interval_seconds = int(get_setting("auto_scan_interval_seconds", os.getenv("AUTO_SCAN_INTERVAL_SECONDS", "1500")))
        self.confidence_threshold = int(get_setting("auto_post_confidence_threshold", os.getenv("AUTO_POST_CONFIDENCE_THRESHOLD", "70")))
        self._task: Optional[asyncio.Task] = None

    def start(self):
        self.is_running = True
        set_setting("auto_scan_enabled", "true")
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._scan_loop())
            mins = self.interval_seconds // 60
            log_activity(
                "info",
                "Autonomous X Scanner & Auto-Commenter started.",
                f"Sweep Interval: Every {mins} mins ({self.interval_seconds}s), Auto-comment threshold: {self.confidence_threshold}%"
            )

    def stop(self):
        self.is_running = False
        set_setting("auto_scan_enabled", "false")
        if self._task and not self._task.done():
            self._task.cancel()
        log_activity("info", "Autonomous X Scanner paused.")

    def set_config(self, interval: Optional[int] = None, threshold: Optional[int] = None):
        if interval and interval >= 15:
            self.interval_seconds = interval
            set_setting("auto_scan_interval_seconds", str(interval))
        if threshold and 0 <= threshold <= 100:
            self.confidence_threshold = threshold
            set_setting("auto_post_confidence_threshold", str(threshold))
        mins = self.interval_seconds // 60
        log_activity("info", f"Scanner settings updated & saved: interval={mins}m, threshold={self.confidence_threshold}%")

    async def run_scan_cycle_for_keyword(self, keyword: str):
        if not twitter_service.is_configured():
            log_activity("warning", "X credentials not ready. Click 'Connect with 𝕏' or supply keys in Settings to start live scanning.")
            return

        # Check for configured seller username (defaults to xzavior if not set)
        target_seller = get_setting("seller_username", os.getenv("DEFAULT_SELLER_USERNAME", "xzavior")).strip().lstrip("@")
        if not target_seller:
            target_seller = "xzavior"

        log_activity("info", f"Sweeping live X for ticket requests: '{keyword}'...")
        
        try:
            buyers = twitter_service.search_buyers(keyword, count=10)
        except Exception as e:
            log_activity("error", f"Live X search error for '{keyword}': {e}")
            return

        if not buyers:
            log_activity("info", f"No new buyer tweets found on X for '{keyword}'.")
            record_scan(keyword, 0, 0, 0, 0)
            return

        # If a designated seller username is set, we pair every buyer with this seller!
        sellers = []
        if target_seller:
            log_activity("info", f"Found {len(buyers)} buyers for '{keyword}'. Pairing with configured seller @{target_seller}.")
            # Synthesize seller representation for matching
            for i, b in enumerate(buyers):
                sellers.append(Tweet(
                    id=f"target_seller_{target_seller}_{b.id}",
                    text=f"Selling verified tickets for {keyword} at a discount rate! Instant transfer.",
                    author_username=target_seller,
                    author_name=target_seller,
                    created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    role="seller"
                ))
        else:
            try:
                sellers = twitter_service.search_sellers(keyword, count=10)
            except Exception as e:
                log_activity("error", f"Error searching sellers for '{keyword}': {e}")
                sellers = []

        if not sellers:
            log_activity("info", f"Discovered {len(buyers)} buyers for '{keyword}', but no sellers found.")
            record_scan(keyword, len(buyers), 0, 0, 0)
            return

        matches_created = 0
        auto_commented_count = 0

        paired_count = min(len(buyers), len(sellers))
        for i in range(paired_count):
            buyer = buyers[i]
            seller = sellers[i]

            if pair_already_processed(buyer.id, seller.id):
                continue

            evaluation, ai_mode = evaluate_pair(buyer, seller, keyword)
            
            status = "pending"
            post_type = "none"
            posted_tweet_id = None
            posted_at = None
            suggested_reply = evaluation.suggested_reply

            # Automatic Direct Commenting without human approval when confidence >= threshold
            if evaluation.confidence >= self.confidence_threshold:
                try:
                    log_activity(
                        "info",
                        f"Target match ({evaluation.confidence}%): Auto-commenting directly on @{buyer.author_username}'s tweet...",
                        f"Promoting seller @{seller.author_username}"
                    )
                    res = twitter_service.post_comment_on_buyer_tweet(
                        comment_text=suggested_reply,
                        buyer_tweet_id=buyer.id,
                        buyer_username=buyer.author_username,
                        seller_username=seller.author_username,
                        event_keyword=keyword
                    )
                    if res.get("success"):
                        status = "auto_posted"
                        post_type = "comment"
                        posted_tweet_id = res.get("tweet_id")
                        posted_at = datetime.utcnow().isoformat()
                        auto_commented_count += 1
                        
                        log_activity(
                            "success",
                            f"AUTO-COMMENTED ON X: Tweet ID {posted_tweet_id}",
                            f"Commented to @{buyer.author_username} recommending @{seller.author_username}"
                        )
                except Exception as e:
                    status = "failed"
                    log_activity("error", f"Auto-comment failed on X for @{buyer.author_username}: {e}")
            else:
                log_activity(
                    "info",
                    f"Match below threshold ({evaluation.confidence}% < {self.confidence_threshold}%). Saved as pending.",
                    f"Buyer: @{buyer.author_username} | Seller: @{seller.author_username}"
                )

            # Insert into DB
            match_id = insert_match(
                event_keyword=keyword,
                buyer_tweet_id=buyer.id,
                buyer_username=buyer.author_username,
                buyer_text=buyer.text,
                buyer_timestamp=buyer.created_at,
                seller_tweet_id=seller.id,
                seller_username=seller.author_username,
                seller_text=seller.text,
                seller_timestamp=seller.created_at,
                confidence_score=evaluation.confidence,
                ai_reasoning=evaluation.reasoning,
                suggested_reply=suggested_reply,
                status=status,
                post_type=post_type,
                posted_tweet_id=posted_tweet_id,
                posted_at=posted_at
            )
            if match_id:
                matches_created += 1

        record_scan(keyword, len(buyers), len(sellers), matches_created, auto_commented_count)

    async def _scan_loop(self):
        while self.is_running:
            try:
                monitored = get_monitored_keywords()
                active_keywords = [k["keyword"] for k in monitored if k.get("is_active", 1)]
                
                for kw in active_keywords:
                    if not self.is_running:
                        break
                    await self.run_scan_cycle_for_keyword(kw)
                    await asyncio.sleep(4)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in autonomous scanner cycle: {e}")

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

autonomous_scanner = AutonomousScanner()
