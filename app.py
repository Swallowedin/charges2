"""
Point d'entrée principal de l'application d'analyse des charges locatives commerciales.
"""
import streamlit as st
import os
import sys
import importlib.util

# Ajouter le répertoire courant au chemin Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Configuration de base
from config import configure_page, initialize_session_state

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
    
    # Importer les modules avec importlib (méthode plus robuste pour Streamlit Cloud)
    sidebar_path = os.path.join(current_dir, "ui", "sidebar.py")
    spec = importlib.util.spec_from_file_location("sidebar", sidebar_path)
    sidebar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sidebar)
    
    tabs_path = os.path.join(current_dir, "ui", "tabs.py")
    spec = importlib.util.spec_from_file_location("tabs", tabs_path)
    tabs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tabs)
    
    results_path = os.path.join(current_dir, "ui", "results.py")
    spec = importlib.util.spec_from_file_location("results", results_path)
    results = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(results)
    
    analysis_path = os.path.join(current_dir, "analysis", "__init__.py")
    spec = importlib.util.spec_from_file_location("analysis", analysis_path)
    analysis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analysis)
    
    # Rendu de la barre latérale
    document_type, surface = sidebar.render_sidebar()
    
    # Rendu des onglets d'entrée et récupération des données
    run_analysis, text1, text2 = tabs.render_input_tabs()
    
    # Exécution de l'analyse si nécessaire
    if run_analysis:
        st.info("📋 Analyse des charges en cours - Cette opération peut prendre une minute...")
        
        # Analyser les charges avec l'approche structurée
        analysis_result = analysis.analyze_with_openai(text1, text2, document_type)
        
        if analysis_result:
            # Enregistrer l'analyse dans l'état de la session
            st.session_state.analysis = analysis_result
            st.session_state.analysis_complete = True
    
    # Afficher les résultats si l'analyse est complète
    if st.session_state.analysis_complete:
        results.display_results(st.session_state.analysis, document_type)

if __name__ == "__main__":
    main()
