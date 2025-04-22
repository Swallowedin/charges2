"""
Module amélioré d'analyse des charges facturées dans la reddition des charges.
Focus sur la détection et l'analyse des tableaux.
"""
import streamlit as st
import pandas as pd
import re
import json
import numpy as np
import cv2
from io import StringIO
from api.openai_client import send_openai_request, parse_json_response
from config import MAX_CHARGES_CHARS
from utils.table_detector import detect_and_extract_tables

def preprocess_charges_text(charges_text):
    """
    Prétraite le texte des charges pour faciliter l'extraction.
    
    Args:
        charges_text: Texte brut de la reddition des charges
        
    Returns:
        Texte prétraité
    """
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', charges_text)
    
    # Normaliser les symboles de monnaie
    text = re.sub(r'€', ' EUR ', text)
    text = re.sub(r'\$', ' USD ', text)
    
    # Uniformiser les séparateurs de nombres
    text = re.sub(r'(\d+),(\d{2})', r'\1.\2', text)  # 1,234.56 -> 1234.56
    
    # Normaliser les lignes du tableau
    text = re.sub(r'(\d+)[\s]*\.[\s]*(\d{2})', r'\1.\2', text)  # Corriger les montants décimaux
    
    return text

def extract_structured_data_from_text(charges_text):
    """
    Tente d'extraire des données structurées du texte brut.
    
    Args:
        charges_text: Texte brut de la reddition des charges
        
    Returns:
        Liste de dictionnaires {poste, montant}
    """
    charges = []
    
    # Recherche des motifs de type "DESCRIPTIF MONTANT"
    pattern = r'([A-Z][A-Za-zÀ-ÿ\s\-\/&]+)\s+(\d{1,3}(?:\s*\d{3})*(?:[,.]\d{2})?)\s*(?:€|EUR)?'
    matches = re.finditer(pattern, charges_text)
    
    for match in matches:
        desc = match.group(1).strip()
        montant_str = match.group(2).replace(' ', '').replace(',', '.')
        try:
            montant = float(montant_str)
            charges.append({"poste": desc, "montant": montant})
        except ValueError:
            continue
    
    # Recherche des motifs de tableaux
    # Format possible: | DESCRIPTIF | MONTANT HT | MONTANT TTC |
    table_pattern = r'([A-Z][A-Za-zÀ-ÿ\s\-\/&]+)\s*\|\s*(\d{1,3}(?:\s*\d{3})*(?:[,.]\d{2})?)'
    matches = re.finditer(table_pattern, charges_text)
    
    for match in matches:
        desc = match.group(1).strip()
        montant_str = match.group(2).replace(' ', '').replace(',', '.')
        try:
            montant = float(montant_str)
            # Vérifier si ce poste existe déjà
            if not any(c["poste"] == desc for c in charges):
                charges.append({"poste": desc, "montant": montant})
        except ValueError:
            continue
    
    return charges

def detect_table_structure(charges_text):
    """
    Détecte la structure d'un tableau dans le texte.
    
    Args:
        charges_text: Texte brut qui pourrait contenir un tableau
        
    Returns:
        DataFrame du tableau si détecté, None sinon
    """
    # Chercher des lignes qui suivent un format tabulaire
    lines = charges_text.split('\n')
    potential_table_lines = []
    
    for line in lines:
        # Si la ligne contient plusieurs chiffres avec des espaces entre eux
        if re.search(r'\d+\s+\d+', line) and len(re.findall(r'\d+', line)) >= 2:
            potential_table_lines.append(line)
    
    if len(potential_table_lines) >= 3:  # Au moins 3 lignes pour un tableau
        # Tenter de parser avec pandas
        try:
            df = pd.read_csv(StringIO('\n'.join(potential_table_lines)), sep=r'\s+', engine='python')
            # Si on a un DataFrame avec au moins 2 colonnes, c'est probablement un tableau
            if df.shape[1] >= 2:
                return df
        except:
            pass
    
    return None

def extract_charges_from_table(table_df):
    """
    Extrait les informations de charges d'un DataFrame.
    
    Args:
        table_df: DataFrame contenant les données de tableau
        
    Returns:
        Liste de dictionnaires {poste, montant}
    """
    charges = []
    
    # Identifier les colonnes pertinentes
    # Chercher les colonnes qui pourraient contenir des montants
    montant_cols = []
    desc_col = None
    
    for col in table_df.columns:
        # Si le nom de colonne contient des mots-clés liés aux montants
        if any(keyword in str(col).lower() for keyword in ['montant', 'total', 'ht', 'ttc', 'prix']):
            montant_cols.append(col)
        # Si le nom de colonne est lié à une description
        elif any(keyword in str(col).lower() for keyword in ['poste', 'desc', 'design', 'libel']):
            desc_col = col
    
    # Si on n'a pas identifié les colonnes par leur nom, utiliser l'heuristique
    if not desc_col:
        # La première colonne est souvent la description
        desc_col = table_df.columns[0]
    
    if not montant_cols:
        # Chercher des colonnes numériques
        for col in table_df.columns:
            if pd.to_numeric(table_df[col], errors='coerce').notna().sum() > len(table_df) / 2:
                montant_cols.append(col)
    
    # Fallback: prendre la dernière colonne comme montant si non identifié autrement
    if not montant_cols and len(table_df.columns) > 1:
        montant_cols = [table_df.columns[-1]]
    
    # Extraire les charges
    if desc_col and montant_cols:
        for idx, row in table_df.iterrows():
            desc = str(row[desc_col]).strip()
            
            # Ignorer les lignes vides ou qui semblent être des en-têtes/totaux
            if not desc or desc.lower() in ['total', 'montant', 'somme', 'sous-total']:
                continue
                
            for montant_col in montant_cols:
                montant_str = str(row[montant_col]).replace(' ', '').replace(',', '.')
                # Extraire juste le nombre si d'autres caractères sont présents
                montant_match = re.search(r'(\d+(?:\.\d+)?)', montant_str)
                
                if montant_match:
                    try:
                        montant = float(montant_match.group(1))
                        charges.append({"poste": desc, "montant": montant})
                        # On ne prend qu'un montant par description
                        break
                    except ValueError:
                        continue
    
    return charges

def extract_charged_amounts_from_reddition(charges_text, client):
    """
    Version améliorée d'extraction des montants des charges facturées.
    
    Args:
        charges_text: Texte de la reddition des charges
        client: Client OpenAI
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    st.write("### Analyse du relevé de charges")
    st.write("Extraction des données du relevé en cours...")
    
    # Prétraitement du texte
    preprocessed_text = preprocess_charges_text(charges_text)
    
    # 1. Essayer d'abord l'extraction de tableaux par vision par ordinateur
    try:
        charges_from_tables = detect_and_extract_tables(charges_text)
        if charges_from_tables and len(charges_from_tables) >= 3:  # Seuil arbitraire de confiance
            st.success(f"✅ Extraction de tableau réussie - {len(charges_from_tables)} postes de charges identifiés")
            return charges_from_tables
    except Exception as e:
        st.warning(f"Extraction automatique de tableaux non réussie: {str(e)}. Tentative avec d'autres méthodes...")
    
    # 2. Essayer la détection de structure tabulaire dans le texte
    table_df = detect_table_structure(preprocessed_text)
    if table_df is not None:
        charges = extract_charges_from_table(table_df)
        if charges and len(charges) >= 3:  # Seuil arbitraire
            st.success(f"✅ Structure de tableau détectée - {len(charges)} postes de charges identifiés")
            return charges
    
    # 3. Essayer l'extraction structurée à partir du texte
    structured_charges = extract_structured_data_from_text(preprocessed_text)
    if structured_charges and len(structured_charges) >= 3:
        st.success(f"✅ Extraction structurée réussie - {len(structured_charges)} postes de charges identifiés")
        return structured_charges
    
    # 4. Si toutes les méthodes échouent, recourir à OpenAI pour l'analyse
    prompt = f"""
    ## EXTRACTION PRÉCISE DES CHARGES LOCATIVES
    
    Le document suivant est un relevé de charges locatives refacturées au preneur.
    Le document est probablement un tableau formaté sous forme de texte.
    
    ```
    {preprocessed_text[:MAX_CHARGES_CHARS]}
    ```
    
    ## INSTRUCTIONS
    
    1. Analyse ce texte pour en extraire les charges facturées.
    2. Cherche les motifs qui ressemblent à "[NOM DE LA CHARGE] ... [MONTANT]"
    3. Identifie les informations suivantes:
       - Le nom exact de la charge (ex: "NETTOYAGE EXTERIEUR")
       - Le montant facturé HT (si disponible)
       - Le montant facturé TTC (si disponible)
    4. Si tu trouves plusieurs montants pour une même charge, prends le montant final ou TTC.
    5. Identifie également le montant TOTAL des charges.
    
    IMPORTANT:
    - Si tu détectes une structure de tableau, analyse-la ligne par ligne.
    - Assure-toi d'extraire TOUTES les charges, même avec des descriptions complexes.
    - CHAQUE LIGNE DE LA PARTIE "charges" DOIT AVOIR un montant numérique valide.
    - Les montants doivent être des nombres décimaux sans symbole € ou autres caractères.
    
    Format précis de la réponse JSON:
    {
        "charges": [
            {"poste": "Nom exact du poste", "montant": montant_numérique},
            ...
        ],
        "total": montant_total_numérique
    }
    """
    
    response_text = send_openai_request(
        client=client,
        prompt=prompt,
        temperature=0
    )
    
    try:
        result = parse_json_response(response_text, default_value={})
        
        if "charges" in result and isinstance(result["charges"], list):
            # Vérifier la validité des données
            valid_charges = []
            for charge in result["charges"]:
                if "poste" in charge and "montant" in charge:
                    try:
                        # S'assurer que le montant est un nombre
                        charge["montant"] = float(charge["montant"])
                        valid_charges.append(charge)
                    except (ValueError, TypeError):
                        continue
            
            if valid_charges:
                # Afficher un résumé formaté des charges extraites
                st.success(f"✅ Extraction avec IA réussie - {len(valid_charges)} postes de charges identifiés")
                
                # Créer un tableau récapitulatif des charges pour vérification visuelle
                total = sum(charge["montant"] for charge in valid_charges)
                
                # Afficher le tableau
                df = pd.DataFrame([
                    {"Poste de charge": charge["poste"], "Montant": f"{charge['montant']:.2f} €"}
                    for charge in valid_charges
                ])
                st.table(df)
                
                return valid_charges
            else:
                st.warning("Aucune charge valide n'a pu être extraite par IA.")
        else:
            st.warning("Format de réponse IA non standard.")
    
    except Exception as e:
        st.error(f"Erreur lors de l'extraction des charges via IA: {str(e)}")
    
    # 5. Dernier recours: méthode simplifiée
    return extract_charged_amounts_fallback(charges_text, client)

def extract_charged_amounts_fallback(charges_text, client):
    """
    Méthode de secours pour extraire les montants facturés.
    
    Args:
        charges_text: Texte de la reddition des charges
        client: Client OpenAI
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    # Utiliser un prompt encore plus simple et robuste
    prompt = f"""
    ## EXTRACTION SIMPLIFIÉE DES CHARGES LOCATIVES

    Extrait SEULEMENT les lignes qui contiennent un nom de charge et un montant numérique.
    Ne cherche PAS à comprendre la structure du document, extrait simplement chaque ligne qui semble être une charge.
    
    Texte:
    ```
    {charges_text[:5000]}
    ```
    
    Format JSON:
    {{
      "charges": [
        {{ "poste": "Nom complet de la charge", "montant": montant_numérique }},
        ...
      ]
    }}
    
    IMPORTANT: Ne réponds RIEN d'autre que ce JSON exact.
    """
    
    response_text = send_openai_request(
        client=client,
        prompt=prompt,
        temperature=0
    )
    
    result = parse_json_response(response_text, default_value={"charges": []})
    
    if "charges" in result and isinstance(result["charges"], list):
        charges = []
        for charge in result["charges"]:
            if "poste" in charge and "montant" in charge:
                try
