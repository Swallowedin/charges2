"""
Module pour la création de graphiques et visualisations.
"""
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

def plot_themes_chart(themes):
    """
    Crée un graphique des thèmes principaux.
    
    Args:
        themes: Liste des thèmes à visualiser
        
    Returns:
        Figure matplotlib du graphique
    """
    if not themes:
        return None

    # Préparer les données (tous les thèmes ont le même poids par défaut)
    labels = themes
    sizes = [1] * len(themes)

    # Graphique camembert
    fig, ax = plt.subplots(figsize=(10, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=labels, 
        autopct='%1.1f%%',
        textprops={'fontsize': 9}
    )

    # Ajuster les propriétés du texte
    plt.setp(autotexts, size=8, weight='bold')
    plt.setp(texts, size=8)

    plt.title('Thèmes principaux identifiés')
    plt.tight_layout()
    
    return fig

def plot_conformity_gauge(conformity_level):
    """
    Crée un graphique de jauge pour visualiser le niveau de conformité.
    
    Args:
        conformity_level: Niveau de conformité (0-100)
        
    Returns:
        Figure matplotlib du graphique de jauge
    """
    # Limiter la valeur entre 0 et 100
    conformity_level = max(0, min(100, conformity_level))
    
    # Créer la figure et les axes
    fig, ax = plt.subplots(figsize=(10, 5), subplot_kw={'projection': 'polar'})
    
    # Paramètres de la jauge
    theta = np.linspace(0, np.pi, 100)
    r = 1.0  # Rayon fixe
    
    # Créer les segments de la jauge
    segments = 5
    width = np.pi / segments
    colors = ['#FF6B6B', '#FFD166', '#06D6A0', '#118AB2', '#073B4C']
    
    for i in range(segments):
        start_angle = i * width
        end_angle = (i + 1) * width
        segment_theta = np.linspace(start_angle, end_angle, 20)
        ax.fill_between(segment_theta, 0, r, color=colors[i], alpha=0.8)
    
    # Calculer la position de l'aiguille
    needle_angle = conformity_level / 100 * np.pi
    ax.plot([0, needle_angle], [0, 0.8], 'k-', linewidth=3)
    
    # Ajouter un cercle à la base de l'aiguille
    ax.add_patch(plt.Circle((0, 0), 0.1, color='k', zorder=10))
    
    # Personnaliser l'apparence du graphique
    ax.set_axis_off()  # Masquer les axes
    
    # Ajouter des étiquettes pour les niveaux
    labels = ['Faible', 'Moyen', 'Bon', 'Très bon', 'Excellent']
    for i, label in enumerate(labels):
        angle = (i + 0.5) * width
        x = 1.2 * np.cos(angle)
        y = 1.2 * np.sin(angle)
        ax.text(angle, 1.2, label, ha='center', va='center', fontsize=9)
    
    # Ajouter la valeur numérique au centre
    ax.text(0, -0.2, f'{conformity_level}%', ha='center', va='center', fontsize=16, fontweight='bold')
    
    return fig

def plot_charges_distribution(charges_facturees):
    """
    Crée un diagramme à barres horizontales pour visualiser la distribution des charges.
    
    Args:
        charges_facturees: Liste des charges facturées
        
    Returns:
        Figure matplotlib du graphique
    """
    if not charges_facturees:
        return None
        
    # Extraire les données
    labels = [charge["poste"] for charge in charges_facturees]
    values = [charge["montant"] for charge in charges_facturees]
    
    # Trier par montant (du plus grand au plus petit)
    sorted_indices = np.argsort(values)[::-1]
    labels = [labels[i] for i in sorted_indices]
    values = [values[i] for i in sorted_indices]
    
    # Limiter à 10 catégories pour la lisibilité
    if len(labels) > 10:
        labels = labels[:9] + ["Autres"]
        values = values[:9] + [sum(values[9:])]
    
    # Créer le graphique
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Définir une palette de couleurs
    cmap = plt.cm.Blues
    colors = cmap(np.linspace(0.4, 0.8, len(labels)))
    
    # Créer les barres horizontales
    y_pos = range(len(labels))
    ax.barh(y_pos, values, color=colors)
    
    # Personnaliser l'apparence
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # Pour avoir la plus grande valeur en haut
    ax.set_xlabel('Montant (€)')
    ax.set_title('Distribution des charges locatives')
    
    # Ajouter les valeurs sur les barres
    for i, v in enumerate(values):
        ax.text(v + max(values) * 0.01, i, f'{v:.2f} €', va='center')
    
    plt.tight_layout()
    return fig

def plot_conformity_by_category(charges_facturees):
    """
    Crée un graphique en barres groupées montrant la conformité par catégorie.
    
    Args:
        charges_facturees: Liste des charges facturées avec leurs statuts de conformité
        
    Returns:
        Figure matplotlib du graphique
    """
    if not charges_facturees:
        return None
        
    # Compter les charges par statut de conformité
    conformity_status = {}
    for charge in charges_facturees:
        status = charge.get("conformite", "à vérifier")
        if status not in conformity_status:
            conformity_status[status] = 0
        conformity_status[status] += 1
    
    # Créer le graphique
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Définir les couleurs par statut
    colors = {
        "conforme": "#06D6A0",
        "à vérifier": "#FFD166",
        "non conforme": "#FF6B6B"
    }
    
    # Créer le graphique en barres
    labels = list(conformity_status.keys())
    counts = list(conformity_status.values())
    bar_colors = [colors.get(status, "#CCCCCC") for status in labels]
    
    bars = ax.bar(labels, counts, color=bar_colors)
    
    # Personnaliser l'apparence
    ax.set_ylabel('Nombre de charges')
    ax.set_title('Répartition des charges par statut de conformité')
    
    # Ajouter les valeurs sur les barres
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.0f}', ha='center', va='bottom')
    
    plt.tight_layout()
    return fig
