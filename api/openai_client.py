"""
Module de gestion de l'API OpenAI pour l'analyse des charges locatives.
"""
import streamlit as st
import json
import requests
from config import get_openai_api_key, DEFAULT_MODEL, FALLBACK_MODEL

def get_openai_client():
    """Vérifie simplement que la clé API est disponible."""
    try:
        api_key = get_openai_api_key()
        if not api_key:
            raise ValueError("Clé API OpenAI non disponible")
        # Retourne un simple dictionnaire au lieu d'un client
        return {"api_key": api_key}
    except Exception as e:
        st.error(f"Erreur lors de la vérification de la clé API: {str(e)}")
        raise

def send_openai_request(client, prompt, model=DEFAULT_MODEL, temperature=0.1, json_format=True, max_tokens=None):
    """
    Envoie une requête à l'API OpenAI en utilisant directement requests.
    
    Args:
        client: Dictionnaire contenant la clé API
        prompt: Le prompt à envoyer à l'API
        model: Modèle à utiliser
        temperature: Paramètre de température (0.0-1.0)
        json_format: Booléen indiquant si la réponse doit être au format JSON
        max_tokens: Nombre maximum de tokens pour la réponse
        
    Returns:
        La réponse de l'API OpenAI, ou None en cas d'erreur
    """
    try:
        api_key = client.get("api_key")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Ajouter "json" au prompt si json_format est demandé mais que "json" n'est pas déjà dans le prompt
        if json_format and "json" not in prompt.lower():
            prompt += "\n\nRéponds sous forme de JSON."
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        if json_format:
            data["response_format"] = {"type": "json_object"}
        
        if max_tokens:
            data["max_tokens"] = max_tokens
            
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            st.error(f"Erreur API ({response.status_code}): {response.text}")
            
            # Tentative avec modèle de secours si différent du modèle actuel
            if model != FALLBACK_MODEL:
                st.info(f"Tentative avec le modèle de secours {FALLBACK_MODEL}...")
                data["model"] = FALLBACK_MODEL
                fallback_response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if fallback_response.status_code == 200:
                    return fallback_response.json()["choices"][0]["message"]["content"]
                else:
                    st.error(f"Erreur avec le modèle de secours ({fallback_response.status_code}): {fallback_response.text}")
            
            return None
    
    except Exception as e:
        st.error(f"Erreur lors de la requête API: {str(e)}")
        return None

def parse_json_response(response_text, default_value=None):
    """
    Parse une réponse JSON de l'API OpenAI et gère les erreurs de parsing.
    
    Args:
        response_text: Texte de la réponse à parser
        default_value: Valeur par défaut à retourner en cas d'erreur
        
    Returns:
        Le contenu JSON parsé ou la valeur par défaut
    """
    if not response_text:
        return default_value
        
    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError as e:
        st.warning(f"Erreur lors du parsing JSON: {str(e)}")
        st.code(response_text[:500] + "..." if len(response_text) > 500 else response_text)
        return default_value
