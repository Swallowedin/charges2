"""
Utilitaires pour l'extraction de texte et l'OCR depuis différents formats de fichiers.
"""
import streamlit as st
import PyPDF2
import docx2txt
import pytesseract
import cv2
import numpy as np
import tempfile
import requests
import os
from pdf2image import convert_from_path
from config import OCR_API_KEY

def extract_text_from_image(uploaded_file):
    """
    Extraire le texte d'une image avec OCR.
    
    Args:
        uploaded_file: Fichier image téléchargé
        
    Returns:
        Le texte extrait de l'image
    """
    try:
        image_bytes = uploaded_file.getvalue()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Prétraitement de l'image
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, lang='fra')
        return text
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte de l'image: {str(e)}")
        return ""

def ocr_from_pdf_using_api(uploaded_file):
    """
    Extraire le texte d'un PDF à l'aide de l'API OCR.Space.
    
    Args:
        uploaded_file: Fichier PDF téléchargé
        
    Returns:
        Le texte extrait du PDF via OCR
    """
    try:
        # Sauvegarder le fichier uploadé sur le système de fichiers temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_pdf_path = tmp.name
        
        with open(temp_pdf_path, 'rb') as file:
            response = requests.post(
                "https://api.ocr.space/parse/image",
                files={'file': file},
                data={'apikey': OCR_API_KEY}
            )

        result = response.json()

        # Nettoyer le fichier temporaire
        try:
            os.unlink(temp_pdf_path)
        except:
            pass

        if result["OCRExitCode"] == 1:
            return result['ParsedResults'][0]['ParsedText']
        else:
            st.error("Erreur dans le traitement OCR : " + result["ErrorMessage"])
            return ""
    
    except Exception as e:
        st.error(f"Erreur lors de l'OCR du PDF: {str(e)}")
        return ""

def extract_text_from_pdf(uploaded_file):
    """
    Extraire le texte d'un fichier PDF.
    
    Args:
        uploaded_file: Fichier PDF téléchargé
        
    Returns:
        Le texte extrait du PDF
    """
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page_num in range(len(pdf_reader.pages)):
            page_text = pdf_reader.pages[page_num].extract_text()
            if page_text:
                text += page_text + "\n"

        # Si aucun texte n'est extrait, utiliser OCR
        if not text.strip():
            uploaded_file.seek(0)  # Rewind to start of file
            text = ocr_from_pdf_using_api(uploaded_file)

        return text
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte du PDF: {str(e)}")
        return ""

def extract_text_from_docx(uploaded_file):
    """
    Extraire le texte d'un fichier Word.
    
    Args:
        uploaded_file: Fichier Word téléchargé
        
    Returns:
        Le texte extrait du fichier Word
    """
    try:
        text = docx2txt.process(uploaded_file)
        return text
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte du fichier Word: {str(e)}")
        return ""

def extract_text_from_txt(uploaded_file):
    """
    Extraire le texte d'un fichier TXT.
    
    Args:
        uploaded_file: Fichier TXT téléchargé
        
    Returns:
        Le texte extrait du fichier TXT
    """
    try:
        return uploaded_file.getvalue().decode("utf-8")
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte du fichier TXT: {str(e)}")
        return ""
