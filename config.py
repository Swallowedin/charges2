"""
Configuration globale de l'application d'analyse de charges locatives commerciales.
"""
import os
import streamlit as st

# Configuration de la page Streamlit
def configure_page():
    """Configure les paramètres de la page Streamlit."""
    st.set_page_config(
        page_title="Analyseur de Charges Locatives Commerciales avec GPT-4o-mini",
        page_icon="📊",
        layout="wide"
    )

# Initialisation de l'état de la session
def initialize_session_state():
    """Initialise les variables d'état de la session Streamlit."""
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False

# Configuration de l'API OpenAI
def get_openai_api_key():
    """Récupère la clé API OpenAI depuis les secrets ou variables d'environnement."""
    api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY n'est pas défini dans les variables d'environnement")
    return api_key

# Configuration de l'API OCR.space
def get_ocr_api_key():
    """Récupère la clé API OCR.space depuis les secrets ou variables d'environnement."""
    api_key = st.secrets["OCR_API_KEY"] if "OCR_API_KEY" in st.secrets else os.getenv('OCR_API_KEY')
    if not api_key:
        # Clé par défaut (à remplacer idéalement par votre propre clé)
        return "K88510884388957"
    return api_key

# Configuration des modèles OpenAI
DEFAULT_MODEL = "gpt-4o-mini"
FALLBACK_MODEL = "gpt-4o-mini"  # Modèle de secours en cas d'erreur

# Limites de caractères pour les prompts
MAX_BAIL_CHARS = 15000
MAX_CHARGES_CHARS = 10000

# Constantes d'analyse
DEFAULT_CONFORMITY_LEVEL = 50  # Niveau de conformité par défaut
