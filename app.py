"""
Application d'analyse des charges locatives commerciales (version simplifiée).
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import re
import io
from openai import OpenAI
import os

# Configuration de la page
st.set_page_config(
    page_title="Analyseur de Charges Locatives Commerciales avec GPT-4o-mini",
    page_icon="📊",
    layout="wide"
)

# Initialisation de l'état de la session
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

# Configuration de l'API OpenAI
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY n'est pas défini. Veuillez configurer cette clé API dans les secrets Streamlit.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# Interface utilisateur principale
st.title("Analyseur de Charges Locatives Commerciales avec GPT-4o-mini")
st.markdown("""
Cet outil simplifié analyse la cohérence entre les clauses de votre bail commercial et la reddition des charges.
""")

# Formulaire de saisie
with st.form("input_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Contrat de bail commercial")
        document1 = st.text_area(
            "Copiez-collez les clauses du bail commercial concernant les charges",
            height=250
        )
    
    with col2:
        st.subheader("Reddition des charges")
        document2 = st.text_area(
            "Copiez-collez le détail des charges facturées",
            height=250
        )
    
    submitted = st.form_submit_button("Analyser les charges")

# Traitement du formulaire
if submitted:
    if not document1 or not document2:
        st.error("Veuillez remplir les deux champs de texte.")
    else:
        st.info("Analyse en cours... (Cette version simplifiée ne fait pas d'analyse réelle)")
        
        # Simulation d'analyse pour démonstration
        st.success("✅ Analyse terminée")
        
        # Affichage de résultats fictifs
        st.header("Résultats de l'analyse")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Montant total des charges", "5000.00€")
        with col2:
            st.metric("Taux de conformité", "75%")
        
        st.subheader("Charges identifiées")
        data = {
            "Poste": ["Nettoyage", "Electricité", "Gardiennage", "Eau"],
            "Montant": [1200, 1800, 1500, 500],
            "Conformité": ["Conforme", "Conforme", "À vérifier", "Non conforme"]
        }
        st.dataframe(pd.DataFrame(data))
        
        # Graphique simple
        fig, ax = plt.subplots()
        ax.pie(data["Montant"], labels=data["Poste"], autopct='%1.1f%%')
        ax.axis('equal')
        st.pyplot(fig)
        
        # Recommandations
        st.subheader("Recommandations")
        st.markdown("""
        1. Vérifier les détails du poste de gardiennage
        2. Le poste eau semble non conforme aux clauses du bail
        """)
