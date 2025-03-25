"""
Utilitaires pour la gestion et le traitement des fichiers.
"""
import streamlit as st
from utils.ocr_utils import (
    extract_text_from_pdf, 
    extract_text_from_docx, 
    extract_text_from_txt, 
    extract_text_from_image
)

def get_file_content(uploaded_file):
    """
    Obtenir le contenu du fichier selon son type.
    
    Args:
        uploaded_file: Fichier téléchargé
        
    Returns:
        Le contenu textuel du fichier
    """
    if uploaded_file is None:
        return ""
        
    file_type = uploaded_file.type
    
    if file_type == "application/pdf":
        return extract_text_from_pdf(uploaded_file)
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(uploaded_file)
    elif file_type == "text/plain":
        return extract_text_from_txt(uploaded_file)
    elif file_type.startswith("image/"):
        return extract_text_from_image(uploaded_file)
    else:
        st.warning(f"Type de fichier non pris en charge: {file_type}")
        return ""

def process_multiple_files(uploaded_files):
    """
    Traiter plusieurs fichiers et concaténer leur contenu.
    
    Args:
        uploaded_files: Liste de fichiers téléchargés
        
    Returns:
        Le contenu textuel combiné de tous les fichiers
    """
    combined_text = ""
    
    if not uploaded_files:
        return combined_text
    
    with st.spinner("Extraction du texte des fichiers..."):
        for file in uploaded_files:
            # Obtenir le contenu du fichier
            file_content = get_file_content(file)
            if file_content:
                combined_text += f"\n\n--- Début du fichier: {file.name} ---\n\n"
                combined_text += file_content
                combined_text += f"\n\n--- Fin du fichier: {file.name} ---\n\n"
    
    return combined_text

def validate_file_input(doc1_files, doc2_files):
    """
    Valider que les fichiers nécessaires ont été fournis.
    
    Args:
        doc1_files: Fichiers pour le document 1 (bail)
        doc2_files: Fichiers pour le document 2 (charges)
        
    Returns:
        Tuple (booléen indiquant si l'entrée est valide, message d'erreur le cas échéant)
    """
    if not doc1_files or not doc2_files:
        return False, "Veuillez télécharger au moins un fichier pour le bail et un fichier pour les charges."
    
    return True, ""
