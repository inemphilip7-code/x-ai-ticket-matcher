import os
import json
import random
import logging
from typing import Tuple
from models import Tweet, MatchEvaluation

logger = logging.getLogger("matcher")

BUYER_INTENT_KEYWORDS = [
    # Explicit buying intent phrases only
    "looking for ticket", "looking for tickets", "looking for tix", "need ticket", "need tickets", "need tix",
    "anyone selling ticket", "anyone selling tickets", "who has ticket", "who has tickets", "who's selling ticket",
    "who is selling ticket", "wtb ticket", "wtb tickets", "buying ticket", "buying tickets", "seeking ticket",
    "extra ticket", "spare ticket", "tickets available?", "any tickets available",
    # Spanish
    "busco entrada", "busco entradas", "busco boleta", "busco boletos", "alguien vende entrada", "compro entrada", "compro boleta",
    # French
    "cherche place", "cherche places", "cherche billet", "cherche billets", "qui vend des places", "achète place",
    # German
    "suche ticket", "suche tickets", "suche karte", "suche karten", "wer hat tickets", "kaufe ticket",
    # Italian
    "cerco biglietto", "cerco biglietti", "chi vende biglietti", "compro biglietto",
    # Portuguese
    "procuro ingresso", "procuro ingressos", "compro ingresso", "quem vende ingresso"
]

SELLER_INTENT_KEYWORDS = [
    # Explicit selling intent phrases only
    "selling ticket", "selling tickets", "selling tix", "have extra ticket", "have spare ticket",
    "tickets available", "tix available", "wts ticket", "transferrable ticket", "tickets with discount",
    # Spanish
    "vendo entrada", "vendo entradas", "vendo boleta", "vendo boletos", "entradas disponibles",
    # French
    "vends place", "vends places", "vends billet", "vends billets", "places disponibles",
    # German
    "verkaufe ticket", "verkaufe tickets", "verkaufe karte", "karten abzugeben", "tickets abzugeben",
    # Italian
    "vendo biglietto", "vendo biglietti", "biglietti disponibili",
    # Portuguese
    "vendo ingresso", "vendo ingressos", "ingressos disponíveis"
]

# Multilingual, varied comment templates (NO buyer username, NO payment methods)
MULTILINGUAL_TEMPLATES = {
    "es": [
        "@{seller} tiene entradas de sobra para {keyword} con descuento, ¡escríbele por privado!",
        "Hola, @{seller} avisó que vende entradas para {keyword} a precio rebajado si aún buscas.",
        "Échale un ojo al perfil de @{seller}, está dejando entradas de {keyword} por debajo del precio oficial.",
        "@{seller} tiene pases disponibles para {keyword} con descuento, ¡aprovecha!"
    ],
    "fr": [
        "Regarde du côté de @{seller}, il a des places en trop pour {keyword} à prix réduit !",
        "@{seller} a mentionné avoir des billets disponibles pour {keyword} avec une réduction si tu cherches toujours.",
        "Passe voir le profil de @{seller}, il cède ses places pour {keyword} sous le prix d'achat.",
        "@{seller} propose des accès pour {keyword} à tarif avantageux, n'hésite pas à le contacter !"
    ],
    "de": [
        "@{seller} hat noch überzählige Tickets für {keyword} zum Sonderpreis abzugeben, schau mal vorbei!",
        "Falls du noch suchst: @{seller} bietet Tickets für {keyword} unter dem Originalpreis an!",
        "Schau mal bei @{seller} vorbei, dort gibt es noch vergünstigte Karten für {keyword}."
    ],
    "it": [
        "@{seller} ha dei biglietti extra per {keyword} a prezzo scontato, prova a contattarlo!",
        "Se cerchi ancora, @{seller} cede biglietti per {keyword} sotto il prezzo di listino!",
        "Dai un'occhiata al profilo di @{seller}, ha ingressi per {keyword} scontati."
    ],
    "pt": [
        "@{seller} tem ingressos sobrando para {keyword} com desconto, dá uma olhada no perfil dele!",
        "Se ainda estiver procurando, @{seller} está vendendo ingressos de {keyword} abaixo do valor!",
        "Fala com @{seller}, ele tem entradas disponíveis para {keyword} com preço reduzido."
    ],
    "en": [
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
}

def detect_tweet_language(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["busco", "entrada", "entradas", "boleta", "boletos", "madrid", "barcelona", "mexico", "españa"]):
        return "es"
    if any(w in text_lower for w in ["cherche", "place", "places", "billet", "billets", "paris", "stade de france", "france"]):
        return "fr"
    if any(w in text_lower for w in ["suche", "karte", "karten", "münchen", "berlin", "deutschland", "österreich"]):
        return "de"
    if any(w in text_lower for w in ["cerco", "biglietto", "biglietti", "milano", "roma", "italia"]):
        return "it"
    if any(w in text_lower for w in ["procuro", "ingresso", "ingressos", "lisboa", "brasil", "são paulo"]):
        return "pt"
    return "en"

def clean_comment_text(text: str, seller_username: str, keyword: str, buyer_username: str = "", lang: str = "en") -> str:
    cleaned = text.strip()
    # Remove buyer username tag if model mistakenly included it
    if buyer_username:
        cleaned = cleaned.replace(f"@{buyer_username}", "").strip()
        cleaned = cleaned.lstrip(",:;- ").strip()
        
    # Ensure seller username is ALWAYS explicitly tagged
    if seller_username:
        clean_seller = seller_username.lstrip("@")
        if f"@{clean_seller}" not in cleaned:
            cleaned = f"Hey! Check with @{clean_seller}, they have {keyword} tickets available."
        
    # Remove any accidental payment terms in multiple languages
    forbidden = [
        "paypal", "cashapp", "venmo", "zelle", "bizum", "revolut", "virement", 
        "überweisung", "payment method", "goods & services", "goods and services",
        "metodo de pago", "moyen de paiement", "forma de pagamento"
    ]
    for term in forbidden:
        if term in cleaned.lower():
            templates = MULTILINGUAL_TEMPLATES.get(lang, MULTILINGUAL_TEMPLATES["en"])
            cleaned = random.choice(templates).format(seller=seller_username.lstrip("@"), keyword=keyword)
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
    
    # STRICT INTENT CHECK: If buyer doesn't have genuine buying intent, REJECT immediately!
    if not buyer_has_intent or not kw_in_buyer:
        return MatchEvaluation(
            confidence=0,
            reasoning=f"Rejected: Tweet contains '{keyword}' but lacks genuine ticket buying/selling intent.",
            suggested_reply="",
            is_match=False
        )
    
    confidence = 75
    if buyer_has_intent and seller_has_intent:
        confidence += 15
    if "2" in buyer_lower or "pair" in buyer_lower or "two" in buyer_lower:
        confidence += 5
        
    confidence = min(95, max(0, confidence))
    
    lang = detect_tweet_language(buyer.text)
    templates = MULTILINGUAL_TEMPLATES.get(lang, MULTILINGUAL_TEMPLATES["en"])
    template = random.choice(templates)
    comment_text = template.format(seller=seller.author_username, keyword=keyword)
    comment_text = clean_comment_text(comment_text, seller.author_username, keyword, buyer.author_username, lang=lang)
    
    reasoning = (
        f"[Rule-Based Intent Engine - {lang.upper()}] Confirmed genuine ticket buyer intent for '{keyword}'. "
        f"Promoting seller @{seller.author_username} with verified tag."
    )

    return MatchEvaluation(
        confidence=confidence,
        reasoning=reasoning,
        suggested_reply=comment_text,
        is_match=confidence >= 50
    )

def evaluate_pair(buyer: Tweet, seller: Tweet, keyword: str) -> Tuple[MatchEvaluation, str]:
    # Collect available Gemini API keys (Primary and Fallback)
    primary_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("AI_API_KEY", "").strip()
    fallback_key = os.getenv("GEMINI_API_KEY_FALLBACK", "").strip()
    
    keys_to_try = [k for k in [primary_key, fallback_key] if k]
    configured_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    
    if not keys_to_try:
        return evaluate_pair_rule_based(buyer, seller, keyword), "Rule-Based Fallback (No Gemini Key)"
        
    try:
        import requests
        
        system_instruction = (
            "You are a sophisticated, multilingual Google Gemini AI Ticket Matchmaker for X (Twitter).\n"
            "Analyze a tweet to determine if someone is GENUINELY trying to BUY tickets for an event, and formulate a reply promoting the seller.\n\n"
            "CRITICAL INTENT VERIFICATION RULE:\n"
            "1. STRICT BUYER INTENT: The tweet author MUST be an actual person looking to BUY, find, or get tickets for the event (e.g., 'need 2 tickets', 'who is selling', 'wtb').\n"
            "   If the tweet is just casual conversation, memes, lyrics, general excitement ('I love Coldplay'), news, or non-commercial chatter, you MUST return confidence: 0 and NO suggested reply!\n\n"
            "CRITICAL TAGGING & COMMENT RULES:\n"
            "2. YOU MUST ALWAYS TAG THE SELLER (@seller_username) IN THE COMMENT! Example: 'Reach out to @{seller}, they have extra tickets available.'\n"
            "3. DO NOT INCLUDE THE BUYER'S USERNAME (@buyer) because this is a direct in-reply-to comment under their tweet.\n"
            "4. NEVER MENTION PAYMENT METHODS (PayPal, CashApp, Venmo, Zelle, Bizum, wire, etc.).\n"
            "5. FLUENT NATIVE LANGUAGE: Match the buyer's language/locale (Spanish, French, German, Italian, Portuguese, English).\n"
            "6. Under 230 characters, friendly, natural human phrasing.\n\n"
            "Output JSON with keys:\n"
            "- 'is_buyer': boolean (true only if explicitly seeking tickets)\n"
            "- 'language': detected language code (e.g. 'en', 'es', 'fr', 'de')\n"
            "- 'confidence': integer (0-100; MUST be 0 if not genuinely seeking tickets)\n"
            "- 'reasoning': concise explanation of intent verification\n"
            "- 'suggested_reply': comment tagging @seller_username (empty string if confidence is 0)."
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
        # Dual-Key & Multi-Model High-Availability Fallback Loop
        for key_index, api_key in enumerate(keys_to_try):
            key_label = "Primary" if key_index == 0 else "Fallback"
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
                        detected_lang = str(data.get("language", "en"))
                        reasoning = str(data.get("reasoning", "Gemini verified ticket buyer intent."))
                        suggested_reply = str(data.get("suggested_reply", ""))
                        suggested_reply = clean_comment_text(suggested_reply, seller.author_username, keyword, buyer.author_username, lang=detected_lang)
                        
                        return MatchEvaluation(
                            confidence=confidence,
                            reasoning=f"[Gemini {key_label} ({model}) - {detected_lang.upper()}] {reasoning}",
                            suggested_reply=suggested_reply,
                            is_match=confidence >= 40
                        ), f"Gemini AI Active ({model} - {key_label} Key)"
                    else:
                        last_error = f"{key_label} Key / {model} HTTP {res.status_code}: {res.text[:80]}"
                except Exception as req_err:
                    last_error = f"{key_label} Key / {model} error: {req_err}"
                    continue
                
        raise RuntimeError(f"All Gemini keys & models failed. Last error: {last_error}")
        
    except Exception as e:
        logger.warning(f"Gemini evaluation error ({e}), falling back to rule-based engine.")
        fallback = evaluate_pair_rule_based(buyer, seller, keyword)
        fallback.reasoning = f"[Gemini Fallback: {str(e)[:40]}] " + fallback.reasoning
        return fallback, "Rule-Based Fallback"
