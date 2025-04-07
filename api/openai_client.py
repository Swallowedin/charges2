"""
Module de gestion de l'API OpenAI pour l'analyse des charges locatives.
"""
import streamlit as st
from openai import OpenAI
import json
from config import get_openai_api_key, DEFAULT_MODEL, FALLBACK_MODEL

def get_openai_client():
    """Initialise et retourne un client OpenAI."""
    try:
        # Essayer d'abord sans proxies
        client = OpenAI(api_key=get_openai_api_key())
        return client
    except TypeError as e:
        # Si l'erreur concerne 'proxies', ignorer ce paramètre
        if "proxies" in str(e):
            st.warning("Ignoré l'erreur de paramètre 'proxies'")
            # Tenter une autre approche d'initialisation
            try:
                # Méthode alternative d'initialisation sans paramètres optionnels
                from openai import OpenAI
                client = OpenAI(api_key=get_openai_api_key())
                return client
            except Exception as inner_e:
                st.error(f"Erreur lors de la seconde tentative d'initialisation: {str(inner_e)}")
                raise
        else:
            # Autre type d'erreur
            st.error(f"Erreur lors de l'initialisation du client OpenAI: {str(e)}")
            raise
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation du client OpenAI: {str(e)}")
        raise

def send_openai_request(client, prompt, model=DEFAULT_MODEL, temperature=0.1, json_format=True, max_tokens=None):
    """
    Envoie une requête à l'API OpenAI et gère les erreurs potentielles.
    
    Args:
        client: Client OpenAI initialisé
        prompt: Le prompt à envoyer à l'API
        model: Modèle à utiliser (par défaut: gpt-4o-mini)
        temperature: Paramètre de température (0.0-1.0)
        json_format: Booléen indiquant si la réponse doit être au format JSON
        max_tokens: Nombre maximum de tokens pour la réponse
        
    Returns:
        La réponse de l'API OpenAI, ou None en cas d'erreur
    """
    try:
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "seed": 42
        }
        
        if json_format:
            kwargs["response_format"] = {"type": "json_object"}
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    except Exception as e:
        st.warning(f"Erreur API OpenAI ({model}): {str(e)}")
        
        # Tentative avec modèle de secours si différent du modèle actuel
        if model != FALLBACK_MODEL:
            st.info(f"Tentative avec le modèle de secours {FALLBACK_MODEL}...")
            try:
                kwargs["model"] = FALLBACK_MODEL
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as fallback_error:
                st.error(f"Erreur avec le modèle de secours: {str(fallback_error)}")
                
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
