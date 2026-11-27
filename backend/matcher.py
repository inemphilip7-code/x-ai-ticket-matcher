import os
import json
import random
import logging
from typing import Tuple, List, Dict, Any, Optional
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
    if buyer_username:
        cleaned = cleaned.replace(f"@{buyer_username}", "").strip()
        cleaned = cleaned.lstrip(",:;- ").strip()
        
    # If a seller username is provided, ensure it is mentioned naturally without destroying human phrasing
    if seller_username and seller_username.strip():
        clean_seller = seller_username.lstrip("@")
        if f"@{clean_seller}" not in cleaned:
            if clean_seller.lower() in cleaned.lower():
                cleaned = re.sub(rf"(?<!@)\b{re.escape(clean_seller)}\b", f"@{clean_seller}", cleaned, flags=re.IGNORECASE)
            elif cleaned:
                if lang == "es":
                    cleaned = f"{cleaned.rstrip('.')} — ¡escríbele a @{clean_seller}!"
                elif lang == "fr":
                    cleaned = f"{cleaned.rstrip('.')} — regarde avec @{clean_seller} !"
                elif lang == "de":
                    cleaned = f"{cleaned.rstrip('.')} — schau mal bei @{clean_seller} vorbei!"
                elif lang == "pt":
                    cleaned = f"{cleaned.rstrip('.')} — fala com @{clean_seller}!"
                elif lang == "it":
                    cleaned = f"{cleaned.rstrip('.')} — prova a sentire @{clean_seller}!"
                else:
                    cleaned = f"{cleaned.rstrip('.')} — check with @{clean_seller}!"
            else:
                if lang == "es":
                    cleaned = f"¡Hola! Si buscas entradas para {keyword}, ¡escríbele a @{clean_seller}!"
                elif lang == "fr":
                    cleaned = f"Salut ! Si tu cherches des places pour {keyword}, contacte @{clean_seller} !"
                elif lang == "de":
                    cleaned = f"Hey! Falls du noch Tickets für {keyword} suchst, frag mal @{clean_seller}!"
                elif lang == "pt":
                    cleaned = f"Oi! Se estiver procurando ingressos para {keyword}, fala com @{clean_seller}!"
                elif lang == "it":
                    cleaned = f"Ciao! Se stai cercando biglietti per {keyword}, chiedi a @{clean_seller}!"
                else:
                    cleaned = f"Hey, if you're looking for {keyword} tickets, check with @{clean_seller}!"
    else:
        if not cleaned:
            if lang == "es":
                cleaned = f"¡Hola! Si buscas entradas para {keyword}, revisa las plataformas oficiales de reventa para conseguir boletos seguros."
            elif lang == "fr":
                cleaned = f"Salut ! Si tu cherches des billets pour {keyword}, jette un œil aux bourses d'échange officielles."
            elif lang == "de":
                cleaned = f"Hey! Falls du Tickets für {keyword} suchst, schau am besten auf verifizierten Fan-Börsen vorbei."
            elif lang == "pt":
                cleaned = f"Oi! Se estiver procurando ingressos para {keyword}, veja nos canais oficiais de revenda."
            elif lang == "it":
                cleaned = f"Ciao! Se cerchi biglietti per {keyword}, controlla le piattaforme di rivendita ufficiali."
            else:
                cleaned = f"Hey! Looking for {keyword} tickets? Be sure to check verified fan exchanges for available seats."
        
    # Remove any accidental payment terms in multiple languages
    forbidden = [
        "paypal", "cashapp", "venmo", "zelle", "bizum", "revolut", "virement", 
        "überweisung", "payment method", "goods & services", "goods and services",
        "metodo de pago", "moyen de paiement", "forma de pagamento"
    ]
    for term in forbidden:
        if term in cleaned.lower():
            if seller_username and seller_username.strip():
                clean_seller = seller_username.lstrip("@")
                if lang == "es":
                    cleaned = f"¡Hola! ¿Aún buscas entradas para {keyword}? Escríbele a @{clean_seller}, tenía pases disponibles."
                elif lang == "fr":
                    cleaned = f"Salut ! Tu cherches toujours des places pour {keyword} ? Vois avec @{clean_seller}, il en avait en trop."
                elif lang == "de":
                    cleaned = f"Hey! Suchst du noch Tickets für {keyword}? Frag mal @{clean_seller}, da gab es noch welche."
                elif lang == "pt":
                    cleaned = f"Oi! Ainda procurando ingressos para {keyword}? Fala com @{clean_seller}, ele tinha sobrando."
                elif lang == "it":
                    cleaned = f"Ciao! Cerchi ancora biglietti per {keyword}? Prova a sentire @{clean_seller}, ne aveva qualcuno."
                else:
                    cleaned = f"Hey! Still searching for {keyword} tickets? Check with @{clean_seller}, they had spare passes available."
            else:
                if lang == "es":
                    cleaned = f"¿Aún buscas entradas para {keyword}? Suelen aparecer boletos de fans verificados más cerca de la fecha."
                elif lang == "fr":
                    cleaned = f"Tu cherches toujours des billets pour {keyword} ? Des places de revente officielle apparaissent souvent avant le jour J."
                else:
                    cleaned = f"Still looking for {keyword} tickets? Fan resale platforms usually have seats pop up closer to the date."
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
            "You are an expert, multilingual AI on X (Twitter). Your role is to evaluate whether a user's tweet shows GENUINE intent to buy, find, or get tickets for an event, and if so, draft an authentic, friendly, and 100% human-sounding reply.\n\n"
            "STEP 1: THINK & ANALYZE (in the 'thinking' field):\n"
            "- Carefully inspect the tweet: Is this person genuinely looking to BUY/GET tickets (e.g. 'need 2 tickets', 'who is selling', 'wtb', 'looking for tickets')?\n"
            "- If they are merely discussing music, quoting lyrics, sharing memes/news, or expressing general feelings (e.g. 'I want to see Coldplay', 'bought a shirt', 'looking for friends'), mark is_buyer: false, confidence: 0, and NO reply!\n"
            "- Reflect on the user's language, tone, and context: Are they excited? In a hurry? What specific concert/city/date do they mention?\n"
            "- Strategize how to sound like a real fellow fan on Twitter, NOT a bot or marketer. Think of a natural, helpful reply.\n\n"
            "STEP 2: NATURAL HUMAN WRITING RULES:\n"
            "1. NEVER USE CANNED OR EXACT ROBOTIC WORDS: Absolutely avoid generic formulas like 'Hey! Check with @seller, they have tickets available.' or 'Reach out to @seller for discount tickets.'\n"
            "2. SOUND LIKE A REAL PERSON: Use relaxed, natural phrasing as if you saw their tweet on your feed. Vary your tone and openings every time:\n"
            "   - 'Hey! Saw you were searching for passes to {keyword}—check out @{seller}, pretty sure they had extras!'\n"
            "   - 'If you’re still hunting for {keyword} seats, @{seller} mentioned having spare tickets earlier.'\n"
            "   - 'Hey, still looking for {keyword} tix? Drop @{seller} a quick DM, they were trying to pass theirs on.'\n"
            "   - 'Hey there! If you still need tickets for {keyword}, take a peek at @{seller}’s profile.'\n"
            "3. INTEGRATE KEYWORD & SELLER SMOOTHLY: Naturally embed the event keyword ({keyword}) and the seller handle (@{seller}) if provided. If no seller is provided, provide friendly fan-to-fan advice without tagging anyone.\n"
            "4. NEVER PREPEND THE BUYER'S HANDLE: Do not write '@buyer' because this is an in-reply-to comment directly under their tweet.\n"
            "5. NO PAYMENT TALK: Never mention payment methods (PayPal, CashApp, Venmo, Zelle, Bizum, wire transfer, etc.).\n"
            "6. FLUENT NATIVE LANGUAGE (STRICT REQUIREMENT): You MUST write 'suggested_reply' in the EXACT language of the buyer tweet:\n"
            "   - If Spanish ('busco entradas', 'alguien vende'), you MUST reply in natural, authentic Spanish (e.g. '¡Hola! Vi que buscabas entradas para {keyword}—fíjate en el perfil de @{seller}, creo que tenía de sobra.').\n"
            "   - If French ('cherche places', 'qui vend'), you MUST reply in natural French (e.g. 'Salut ! Si tu cherches toujours des places pour {keyword}, regarde avec @{seller}, il en avait en trop.').\n"
            "   - If German ('suche tickets', 'brauche karten'), you MUST reply in natural German (e.g. 'Hey! Falls du noch Karten für {keyword} suchst, schau mal bei @{seller} vorbei.').\n"
            "   - If Portuguese ('procuro ingressos'), you MUST reply in natural Portuguese (e.g. 'Oi! Se ainda estiver procurando ingressos para {keyword}, fala com o @{seller}!').\n"
            "   - If Italian ('cerco biglietti'), you MUST reply in natural Italian (e.g. 'Ciao! Se cerchi ancora biglietti per {keyword}, senti @{seller}!').\n"
            "   - NEVER reply in English if the buyer tweeted in another language! Match their dialect, language, and slang perfectly.\n"
            "7. LENGTH: Keep it concise, natural, and under 220 characters.\n\n"
            "Output valid JSON with keys:\n"
            "- 'thinking': string (your internal thoughts on intent analysis, tone, and human phrasing strategy)\n"
            "- 'is_buyer': boolean (true only if explicitly seeking tickets)\n"
            "- 'language': string (e.g. 'en', 'es', 'fr', 'de')\n"
            "- 'confidence': integer (0-100; MUST be 0 if not genuinely seeking tickets)\n"
            "- 'reasoning': concise explanation of intent\n"
            "- 'suggested_reply': unique, human-sounding comment (empty string if confidence is 0)."
        )
        
        seller_label = f"@{seller.author_username}" if seller.author_username else "General Ticket Marketplace"
        user_content = (
            f"Event Keyword: {keyword}\n\n"
            f"Buyer Tweet:\n\"{buyer.text}\"\n\n"
            f"Seller Information ({seller_label}):\n\"{seller.text}\""
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
                        "temperature": 0.8,
                        "maxOutputTokens": 600
                    }
                }
                try:
                    res = requests.post(url, json=payload, timeout=12)
                    if res.status_code == 200:
                        data = json.loads(res.json()["candidates"][0]["content"]["parts"][0]["text"])
                        confidence = int(data.get("confidence", 75))
                        confidence = max(0, min(100, confidence))
                        detected_lang = str(data.get("language", "en"))
                        thinking = str(data.get("thinking", "")).strip()
                        reasoning = str(data.get("reasoning", "Gemini verified ticket buyer intent."))
                        summary_reasoning = f"{reasoning} (AI Thought: {thinking[:120]}...)" if thinking else reasoning
                        suggested_reply = str(data.get("suggested_reply", ""))
                        suggested_reply = clean_comment_text(suggested_reply, seller.author_username, keyword, buyer.author_username, lang=detected_lang)
                        
                        return MatchEvaluation(
                            confidence=confidence,
                            reasoning=f"[Gemini {key_label} ({model}) - {detected_lang.upper()}] {summary_reasoning}",
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


def extract_trending_events_from_tweets(demand_tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze real-time ticket demand tweets from X using Gemini AI to extract
    trending concert, festival, or sports event keywords currently in high demand.
    """
    if not demand_tweets:
        return []

    import requests

    primary_key = get_setting("gemini_api_key", os.getenv("GEMINI_API_KEY", "")).strip()
    fallback_key = get_setting("gemini_api_key_fallback", os.getenv("GEMINI_API_KEY_FALLBACK", "")).strip()
    keys_to_try = [k for k in [primary_key, fallback_key] if k]
    if not keys_to_try:
        return []

    configured_model = get_setting("gemini_model", os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")).strip()

    sample_texts = [f"Tweet {i+1}: \"{t.get('text', '')}\"" for i, t in enumerate(demand_tweets[:12])]
    tweets_block = "\n".join(sample_texts)

    prompt = (
        "You are an AI Ticket Trend Hunter. Analyze these real-time buyer demand tweets from X.\n"
        "Extract up to 6 of the most specific, high-demand events (concerts, tours, artists, sports matches, festivals) that people are urgently seeking tickets for right now.\n"
        "Extract the actual clean event or artist name (e.g. 'Moto GP Valencia', 'Liverpool vs Everton', 'Chelsea', 'Fetty Wap').\n\n"
        f"Real-Time Demand Tweets on X:\n{tweets_block}\n\n"
        "Respond ONLY with valid JSON array of objects:\n"
        "[\n"
        "  {\"keyword\": \"Clean Event or Artist Name\", \"category\": \"concert|sports|festival\", \"language\": \"en|es|fr|de|pt\", \"summary\": \"Brief note on demand\"}\n"
        "]"
    )

    models_to_try = [configured_model, "gemini-3.5-flash-lite", "gemini-flash-latest"]
    for api_key in keys_to_try:
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            try:
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    text_out = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # Strip markdown codeblocks if model included them
                    if text_out.startswith("```"):
                        text_out = re.sub(r"^```(?:json)?\s*|\s*```$", "", text_out, flags=re.MULTILINE).strip()
                    data = json.loads(text_out)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                logger.warning(f"Error in extract_trending_events_from_tweets ({model}): {e}")
                continue

    return []
