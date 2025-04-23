"""
Module amélioré pour l'extraction de texte et l'OCR depuis différents formats de fichiers.
Focus sur les documents de faible qualité et tableaux.
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
import io
from PIL import Image
from config import get_ocr_api_key

def preprocess_image_for_ocr(img):
    """
    Prétraitement avancé d'une image pour améliorer les résultats OCR.
    
    Args:
        img: Image OpenCV à prétraiter
        
    Returns:
        Image prétraitée
    """
    # Conversion en niveaux de gris
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Appliquer une légère réduction de bruit
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Augmenter le contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_enhanced = clahe.apply(denoised)
    
    # Binarisation avec Otsu pour une meilleure segmentation
    _, thresh = cv2.threshold(contrast_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Dilatation légère pour renforcer les caractères
    kernel = np.ones((1, 1), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    
    return dilated

def extract_text_with_multiple_methods(img):
    """
    Essaie plusieurs méthodes d'OCR et retourne le meilleur résultat.
    
    Args:
        img: Image à analyser
        
    Returns:
        Meilleur texte extrait
    """
    results = []
    
    # Méthode 1: Image originale
    try:
        text1 = pytesseract.image_to_string(img, lang='fra', config='--psm 6')
        results.append((text1, len(text1.strip())))
    except Exception as e:
        st.warning(f"Erreur OCR méthode 1: {str(e)}")
    
    # Méthode 2: Prétraitement avancé
    try:
        processed = preprocess_image_for_ocr(img)
        text2 = pytesseract.image_to_string(processed, lang='fra', config='--psm 6')
        results.append((text2, len(text2.strip())))
    except Exception as e:
        st.warning(f"Erreur OCR méthode 2: {str(e)}")
    
    # Méthode 3: Binarisation simple
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        text3 = pytesseract.image_to_string(binary, lang='fra', config='--psm 6')
        results.append((text3, len(text3.strip())))
    except Exception as e:
        st.warning(f"Erreur OCR méthode 3: {str(e)}")
    
    # Méthode 4: Orientation spécifique pour les tableaux
    try:
        text4 = pytesseract.image_to_string(img, lang='fra', config='--psm 4')
        results.append((text4, len(text4.strip())))
    except Exception as e:
        st.warning(f"Erreur OCR méthode 4: {str(e)}")
    
    # Retourner le résultat avec le plus de texte
    if results:
        results.sort(key=lambda x: x[1], reverse=True)
        return results[0][0]
    
    return ""

def extract_text_from_image(uploaded_file):
    """
    Extraire le texte d'une image avec OCR amélioré.
    
    Args:
        uploaded_file: Fichier image téléchargé
        
    Returns:
        Le texte extrait de l'image
    """
    try:
        image_bytes = uploaded_file.getvalue()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Utiliser la méthode multiple
        return extract_text_with_multiple_methods(img)
    
    except Exception as e:
        st.warning(f"Erreur lors de l'extraction du texte de l'image: {str(e)}")
        # Tentative de secours avec l'API OCR
        try:
            return ocr_from_image_using_api(uploaded_file)
        except Exception as ocr_e:
            st.warning(f"Erreur API OCR: {str(ocr_e)}")
            return ""

def extract_text_from_pdf(uploaded_file):
    """
    Extraire le texte d'un fichier PDF avec une approche hybride.
    
    Args:
        uploaded_file: Fichier PDF téléchargé
        
    Returns:
        Le texte extrait du PDF
    """
    text = ""
    
    # Essayer d'abord l'extraction native de PyPDF2
    try:
        uploaded_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page_num in range(len(pdf_reader.pages)):
            page_text = pdf_reader.pages[page_num].extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        st.warning(f"Extraction native du PDF non réussie: {str(e)}")
    
    # Si peu ou pas de texte extrait, essayer l'OCR
    if len(text.strip()) < 100:  # Seuil arbitraire pour déterminer si l'extraction est insuffisante
        st.info("Extraction de texte limitée, utilisation de l'OCR...")
        
        try:
            # Utiliser directement l'API OCR external comme méthode fiable
            uploaded_file.seek(0)
            text = ocr_from_pdf_using_api(uploaded_file)
            if text:
                return text
                
        except Exception as e:
            st.warning(f"Erreur lors de l'OCR du PDF via API: {str(e)}")
            
            # Essayer avec pdf2image mais gérer gracieusement les erreurs
            try:
                # Import conditionnel pour éviter les erreurs d'importation
                from pdf2image import convert_from_bytes
                
                uploaded_file.seek(0)
                pdf_bytes = uploaded_file.getvalue()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(pdf_bytes)
                    temp_pdf_path = tmp.name
                
                # Augmenter le DPI pour une meilleure qualité
                images = convert_from_bytes(pdf_bytes, dpi=300)
                
                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_pdf_path)
                except:
                    pass
                
                # OCR sur chaque page
                page_texts = []
                for i, img in enumerate(images):
                    with st.spinner(f"OCR sur la page {i+1}/{len(images)}..."):
                        # Convertir PIL Image en format OpenCV
                        open_cv_image = np.array(img)
                        # RGB vers BGR (format OpenCV)
                        open_cv_image = open_cv_image[:, :, ::-1].copy()
                        
                        # Extraire le texte avec notre méthode multiple
                        page_text = extract_text_with_multiple_methods(open_cv_image)
                        page_texts.append(page_text)
                
                # Si on a des résultats d'OCR, les utiliser
                if any(page_texts):
                    text = "\n\n".join(page_texts)
                
            except ImportError:
                st.warning("pdf2image ou poppler n'est pas correctement installé. Utilisation de l'API OCR.")
                
            except Exception as pdf2image_error:
                st.warning(f"Erreur lors de l'utilisation de pdf2image: {str(pdf2image_error)}")

    return text

def ocr_from_image_using_api(uploaded_file):
    """
    Utilise l'API OCR.space pour extraire le texte d'une image.
    
    Args:
        uploaded_file: Fichier image téléchargé
        
    Returns:
        Le texte extrait via l'API OCR
    """
    try:
        OCR_API_KEY = get_ocr_api_key()
        
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={'file': uploaded_file.getvalue()},
            data={
                'apikey': OCR_API_KEY,
                'language': 'fre',
                'isTable': True,
                'OCREngine': 2  # Utiliser le moteur OCR le plus précis
            }
        )
        
        result = response.json()
        
        if result["OCRExitCode"] == 1:
            parsed_text = result['ParsedResults'][0]['ParsedText']
            # Fix pour l'erreur "can only concatenate str (not 'list') to str"
            if isinstance(parsed_text, list):
                parsed_text = ''.join(parsed_text)
            return parsed_text
        else:
            st.warning("Erreur dans le traitement OCR API: " + result.get("ErrorMessage", "Erreur inconnue"))
            return ""
    
    except Exception as e:
        st.warning(f"Erreur lors de l'utilisation de l'API OCR: {str(e)}")
        return ""

def ocr_from_pdf_using_api(uploaded_file):
    """
    Extraire le texte d'un PDF à l'aide de l'API OCR.Space avec options améliorées.
    
    Args:
        uploaded_file: Fichier PDF téléchargé
        
    Returns:
        Le texte extrait du PDF via OCR
    """
    try:
        OCR_API_KEY = get_ocr_api_key()
        
        # Sauvegarder le fichier uploadé sur le système de fichiers temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_file.getvalue())
            temp_pdf_path = tmp.name
        
        with open(temp_pdf_path, 'rb') as file:
            response = requests.post(
                "https://api.ocr.space/parse/image",
                files={'file': file},
                data={
                    'apikey': OCR_API_KEY,
                    'language': 'fre',
                    'isTable': True,
                    'OCREngine': 2,  # Moteur plus précis
                    'scale': True,   # Redimensionnement automatique
                    'detectOrientation': True
                }
            )

        # Nettoyer le fichier temporaire
        try:
            os.unlink(temp_pdf_path)
        except:
            pass

        result = response.json()

        if result["OCRExitCode"] == 1:
            parsed_text = result['ParsedResults'][0]['ParsedText']
            # Fix pour l'erreur "can only concatenate str (not 'list') to str"
            if isinstance(parsed_text, list):
                parsed_text = ''.join(parsed_text)
            return parsed_text
        else:
            st.warning("Erreur dans le traitement OCR API: " + result.get("ErrorMessage", "Erreur inconnue"))
            return ""
    
    except Exception as e:
        st.warning(f"Erreur lors de l'OCR du PDF via API: {str(e)}")
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
        st.warning(f"Erreur lors de l'extraction du texte du fichier Word: {str(e)}")
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
        st.warning(f"Erreur lors de l'extraction du texte du fichier TXT: {str(e)}")
        return ""

def process_file_with_fallback(uploaded_file):
    """
    Traite un fichier avec plusieurs méthodes de secours.
    
    Args:
        uploaded_file: Fichier téléchargé
        
    Returns:
        Le contenu textuel du fichier
    """
    file_type = uploaded_file.type
    
    # Première tentative: méthode standard selon le type de fichier
    if file_type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_text_from_docx(uploaded_file)
    elif file_type == "text/plain":
        text = extract_text_from_txt(uploaded_file)
    elif file_type.startswith("image/"):
        text = extract_text_from_image(uploaded_file)
    else:
        st.warning(f"Type de fichier non pris en charge: {file_type}. Tentative d'OCR générique.")
        # Tenter OCR générique pour les types non reconnus
        text = ocr_from_image_using_api(uploaded_file)
    
    # Si le texte est vide ou très court, essayer l'API OCR comme secours final
    if len(text.strip()) < 50:
        st.warning("Extraction de texte insuffisante. Tentative avec API OCR.")
        uploaded_file.seek(0)
        if file_type == "application/pdf":
            backup_text = ocr_from_pdf_using_api(uploaded_file)
        else:
            backup_text = ocr_from_image_using_api(uploaded_file)
        
        # N'utiliser le texte de secours que s'il est meilleur
        if len(backup_text.strip()) > len(text.strip()):
            text = backup_text
    
    return text
