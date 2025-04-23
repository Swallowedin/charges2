"""
Module spécialisé dans la détection et l'extraction de tableaux à partir d'images.
"""
import cv2
import numpy as np
import pandas as pd
import pytesseract
import streamlit as st
import re
import tempfile
import os
import io
from PIL import Image

def detect_table_boundaries(img):
    """
    Détecte les contours d'un tableau dans une image.
    
    Args:
        img: Image OpenCV
        
    Returns:
        Contours détectés des potentiels tableaux
    """
    # Vérifier que l'image est valide
    if img is None or img.size == 0:
        st.warning("Image invalide pour la détection de tableaux")
        return []
        
    try:
        # Conversion en niveaux de gris
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Réduction du bruit
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Détection des bords
        edges = cv2.Canny(blur, 50, 150, apertureSize=3)
        
        # Amélioration des lignes par dilatation
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Détecter les contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrer les contours par taille (pour éliminer le bruit)
        min_area = img.shape[0] * img.shape[1] * 0.05  # Au moins 5% de l'image
        large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        
        return large_contours
    except Exception as e:
        st.warning(f"Erreur lors de la détection des contours du tableau: {str(e)}")
        return []

def extract_tables_from_image(img):
    """
    Extrait plusieurs tableaux d'une image.
    
    Args:
        img: Image OpenCV
        
    Returns:
        Liste de sous-images contenant des tableaux
    """
    if img is None or img.size == 0:
        return []
        
    try:
        contours = detect_table_boundaries(img)
        tables = []
        
        for contour in contours:
            # Créer un rectangle autour du contour
            x, y, w, h = cv2.boundingRect(contour)
            
            # Vérifier que les dimensions sont valides
            if w <= 0 or h <= 0 or x + w > img.shape[1] or y + h > img.shape[0]:
                continue
                
            # Extraire la zone du tableau
            table_roi = img[y:y+h, x:x+w]
            
            # Vérifier que l'extraction a réussi
            if table_roi is not None and table_roi.size > 0:
                tables.append(table_roi)
        
        return tables
    except Exception as e:
        st.warning(f"Erreur lors de l'extraction des tableaux: {str(e)}")
        return []

def preprocess_table_image(table_img):
    """
    Prétraite l'image d'un tableau pour améliorer l'OCR.
    
    Args:
        table_img: Image du tableau
        
    Returns:
        Image prétraitée
    """
    if table_img is None or table_img.size == 0:
        return None
        
    try:
        # Conversion en niveaux de gris
        gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
        
        # Augmentation du contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrasted = clahe.apply(gray)
        
        # Binarisation adaptative
        binary = cv2.adaptiveThreshold(
            contrasted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 15, 10
        )
        
        # Opérations morphologiques pour nettoyer l'image
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        
        # Inverser l'image pour l'OCR (texte noir sur fond blanc)
        result = cv2.bitwise_not(closing)
        
        return result
    except Exception as e:
        st.warning(f"Erreur lors du prétraitement de l'image du tableau: {str(e)}")
        return None

def ocr_table_cell(cell_img):
    """
    Applique l'OCR à une cellule de tableau.
    
    Args:
        cell_img: Image d'une cellule
        
    Returns:
        Texte extrait
    """
    if cell_img is None or cell_img.size == 0:
        return ""
        
    try:
        # Prétraitement spécifique pour les cellules
        # Agrandir l'image pour améliorer l'OCR
        height, width = cell_img.shape[:2]
        cell_img = cv2.resize(cell_img, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # Conversion en niveaux de gris si nécessaire
        if len(cell_img.shape) == 3:
            gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = cell_img
        
        # Binarisation
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # OCR avec configuration pour cellule
        text = pytesseract.image_to_string(
            binary, 
            lang='fra',
            config='--psm 6 --oem 3 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789,.€ -/&"'
        )
        
        # Nettoyage du texte
        text = text.strip()
        
        return text
    except Exception as e:
        st.warning(f"Erreur lors de l'OCR de la cellule: {str(e)}")
        return ""

def ocr_table_by_grid(table_img):
    """
    Extrait les données d'un tableau en le divisant en grille uniforme.
    
    Args:
        table_img: Image du tableau
        
    Returns:
        Liste de dictionnaires représentant les données du tableau
    """
    if table_img is None or table_img.size == 0:
        return []
        
    try:
        # Estimation du nombre de lignes et colonnes
        height, width = table_img.shape[:2]
        
        # Division simple en grille
        est_rows = max(3, height // 50)  # Estimation grossière
        est_cols = max(3, width // 100)  # Estimation grossière
        
        row_height = height // est_rows
        col_width = width // est_cols
        
        h_clusters = [i * row_height for i in range(est_rows + 1)]
        v_clusters = [i * col_width for i in range(est_cols + 1)]
        
        # Créer la grille et extraire le texte de chaque cellule
        rows = len(h_clusters) - 1
        cols = len(v_clusters) - 1
        
        table_data = []
        
        for i in range(rows):
            row_data = {}
            for j in range(cols):
                try:
                    # Définir les limites de la cellule
                    y1, y2 = h_clusters[i], h_clusters[i+1]
                    x1, x2 = v_clusters[j], v_clusters[j+1]
                    
                    # Vérifier que les dimensions sont valides
                    if x1 >= x2 or y1 >= y2 or x2 > width or y2 > height:
                        cell_text = ""
                    else:
                        # Extraire la cellule
                        cell_img = table_img[y1:y2, x1:x2]
                        
                        # Vérifier que la cellule n'est pas vide
                        if cell_img.size == 0 or np.mean(cell_img) > 245:  # Cellule presque blanche
                            cell_text = ""
                        else:
                            # Extraire le texte de la cellule
                            cell_text = ocr_table_cell(cell_img)
                except Exception as cell_error:
                    st.warning(f"Erreur lors de l'extraction de la cellule grille [{i},{j}]: {str(cell_error)}")
                    cell_text = ""
                
                # Stocker le résultat
                row_data[f"col_{j}"] = cell_text
            
            table_data.append(row_data)
        
        return table_data
    except Exception as e:
        st.warning(f"Erreur lors de l'extraction par grille: {str(e)}")
        return []

def extract_table_data(table_img):
    """
    Extrait les données d'un tableau en utilisant la détection de structure.
    
    Args:
        table_img: Image du tableau
        
    Returns:
        Liste de dictionnaires représentant les données du tableau
    """
    if table_img is None or table_img.size == 0:
        return []
        
    try:
        # Essayer la méthode par grille qui est plus robuste
        return ocr_table_by_grid(table_img)
    except Exception as e:
        st.warning(f"Erreur lors de l'extraction des données du tableau: {str(e)}")
        return []

def convert_table_data_to_charges(table_data):
    """
    Convertit les données de tableau brutes en liste structurée de charges.
    
    Args:
        table_data: Données brutes extraites du tableau
        
    Returns:
        Liste de dictionnaires {poste, montant}
    """
    if not table_data:
        return []
    
    charges = []
    
    # Identifier les colonnes probables pour le nom et le montant
    # Les premières lignes sont souvent des en-têtes
    header_row = table_data[0] if len(table_data) > 0 else {}
    
    desc_col = None
    amount_col = None
    
    # Rechercher dans les en-têtes
    for col, value in header_row.items():
        value = str(value).lower()
        if any(keyword in value for keyword in ["désignation", "designation", "libellé", "libelle", "desc", "poste"]):
            desc_col = col
        elif any(keyword in value for keyword in ["montant", "total", "ht", "ttc", "somme", "euros"]):
            amount_col = col
    
    # Si les en-têtes n'ont pas été identifiés, essayer de déduire à partir des données
    if not desc_col or not amount_col:
        # Supposer que la première colonne est la description et la dernière est le montant
        columns = list(table_data[0].keys())
        if len(columns) >= 2:
            if not desc_col:
                desc_col = columns[0]
            if not amount_col:
                # Chercher la première colonne qui contient des valeurs numériques
                for col in reversed(columns):  # Commencer par la fin
                    has_numbers = False
                    for row in table_data[1:]:  # Ignorer l'en-tête
                        if col in row and re.search(r'\d+([,.]\d+)?', str(row[col])):
                            has_numbers = True
                            break
                    if has_numbers:
                        amount_col = col
                        break
    
    # Si toujours pas identifié, utiliser les colonnes par défaut
    if not desc_col and table_data and table_data[0]:
        desc_col = list(table_data[0].keys())[0]
    if not amount_col and table_data and table_data[0]:
        amount_col = list(table_data[0].keys())[-1]
    
    # Parcourir les lignes (ignorer la première qui est probablement l'en-tête)
    for row in table_data[1:]:
        if desc_col in row and amount_col in row:
            desc = str(row[desc_col]).strip()
            amount_str = str(row[amount_col]).strip()
            
            # Ignorer les lignes vides ou les totaux
            if not desc or desc.lower() in ["total", "sous-total", "somme", "montant"]:
                continue
                
            # Extraire le montant numérique
            amount_match = re.search(r'(\d+[,.]\d+|\d+)', amount_str.replace(' ', ''))
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '.')
                try:
                    amount = float(amount_str)
                    charges.append({"poste": desc, "montant": amount})
                except ValueError:
                    continue
    
    return charges

def extract_charges_directly_from_text(charges_text):
    """
    Extrait les charges directement à partir du texte formaté comme un tableau.
    
    Args:
        charges_text: Texte de la reddition des charges
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    charges = []
    
    try:
        # Rechercher lignes qui suivent un format tabulaire
        lines = charges_text.strip().split('\n')
        
        # Chercher des lignes qui contiennent des montants
        for line in lines:
            # Rechercher des motifs de "texte descriptif + montant"
            match = re.search(r'([A-Za-zÀ-ÿ\s\-\/&\.]+)\s+(\d[\d\s]*[\.,]\d+)', line)
            if match:
                desc = match.group(1).strip()
                amount_str = match.group(2).strip().replace(' ', '').replace(',', '.')
                
                # Ignorer les lignes de totaux
                if desc.lower() in ["total", "sous-total", "somme", "montant", "total charges"]:
                    continue
                    
                try:
                    amount = float(amount_str)
                    charges.append({"poste": desc, "montant": amount})
                except ValueError:
                    continue
    
    except Exception as e:
        st.warning(f"Erreur lors de l'extraction directe des charges du texte: {str(e)}")
    
    return charges

def detect_and_extract_tables(charges_text, image_data=None):
    """
    Détecte et extrait les tableaux de charges à partir du texte ou de l'image.
    
    Args:
        charges_text: Texte de la reddition des charges
        image_data: Données d'image binaires (optionnel)
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    all_charges = []
    
    # Essayer d'abord d'extraire directement à partir du texte formaté comme un tableau
    if charges_text:
        # Rechercher le texte contenant "RELEVE INDIVIDUEL DES CHARGES LOCATIVES"
        if "RELEVE INDIVIDUEL DES CHARGES LOCATIVES" in charges_text:
            section = charges_text.split("RELEVE INDIVIDUEL DES CHARGES LOCATIVES")[1]
            # Extraire les lignes potentielles de charges
            pattern = r'([A-Z][A-Z\s]+)\s+(\d[\d\s]*[\.,]\d+)\s*€?'
            matches = re.findall(pattern, section)
            for match in matches:
                desc = match[0].strip()
                amount_str = match[1].replace(' ', '').replace(',', '.')
                try:
                    amount = float(amount_str)
                    if amount > 0:  # Ignorer les montants nuls ou négatifs
                        all_charges.append({"poste": desc, "montant": amount})
                except ValueError:
                    continue
            
            if all_charges:
                return all_charges
    
    # Si aucune charge trouvée via la méthode de texte, essayer l'extraction d'image
    tables = []
    
    # Si des données d'image sont fournies, les utiliser directement
    if image_data:
        try:
            # Tenter de décoder l'image
            try:
                # Méthode 1: Utiliser numpy et OpenCV
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Si l'image est décodée avec succès
                if img is not None and img.size > 0:
                    # Extraire les tableaux
                    tables = extract_tables_from_image(img)
            except Exception as e1:
                st.warning(f"Méthode 1 de décodage d'image échouée: {str(e1)}")
                
                try:
                    # Méthode 2: Utiliser PIL
                    img_io = io.BytesIO(image_data)
                    pil_img = Image.open(img_io)
                    
                    # Convertir l'image PIL en OpenCV
                    img = np.array(pil_img)
                    if len(img.shape) == 3 and img.shape[2] == 4:  # Si RGBA
                        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                    elif len(img.shape) == 3 and img.shape[2] == 3:  # Si RGB
                        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    
                    # Vérifier que l'image est valide
                    if img is not None and img.size > 0:
                        # Extraire les tableaux
                        tables = extract_tables_from_image(img)
                except Exception as e2:
                    st.warning(f"Méthode 2 de décodage d'image échouée: {str(e2)}")
                    
                    # Méthode 3: Sauvegarder et relire le fichier
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                            tmp.write(image_data)
                            tmp_path = tmp.name
                        
                        img = cv2.imread(tmp_path)
                        
                        # Nettoyer le fichier temporaire
                        os.unlink(tmp_path)
                        
                        # Vérifier que l'image est valide
                        if img is not None and img.size > 0:
                            # Extraire les tableaux
                            tables = extract_tables_from_image(img)
                    except Exception as e3:
                        st.warning(f"Méthode 3 de décodage d'image échouée: {str(e3)}")
        except Exception as e:
            st.warning(f"Erreur lors de l'extraction des tableaux de l'image: {str(e)}")
    
    # Traiter chaque tableau et extraire les charges
    for i, table_img in enumerate(tables):
        try:
            # Prétraiter l'image du tableau
            processed_table = preprocess_table_image(table_img)
            
            if processed_table is None:
                continue
                
            # Extraire les données du tableau
            table_data = extract_table_data(table_img)
            
            # Convertir les données en charges
            charges = convert_table_data_to_charges(table_data)
            
            # Ajouter à la liste globale
            all_charges.extend(charges)
        except Exception as e:
            st.warning(f"Erreur lors du traitement du tableau {i+1}: {str(e)}")
    
    # Si aucun tableau n'a été trouvé, essayer l'extraction directe du texte
    if not all_charges and charges_text:
        text_charges = extract_charges_directly_from_text(charges_text)
        all_charges.extend(text_charges)
    
    # Analyser le texte de la reddition de charges pour extraire les montants
    if not all_charges and charges_text:
        # Méthode de secours: rechercher des patterns spécifiques au format du document
        pattern = r'(NETTOYAGE EXTERIEUR|DECHETS SECS|HYGIENE SANTE|ELECTRICITE ABORDS|STRUCTURE|VRD|ESPACES VERTS|MOYENS DE PROTECTION|SURVEILLANCE|GESTION ADMINISTRATION|HONORAIRES GESTION)\s+(\d[\d\s]*[\.,]\d+)'
        matches = re.findall(pattern, charges_text)
        
        for match in matches:
            desc = match[0].strip()
            amount_str = match[1].replace(' ', '').replace(',', '.')
            try:
                amount = float(amount_str)
                all_charges.append({"poste": desc, "montant": amount})
            except ValueError:
                continue
    
    return all_charges
