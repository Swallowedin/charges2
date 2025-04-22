"""
Modules d'analyseurs locaux ne dépendant pas de l'API externe pour améliorer la robustesse.
"""

# -------------------------------
# local_bail_analyzer.py
# -------------------------------
import re

def extract_refacturable_charges_locally(bail_text):
    """
    Extrait les charges refacturables du bail en utilisant des expressions régulières
    et des heuristiques, sans recourir à une API.
    
    Args:
        bail_text: Texte du bail commercial
        
    Returns:
        Liste de dictionnaires contenant les charges refacturables
    """
    charges = []
    
    # Catégories de charges communément refacturables dans les baux commerciaux
    common_categories = [
        {"pattern": r'nettoyage', "categorie": "Nettoyage", "description": "Frais de nettoyage"},
        {"pattern": r'd[ée]chet', "categorie": "Déchets", "description": "Enlèvement des déchets"},
        {"pattern": r'espaces?\s+verts?', "categorie": "Espaces verts", "description": "Entretien des espaces verts"},
        {"pattern": r'[ée]lectricit[ée]', "categorie": "Électricité", "description": "Électricité des parties communes"},
        {"pattern": r'eau', "categorie": "Eau", "description": "Consommation d'eau"},
        {"pattern": r'chauffage', "categorie": "Chauffage", "description": "Chauffage collectif"},
        {"pattern": r'ascenseur', "categorie": "Ascenseurs", "description": "Entretien des ascenseurs"},
        {"pattern": r'surveillance|gardiennage|s[ée]curit[ée]', "categorie": "Sécurité & Surveillance", "description": "Frais de surveillance et sécurité"},
        {"pattern": r'assurance', "categorie": "Assurances", "description": "Primes d'assurance"},
        {"pattern": r'imp[ôo]ts?|taxe', "categorie": "Impôts & Taxes", "description": "Taxes et impôts locaux"},
        {"pattern": r'foncier', "categorie": "Taxe foncière", "description": "Taxe foncière"},
        {"pattern": r'taxe\s+bureaux', "categorie": "Taxe bureaux", "description": "Taxe sur les bureaux"},
        {"pattern": r'gestion|administration', "categorie": "Frais de gestion", "description": "Frais de gestion administrative"},
        {"pattern": r'maintenance', "categorie": "Maintenance", "description": "Maintenance technique"},
        {"pattern": r'r[ée]paration', "categorie": "Réparations", "description": "Réparations courantes"}
    ]
    
    # Rechercher les clauses de charges
    # Motif typique: "Le preneur prendra à sa charge..."
    charge_clauses = []
    
    # 1. Rechercher des sections entières dédiées aux charges
    section_patterns = [
        r'(?i)(?:ARTICLE|ART\.?)[\s0-9\.]*(?:CHARGES|REPARTITION DES CHARGES).*?(?=(?:ARTICLE|ART\.?)|$)',
        r'(?i)CHARGES LOCATIVES.*?(?=(?:ARTICLE|ART\.?)|$)',
        r'(?i)(?:Le preneur|Le locataire)[\s\S]{0,50}(?:prendra à sa charge|supportera|remboursera)[\s\S]{0,500}(?=\n\n|\.\s[A-Z])'
    ]
    
    for pattern in section_patterns:
        matches = re.finditer(pattern, bail_text, re.DOTALL)
        for match in matches:
            charge_clauses.append(match.group(0))
    
    # 2. Si aucune section n'est trouvée, rechercher des phrases isolées
    if not charge_clauses:
        sentence_patterns = [
            r'(?i)(?:Le preneur|Le locataire)[\s\S]{0,50}(?:prendra à sa charge|supportera|remboursera)[\s\S]{0,200}?(?=\.|$)',
            r'(?i)(?:charges|dépenses)[\s\S]{0,50}(?:du preneur|du locataire|refacturable)[\s\S]{0,200}?(?=\.|$)',
            r'(?i)(?:seront à la charge)[\s\S]{0,50}(?:du preneur|du locataire)[\s\S]{0,200}?(?=\.|$)'
        ]
        
        for pattern in sentence_patterns:
            matches = re.finditer(pattern, bail_text, re.DOTALL)
            for match in matches:
                charge_clauses.append(match.group(0))
    
    # Texte complet des clauses de charges
    charges_text = "\n".join(charge_clauses)
    
    # Rechercher dans le texte des clauses chaque catégorie commune de charges
    for category in common_categories:
        if re.search(category["pattern"], charges_text, re.IGNORECASE):
            # Trouver le contexte autour de la mention
            matches = re.finditer(category["pattern"], charges_text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 100)
                end = min(len(charges_text), match.end() + 100)
                context = charges_text[start:end]
                
                # Chercher une référence à un article dans le contexte
                article_match = re.search(r'(?:ARTICLE|ART\.?)[\s0-9\.]+', context)
                base_legale = article_match.group(0) if article_match else "Mentionné dans le bail"
                
                # Ajouter la charge uniquement si elle n'existe pas déjà
                existing = [c for c in charges if c["categorie"] == category["categorie"]]
                if not existing:
                    charges.append({
                        "categorie": category["categorie"],
                        "description": category["description"],
                        "base_legale": base_legale,
                        "certitude": "moyenne"  # Niveau de certitude par défaut
                    })
    
    # Si on n'a toujours rien trouvé, utiliser des règles par défaut selon le type de bail commercial
    if not charges and "BAIL COMMERCIAL" in bail_text.upper():
        # Charges typiquement refacturables dans les baux commerciaux
        default_charges = [
            {"categorie": "Entretien immeuble", "description": "Frais d'entretien de l'immeuble", "base_legale": "Usage commercial", "certitude": "faible"},
            {"categorie": "Nettoyage", "description": "Nettoyage des parties communes", "base_legale": "Usage commercial", "certitude": "faible"},
            {"categorie": "Taxes", "description": "Impôts et taxes", "base_legale": "Usage commercial", "certitude": "faible"}
        ]
        charges.extend(default_charges)
    
    return charges


# -------------------------------
# local_charges_analyzer.py
# -------------------------------
import re

def extract_charged_amounts_locally(charges_text):
    """
    Extrait les montants des charges facturées en utilisant des expressions régulières
    et des heuristiques, sans recourir à une API.
    
    Args:
        charges_text: Texte de la reddition des charges
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    charges = []
    
    # Rechercher les montants et leur description
    # Différents motifs pour s'adapter aux formats variés
    patterns = [
        # Format: DESCRIPTION ... MONTANT€
        r'([A-Z][A-Za-zÀ-ÿ\s\-\/&\.]+)\s+(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)\s*(?:€|EUR)?',
        
        # Format: DESCRIPTION ... MONTANT (sans symbole €)
        r'([A-Z][A-Za-zÀ-ÿ\s\-\/&\.]+)\s+(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)(?:\s|$)',
        
        # Format tabulaire avec espaces ou pipes: DESCRIPTION | MONTANT
        r'([A-Za-zÀ-ÿ\s\-\/&\.]+)[|\t\s]{2,}(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)',
        
        # Format numéroté: NUM. DESCRIPTION ... MONTANT
        r'\d+\.?\s+([A-Za-zÀ-ÿ\s\-\/&\.]+)\s+(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)'
    ]
    
    # Mots-clés qui indiquent des montants à ignorer (totaux, sous-totaux, etc.)
    ignore_keywords = [
        'total', 'sous-total', 'sous total', 'montant ht', 'montant ttc', 
        'somme', 'report', 'solde', 'provision'
    ]
    
    # Rechercher tous les motifs
    all_matches = []
    for pattern in patterns:
        matches = re.finditer(pattern, charges_text)
        for match in matches:
            desc = match.group(1).strip()
            
            # Ignorer les lignes qui contiennent des mots-clés à ignorer
            if any(keyword in desc.lower() for keyword in ignore_keywords):
                continue
                
            # Extraire et nettoyer le montant
            montant_str = match.group(2).strip().replace(' ', '').replace(',', '.')
            
            try:
                montant = float(montant_str)
                # Ignorer les montants nuls ou négatifs
                if montant <= 0:
                    continue
                
                # Vérifier si cette charge existe déjà (éviter les doublons)
                if not any(c["poste"] == desc for c in charges):
                    charges.append({
                        "poste": desc,
                        "montant": montant
                    })
            except ValueError:
                continue
    
    # Si on n'a pas trouvé assez de charges, essayer une recherche plus agressive
    if len(charges) < 3:
        # Chercher simplement tous les nombres suivis ou précédés d'un texte
        aggressive_pattern = r'([A-Za-zÀ-ÿ\s\-\/&\.]{3,30})?(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)([A-Za-zÀ-ÿ\s\-\/&\.]{3,30})?'
        
        matches = re.finditer(aggressive_pattern, charges_text)
        for match in matches:
            before = match.group(1).strip() if match.group(1) else ""
            after = match.group(3).strip() if match.group(3) else ""
            
            # Déterminer la description (avant ou après le montant)
            if before and len(before) > len(after):
                desc = before
            else:
                desc = after
            
            # Si la description est vide ou trop courte, ignorer
            if not desc or len(desc) < 3:
                continue
                
            # Nettoyer et convertir le montant
            montant_str = match.group(2).strip().replace(' ', '').replace(',', '.')
            
            try:
                montant = float(montant_str)
                # Ignorer les montants trop petits ou trop grands
                if montant <= 0 or montant > 1000000:
                    continue
                
                # Vérifier si cette charge existe déjà (éviter les doublons)
                if not any(c["poste"] == desc for c in charges):
                    charges.append({
                        "poste": desc,
                        "montant": montant
                    })
            except ValueError:
                continue
    
    return charges
