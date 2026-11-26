import os
import json
import random
import logging
from typing import Tuple
from models import Tweet, MatchEvaluation

logger = logging.getLogger("matcher")

BUYER_INTENT_KEYWORDS = [
    "looking for", "who has", "who as", "need ticket", "need tickets",
    "anyone have", "anyone selling", "wtb", "buying", "seeking"
]

SELLER_INTENT_KEYWORDS = [
    "selling", "discount", "face value", "retail", "extra", "have extra",
    "spare", "wts", "transferrable", "available"
]

# Varied, non-repetitive comments strictly mentioning ONLY the seller (NO buyer username, NO payment methods)
VARIED_COMMENT_TEMPLATES = [
    "@{seller} has spare tickets for {keyword} at a discounted rate, check out their post!",
    "@{seller} mentioned having extra {keyword} tickets available for a great price if you're still looking!",
    "Hey, looks like @{seller} is letting go of their {keyword} tickets below retail!",
    "Head over to @{seller}'s profile, they posted about selling {keyword} tickets at a discount!",
    "@{seller} has {keyword} passes available for less than face value, reach out to them!",
    "Check with @{seller}, they were offering discounted tickets for {keyword} earlier!",
    "If you still need tickets for {keyword}, @{seller} has extra seats up for grabs at a fair discount!",
    "@{seller} just posted about selling {keyword} tickets under box office price, take a look!",
    "@{seller} is selling their {keyword} tickets at a discount, thought you might be interested!",
    "@{seller} has spare {keyword} tickets they're trying to rehome at a discount, hit them up!",
    "Saw @{seller} offering {keyword} tickets below original price, worth checking with them!",
    "You might want to reach out to @{seller}, they have {keyword} tickets listed at a discount!"
]

def clean_comment_text(text: str, seller_username: str, keyword: str, buyer_username: str = "") -> str:
    cleaned = text.strip()
    # Remove buyer username tag if model mistakenly included it
    if buyer_username:
        cleaned = cleaned.replace(f"@{buyer_username}", "").strip()
        # Clean up any leading comma or punctuation left behind
        cleaned = cleaned.lstrip(",:;- ").strip()
        
    # Ensure seller username is tagged
    if f"@{seller_username}" not in cleaned:
        cleaned = f"@{seller_username} {cleaned}"
        
    # Remove any accidental payment terms
    forbidden = ["paypal", "cashapp", "venmo", "zelle", "payment method", "goods & services", "goods and services"]
    for term in forbidden:
        if term in cleaned.lower():
            cleaned = random.choice(VARIED_COMMENT_TEMPLATES).format(seller=seller_username, keyword=keyword)
            break
            
    if len(cleaned) > 238:
        cleaned = cleaned[:235] + "..."
    return cleaned

def evaluate_pair_rule_based(buyer: Tweet, seller: Tweet, keyword: str) -> MatchEvaluation:
    buyer_lower = buyer.text.lower()
    seller_lower = seller.text.lower()
    
    buyer_has_intent = any(k in buyer_lower for k in BUYER_INTENT_KEYWORDS)
    seller_has_intent = any(k in seller_lower for k in SELLER_INTENT_KEYWORDS)
    
    kw_in_buyer = keyword.lower() in buyer_lower
    kw_in_seller = keyword.lower() in seller_lower
    
    confidence = 55
    if kw_in_buyer and kw_in_seller:
        confidence += 25
    if buyer_has_intent:
        confidence += 10
    if seller_has_intent:
        confidence += 10
        
    confidence = min(96, max(30, confidence))
    
    reasoning = (
        f"[Rule-Based Gemini Engine] Verified buyer asking for '{keyword}' tickets. "
        f"Seller @{seller.author_username} offers tickets at a discount. Formulating direct comment without buyer tag."
    )
    
    template = random.choice(VARIED_COMMENT_TEMPLATES)
    comment_text = template.format(seller=seller.author_username, keyword=keyword)
    comment_text = clean_comment_text(comment_text, seller.author_username, keyword, buyer.author_username)

    return MatchEvaluation(
        confidence=confidence,
        reasoning=reasoning,
        suggested_reply=comment_text,
        is_match=confidence >= 40
    )

def evaluate_pair(buyer: Tweet, seller: Tweet, keyword: str) -> Tuple[MatchEvaluation, str]:
    # Support GEMINI_API_KEY with fallback to AI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("AI_API_KEY", "").strip()
    configured_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    
    if not api_key:
        return evaluate_pair_rule_based(buyer, seller, keyword), "Rule-Based Fallback (No Gemini Key)"
        
    try:
        import requests
        
        system_instruction = (
            "You are a helpful, human-like Google Gemini AI Ticket Matchmaker for X (Twitter).\n"
            "Analyze a potential Buyer tweet looking for tickets, and a Seller offering tickets for an event.\n"
            "CRITICAL RULES FOR THE COMMENT:\n"
            "1. DO NOT INCLUDE THE BUYER'S USERNAME (@buyer) because this comment is published directly underneath the buyer's post as an in-reply-to comment! Do NOT write '@buyer'.\n"
            "2. Mention ONLY the seller's handle (@seller_username) and state that they are selling tickets at a discount.\n"
            "3. DO NOT INCLUDE ANY PAYMENT METHOD (NEVER mention PayPal, CashApp, Venmo, wire, etc.).\n"
            "4. EVERY COMMENT MUST BE UNIQUE, HUMAN-LIKE, AND DIFFERENT: Use natural conversational phrasing (e.g. 'Saw that @seller has spare tickets...', 'Hey, looks like @seller is letting go of...', 'Take a look at @seller's post...').\n"
            "5. Under 230 characters.\n\n"
            "Output JSON with keys:\n"
            "- 'confidence': integer (0-100)\n"
            "- 'reasoning': concise explanation of match compatibility\n"
            "- 'suggested_reply': human-like comment mentioning @seller_username (NO @buyer tag, NO payment methods)."
        )
        
        user_content = (
            f"Event Keyword: {keyword}\n\n"
            f"Buyer Tweet:\n\"{buyer.text}\"\n\n"
            f"Seller Tweet (@{seller.author_username}):\n\"{seller.text}\""
        )
        
        prompt_text = f"{system_instruction}\n\n{user_content}"
        
        # Candidate models with best speed and quota reliability
        models_to_try = [configured_model]
        for alt in ["gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.1-flash-lite"]:
            if alt not in models_to_try:
                models_to_try.append(alt)
                
        last_error = ""
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.75,
                    "maxOutputTokens": 300
                }
            }
            try:
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    data = json.loads(res.json()["candidates"][0]["content"]["parts"][0]["text"])
                    confidence = int(data.get("confidence", 75))
                    confidence = max(0, min(100, confidence))
                    reasoning = str(data.get("reasoning", "Gemini verified ticket buyer intent."))
                    suggested_reply = str(data.get("suggested_reply", ""))
                    suggested_reply = clean_comment_text(suggested_reply, seller.author_username, keyword, buyer.author_username)
                    
                    return MatchEvaluation(
                        confidence=confidence,
                        reasoning=f"[Gemini AI - {model}] {reasoning}",
                        suggested_reply=suggested_reply,
                        is_match=confidence >= 40
                    ), f"Gemini AI Active ({model})"
                else:
                    last_error = f"HTTP {res.status_code}: {res.text[:80]}"
            except Exception as req_err:
                last_error = str(req_err)
                continue
                
        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")
        
    except Exception as e:
        logger.warning(f"Gemini evaluation error ({e}), falling back to rule-based engine.")
        fallback = evaluate_pair_rule_based(buyer, seller, keyword)
        fallback.reasoning = f"[Gemini Fallback: {str(e)[:40]}] " + fallback.reasoning
        return fallback, "Rule-Based Fallback"
