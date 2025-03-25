"""
Point d'entrée principal de l'application d'analyse des charges locatives commerciales.
"""
import streamlit as st
import os
import sys

# Ajout du répertoire courant au chemin Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration de base
from config import configure_page, initialize_session_state

# Importer les fonctions nécessaires directement
def main():
    """Fonction principale de l'application."""
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
    
    # Importations à l'intérieur de la fonction pour éviter les problèmes d'importation circulaire
    from ui.sidebar import render_sidebar
    from ui.tabs import render_input_tabs
    from ui.results import display_results
    from analysis import analyze_with_openai
    
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
    if st.session_state.analysis_complete:
        display_results(st.session_state.analysis, document_type)

if __name__ == "__main__":
    main()
