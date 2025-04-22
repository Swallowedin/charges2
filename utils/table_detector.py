"""
Module spécialisé dans la détection et l'extraction de tableaux à partir d'images.
"""
import cv2
import numpy as np
import pandas as pd
import pytesseract
from pdf2image import convert_from_bytes
import streamlit as st
import re
import tempfile
import os
import io

def detect_table_boundaries(img):
    """
    Détecte les contours d'un tableau dans une image.
    
    Args:
        img: Image OpenCV
        
    Returns:
        Contours détectés des potentiels tableaux
    """
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

def extract_tables_from_image(img):
    """
    Extrait plusieurs tableaux d'une image.
    
    Args:
        img: Image OpenCV
        
    Returns:
        Liste de sous-images contenant des tableaux
    """
    contours = detect_table_boundaries(img)
    tables = []
    
    for contour in contours:
        # Créer un rectangle autour du contour
        x, y, w, h = cv2.boundingRect(contour)
        
        # Extraire la zone du tableau
        table_roi = img[y:y+h, x:x+w]
        tables.append(table_roi)
    
    return tables

def preprocess_table_image(table_img):
    """
    Prétraite l'image d'un tableau pour améliorer l'OCR.
    
    Args:
        table_img: Image du tableau
        
    Returns:
        Image prétraitée
    """
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

def detect_and_extract_line_structure(table_img):
    """
    Détecte la structure des lignes et colonnes dans un tableau.
    
    Args:
        table_img: Image du tableau
        
    Returns:
        Listes des positions de lignes et colonnes
    """
    # Prétraitement pour détecter les lignes
    gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)
    
    # Détecter les lignes horizontales et verticales avec Hough
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
    
    h_lines = []
    v_lines = []
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # Calculer l'angle pour déterminer si la ligne est horizontale ou verticale
            angle = np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi
            
            if abs(angle) < 20 or abs(angle) > 160:  # Presque horizontale
                h_lines.append((min(y1, y2), max(y1, y2)))
            elif abs(angle - 90) < 20 or abs(angle + 90) < 20:  # Presque verticale
                v_lines.append((min(x1, x2), max(x1, x2)))
    
    # Regrouper les lignes horizontales proches
    h_lines.sort()
    h_clusters = []
    if h_lines:
        current_cluster = [h_lines[0]]
        for i in range(1, len(h_lines)):
            if h_lines[i][0] - current_cluster[-1][1] < 10:  # Lignes proches
                current_cluster.append(h_lines[i])
            else:
                h_clusters.append(np.mean([line[0] for line in current_cluster]))
                current_cluster = [h_lines[i]]
        
        h_clusters.append(np.mean([line[0] for line in current_cluster]))
    
    # Regrouper les lignes verticales proches
    v_lines.sort()
    v_clusters = []
    if v_lines:
        current_cluster = [v_lines[0]]
        for i in range(1, len(v_lines)):
            if v_lines[i][0] - current_cluster[-1][1] < 10:  # Lignes proches
                current_cluster.append(v_lines[i])
            else:
                v_clusters.append(np.mean([line[0] for line in current_cluster]))
                current_cluster = [v_lines[i]]
                
        v_clusters.append(np.mean([line[0] for line in current_cluster]))
    
    return h_clusters, v_clusters

def ocr_table_cell(cell_img):
    """
    Applique l'OCR à une cellule de tableau.
    
    Args:
        cell_img: Image d'une cellule
        
    Returns:
        Texte extrait
    """
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

def extract_table_data(table_img):
    """
    Extrait les données d'un tableau en utilisant la détection de structure.
    
    Args:
        table_img: Image du tableau
        
    Returns:
        Liste de dictionnaires représentant les données du tableau
    """
    # Détecter la structure du tableau
    h_lines, v_lines = detect_and_extract_line_structure(table_img)
    
    # Si la détection de structure échoue, utiliser la méthode par grille
    if len(h_lines) < 2 or len(v_lines) < 2:
        return ocr_table_by_grid(table_img)
    
    # Trier les positions des lignes et colonnes
    h_lines.sort()
    v_lines.sort()
    
    # Créer une matrice pour stocker le texte des cellules
    rows = len(h_lines) - 1
    cols = len(v_lines) - 1
    
    if rows <= 0 or cols <= 0:
        return []
    
    table_data = []
    
    # Parcourir les cellules
    for i in range(rows):
        row_data = {}
        for j in range(cols):
            # Définir les limites de la cellule
            y1, y2 = int(h_lines[i]), int(h_lines[i+1])
            x1, x2 = int(v_lines[j]), int(v_lines[j+1])
            
            # Extraire la cellule
            cell_img = table_img[y1:y2, x1:x2]
            
            # Extraire le texte de la cellule
            cell_text = ocr_table_cell(cell_img)
            
            # Stocker le résultat
            row_data[f"col_{j}"] = cell_text
        
        table_data.append(row_data)
    
    return table_data

def ocr_table_by_grid(table_img):
    """
    Extrait les données d'un tableau en le divisant en grille uniforme.
    
    Args:
        table_img: Image du tableau
        
    Returns:
        Liste de dictionnaires représentant les données du tableau
    """
    # Prétraiter l'image
    preprocessed = preprocess_table_image(table_img)
    
    # Estimer le nombre de lignes et colonnes
    height, width = preprocessed.shape[:2]
    
    # Analyse de la projection horizontale pour estimer les lignes
    h_projection = np.sum(preprocessed, axis=1)
    h_peaks = np.where(h_projection > np.median(h_projection) * 1.5)[0]
    
    # Créer des clusters pour les lignes
    h_clusters = []
    if len(h_peaks) > 0:
        current_cluster = [h_peaks[0]]
        for i in range(1, len(h_peaks)):
            if h_peaks[i] - current_cluster[-1] <= 5:  # Points proches
                current_cluster.append(h_peaks[i])
            else:
                h_clusters.append(int(np.mean(current_cluster)))
                current_cluster = [h_peaks[i]]
        h_clusters.append(int(np.mean(current_cluster)))
    
    # Si la détection des lignes échoue, diviser uniformément
    if len(h_clusters) < 3:  # Au moins 2 lignes de données + en-tête
        est_rows = max(3, height // 50)  # Estimation grossière
        row_height = height // est_rows
        h_clusters = [i * row_height for i in range(est_rows)]
    
    # Analyse de la projection verticale pour estimer les colonnes
    v_projection = np.sum(preprocessed, axis=0)
    v_peaks = np.where(v_projection > np.median(v_projection) * 1.5)[0]
    
    # Créer des clusters pour les colonnes
    v_clusters = []
    if len(v_peaks) > 0:
        current_cluster = [v_peaks[0]]
        for i in range(1, len(v_peaks)):
            if v_peaks[i] - current_cluster[-1] <= 5:  # Points proches
                current_cluster.append(v_peaks[i])
            else:
                v_clusters.append(int(np.mean(current_cluster)))
                current_cluster = [v_peaks[i]]
        v_clusters.append(int(np.mean(current_cluster)))
    
    # Si la détection des colonnes échoue, diviser uniformément
    if len(v_clusters) < 3:  # Au moins 2 colonnes de données + index
        est_cols = max(3, width // 100)  # Estimation grossière
        col_width = width // est_cols
        v_clusters = [i * col_width for i in range(est_cols)]
    
    # Ajouter les limites de l'image
    if h_clusters[0] > 10:
        h_clusters.insert(0, 0)
    if h_clusters[-1] < height - 10:
        h_clusters.append(height)
        
    if v_clusters[0] > 10:
        v_clusters.insert(0, 0)
    if v_clusters[-1] < width - 10:
        v_clusters.append(width)
    
    # Créer la grille et extraire le texte de chaque cellule
    rows = len(h_clusters) - 1
    cols = len(v_clusters) - 1
    
    table_data = []
    
    for i in range(rows):
        row_data = {}
        for j in range(cols):
            # Définir les limites de la cellule
            y1, y2 = h_clusters[i], h_clusters[i+1]
            x1, x2 = v_clusters[j], v_clusters[j+1]
            
            # Extraire la cellule
            cell_img = table_img[y1:y2, x1:x2]
            
            # Vérifier que la cellule n'est pas vide
            if cell_img.size == 0 or np.mean(cell_img) > 245:  # Cellule presque blanche
                cell_text = ""
            else:
                # Extraire le texte de la cellule
                cell_text = ocr_table_cell(cell_img)
            
            # Stocker le résultat
            row_data[f"col_{j}"] = cell_text
        
        table_data.append(row_data)
    
    return table_data

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
        value = value.lower()
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
    if not desc_col:
        desc_col = list(table_data[0].keys())[0]
    if not amount_col:
        amount_col = list(table_data[0].keys())[-1]
    
    # Parcourir les lignes (ignorer la première qui est probablement l'en-tête)
    for row in table_data[1:]:
        if desc_col in row and amount_col in row:
            desc = row[desc_col].strip()
            amount_str = row[amount_col].strip()
            
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

def detect_and_extract_tables(charges_text, image_data=None):
    """
    Détecte et extrait les tableaux de charges à partir du texte ou de l'image.
    
    Args:
        charges_text: Texte de la reddition des charges
        image_data: Données d'image binaires (optionnel)
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    tables = []
    
    # Si des données d'image sont fournies, les utiliser directement
    if image_data:
        try:
            # Convertir les données binaires en image
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Extraire les tableaux
            tables = extract_tables_from_image(img)
        except Exception as e:
            st.warning(f"Erreur lors de l'extraction des tableaux de l'image: {str(e)}")
            return []
    
    # Si aucun tableau n'a été extrait et que nous avons un PDF
    if not tables and charges_text and "pdf" in charges_text.lower():
        try:
            # Extraire le chemin du PDF du texte
            pdf_path_match = re.search(r'Fichier:\s*([^\n]+\.pdf)', charges_text)
            if pdf_path_match:
                pdf_path = pdf_path_match.group(1)
                
                # Convertir le PDF en images
                with open(pdf_path, 'rb') as pdf_file:
                    images = convert_from_bytes(pdf_file.read(), dpi=300)
                
                # Extraire les tableaux de chaque page
                for img_pil in images:
                    # Convertir l'image PIL en OpenCV
                    img = np.array(img_pil)
                    img = img[:, :, ::-1].copy()  # RGB -> BGR
                    
                    # Extraire les tableaux
                    page_tables = extract_tables_from_image(img)
                    tables.extend(page_tables)
        except Exception as e:
            st.warning(f"Erreur lors de l'extraction des tableaux du PDF: {str(e)}")
    
    # Traiter chaque tableau et extraire les charges
    all_charges = []
    
    for i, table_img in enumerate(tables):
        try:
            # Prétraiter l'image du tableau
            processed_table = preprocess_table_image(table_img)
            
            # Extraire les données du tableau
            table_data = extract_table_data(processed_table)
            
            # Convertir les données en charges
            charges = convert_table_data_to_charges(table_data)
            
            # Ajouter à la liste globale
            all_charges.extend(charges)
        except Exception as e:
            st.warning(f"Erreur lors du traitement du tableau {i+1}: {str(e)}")
    
    return all_charges
