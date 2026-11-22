"""
Génère un fichier PDF d'exemple pour tester immédiatement le logiciel.
"""

import fitz

def create_sample():
    doc = fitz.open()
    
    pages_data = [
        ("Bienvenue dans votre Éditeur PDF", "Ce document est un exemple prêt à l'emploi pour tester les fonctionnalités.\n\nVous pouvez :\n- Tourner cette page à 90° ou 180°\n- Réorganiser l'ordre des pages\n- Supprimer des pages inutiles\n- Fusionner avec un autre PDF\n- Ajouter un filigrane (ex: CONFIDENTIEL)\n- Numéroter automatiquement les pages\n- Protéger avec un mot de passe"),
        ("Page 2 : Analyse & Données", "Section 1 : Synthèse des modifications apportées aux documents.\nSection 2 : Les fonctionnalités visuelles vous permettent de voir les miniatures de chaque page en direct.\n\nEssayez de déplacer cette page en première position !"),
        ("Page 3 : Facture & Détails", "Facture N° 2026-0042\nDate : Novembre 2026\nClient : Démonstration\nMontant Total : 150,00 € TTC\n\nVous pouvez apposer un tampon 'PAYÉ' ou 'COPIE' sur cette page."),
        ("Page 4 : Page à supprimer", "Cette page est destinée à être supprimée lors de vos tests.\nSélectionnez cette page et cliquez sur le bouton 'Supprimer' !"),
        ("Page 5 : Conclusion & Contact", "Félicitations ! Vous maîtrisez maintenant les outils PDF.\nVous pouvez convertir ce PDF en images PNG ou le compresser.")
    ]
    
    colors = [
        (0.1, 0.3, 0.7),
        (0.2, 0.5, 0.2),
        (0.7, 0.3, 0.1),
        (0.6, 0.1, 0.1),
        (0.3, 0.2, 0.6)
    ]
    
    for i, (title, content) in enumerate(pages_data):
        page = doc.new_page()
        # Header banner
        page.draw_rect(fitz.Rect(0, 0, page.rect.width, 80), color=None, fill=colors[i % len(colors)])
        page.insert_text(fitz.Point(40, 50), title, fontsize=20, color=(1, 1, 1))
        
        # Content box
        page.insert_textbox(
            fitz.Rect(50, 120, page.rect.width - 50, page.rect.height - 100),
            content,
            fontsize=13,
            color=(0.1, 0.1, 0.1)
        )
        
        # Footer
        page.insert_text(
            fitz.Point(page.rect.width / 2 - 40, page.rect.height - 30),
            f"- Page {i + 1} d'exemple -",
            fontsize=10,
            color=(0.5, 0.5, 0.5)
        )
        
    doc.save("exemple_document.pdf")
    doc.close()
    print("Fichier 'exemple_document.pdf' créé avec succès !")

if __name__ == "__main__":
    create_sample()
