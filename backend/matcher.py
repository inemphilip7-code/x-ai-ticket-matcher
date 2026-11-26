import os
import json
import random
import logging
from typing import Tuple
from models import Tweet, MatchEvaluation

logger = logging.getLogger("matcher")

BUYER_INTENT_KEYWORDS = [
    # English
    "looking for", "who has", "who as", "need ticket", "need tickets",
    "anyone have", "anyone selling", "wtb", "buying", "seeking", "extra ticket",
    # Spanish
    "busco entrada", "busco entradas", "busco boleta", "busco boletos", "alguien vende", "compro entrada",
    # French
    "cherche place", "cherche places", "cherche billet", "cherche billets", "qui vend",
    # German
    "suche ticket", "suche tickets", "suche karte", "suche karten", "wer hat ticket",
    # Italian
    "cerco biglietto", "cerco biglietti", "chi vende", "compro biglietto",
    # Portuguese
    "procuro ingresso", "procuro ingressos", "compro ingresso", "quem vende"
]

SELLER_INTENT_KEYWORDS = [
    # English
    "selling", "discount", "face value", "retail", "extra", "have extra", "spare", "wts", "transferrable", "available",
    # Spanish
    "vendo", "vendo entrada", "vendo boleta", "descuento", "disponible",
    # French
    "vends", "vends place", "vends billet", "réduction", "disponible",
    # German
    "verkaufe", "abzugeben", "unter originalpreis", "rabatt",
    # Italian
    "vendo", "vendo biglietto", "sconto", "disponibile",
    # Portuguese
    "vendo", "vendo ingresso", "desconto", "disponível"
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
        # Clean up any leading comma or punctuation left behind
        cleaned = cleaned.lstrip(",:;- ").strip()
        
    # Ensure seller username is tagged
    if f"@{seller_username}" not in cleaned:
        cleaned = f"@{seller_username} {cleaned}"
        
    # Remove any accidental payment terms in multiple languages
    forbidden = [
        "paypal", "cashapp", "venmo", "zelle", "bizum", "revolut", "virement", 
        "überweisung", "payment method", "goods & services", "goods and services",
        "metodo de pago", "moyen de paiement", "forma de pagamento"
    ]
    for term in forbidden:
        if term in cleaned.lower():
            templates = MULTILINGUAL_TEMPLATES.get(lang, MULTILINGUAL_TEMPLATES["en"])
            cleaned = random.choice(templates).format(seller=seller_username, keyword=keyword)
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
    
    lang = detect_tweet_language(buyer.text)
    templates = MULTILINGUAL_TEMPLATES.get(lang, MULTILINGUAL_TEMPLATES["en"])
    template = random.choice(templates)
    comment_text = template.format(seller=seller.author_username, keyword=keyword)
    comment_text = clean_comment_text(comment_text, seller.author_username, keyword, buyer.author_username, lang=lang)
    
    reasoning = (
        f"[Rule-Based Gemini Engine - {lang.upper()}] Detected buyer requesting '{keyword}' in language '{lang}'. "
        f"Seller @{seller.author_username} promotes tickets at a discount. Formulating natural multilingual reply."
    )

    return MatchEvaluation(
        confidence=confidence,
        reasoning=reasoning,
        suggested_reply=comment_text,
        is_match=confidence >= 40
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
            "Analyze a potential Buyer tweet looking for tickets, and a Seller offering tickets for an event.\n\n"
            "CRITICAL MULTILINGUAL & GEOLOCATION RULES:\n"
            "1. DETECT THE BUYER'S LANGUAGE AND EVENT LOCATION: If the buyer writes in Spanish or the event is in a Spanish-speaking city (Madrid, Barcelona, CDMX, etc.), you MUST reply in natural, fluent Spanish.\n"
            "   If French (Paris, Stade de France) -> reply in natural French.\n"
            "   If German (Berlin, Munich, etc.) -> reply in natural German.\n"
            "   If Italian (Milan, Rome) -> reply in natural Italian.\n"
            "   If Portuguese (São Paulo, Lisbon) -> reply in natural Portuguese.\n"
            "   Otherwise, reply in the exact detected language of the buyer's post!\n\n"
            "CRITICAL COMMENT SAFETY RULES:\n"
            "2. DO NOT INCLUDE THE BUYER'S USERNAME (@buyer) because this comment is published directly underneath the buyer's post as an in-reply-to comment! Do NOT write '@buyer'.\n"
            "3. Mention ONLY the seller's handle (@seller_username) and state that they are selling tickets at a discount.\n"
            "4. DO NOT INCLUDE ANY PAYMENT METHOD (NEVER mention PayPal, CashApp, Venmo, Bizum, wire, etc.).\n"
            "5. EVERY COMMENT MUST BE UNIQUE, HUMAN-LIKE, AND DIFFERENT in the detected language.\n"
            "6. Under 230 characters.\n\n"
            "Output JSON with keys:\n"
            "- 'language': detected language (e.g. 'en', 'es', 'fr', 'de')\n"
            "- 'confidence': integer (0-100)\n"
            "- 'reasoning': concise explanation of match compatibility & detected location/language\n"
            "- 'suggested_reply': human-like comment in the native language mentioning @seller_username (NO @buyer tag, NO payment methods)."
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
