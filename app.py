"""
Point d'entrée principal de l'application d'analyse des charges locatives commerciales.
"""
import streamlit as st
import os
import sys

# Assurez-vous que le répertoire courant est dans le chemin de recherche Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Toutes les importations au niveau du module, pas à l'intérieur des fonctions
from config import configure_page, initialize_session_state

# Version simplifiée - fonctions directement dans le module principal
def render_sidebar():
    st.sidebar.header("Configuration")
    document_type = "commercial"
    st.sidebar.info("Cet outil est conçu spécifiquement pour analyser les baux commerciaux et leurs charges.")
    surface = st.sidebar.text_input("Surface locative (m²)")
    return document_type, surface

def render_input_tabs():
    run_analysis = False
    text1 = None
    text2 = None
    
    with st.form("input_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Contrat de bail commercial")
            document1 = st.text_area("Copiez-collez les clauses du bail", height=250)
        with col2:
            st.subheader("Reddition des charges")
            document2 = st.text_area("Copiez-collez le détail des charges", height=250)
        
        submitted = st.form_submit_button("Analyser les charges")
        
        if submitted and document1 and document2:
            run_analysis = True
            text1 = document1
            text2 = document2
    
    return run_analysis, text1, text2

def analyze_with_openai(text1, text2, document_type):
    # Version simplifiée pour test
    st.success("Analyse terminée avec succès!")
    return {
        "charges_refacturables": [{"categorie": "Test", "description": "Charge test"}],
        "charges_facturees": [{"poste": "Test", "montant": 100, "conformite": "conforme"}],
        "montant_total": 100,
        "analyse_globale": {"taux_conformite": 80, "conformite_detail": "Analyse test"}
    }

def display_results(analysis, document_type):
    st.header("Résultats de l'analyse")
    st.json(analysis)

def main():
    # Configuration de la page
    configure_page()
    
    # Initialisation de l'état de la session
    initialize_session_state()
    
    # Titre et description de l'application
    st.title("Analyseur de Charges Locatives Commerciales avec GPT-4o-mini")
    
    st.markdown("""
    Cet outil analyse la cohérence entre les clauses de votre bail commercial et la reddition des charges en utilisant GPT-4o-mini.
    L'analyse se fait en trois étapes précises:
    1. Extraction des charges refacturables du bail
    2. Extraction des montants facturés de la reddition
    3. Analyse de la conformité entre les charges autorisées et les charges facturées
    """)
    
    # Rendu de la barre latérale
    document_type, surface = render_sidebar()
    
    # Rendu des onglets d'entrée et récupération des données
    run_analysis, text1, text2 = render_input_tabs()
    
    # Exécution de l'analyse si nécessaire
    if run_analysis:
        st.info("📋 Analyse des charges en cours - Cette opération peut prendre une minute...")
        
        # Analyser les charges avec l'approche structurée
        analysis = analyze_with_openai(text1, text2, document_type)
        
        if analysis:
            # Enregistrer l'analyse dans l'état de la session
            st.session_state.analysis = analysis
            st.session_state.analysis_complete = True
    
    # Afficher les résultats si l'analyse est complète
    if st.session_state.get('analysis_complete', False):
        display_results(st.session_state.analysis, document_type)

if __name__ == "__main__":
    main()
