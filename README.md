# PDF Studio Express

Logiciel libre, complet et léger pour modifier, organiser, fusionner, découper, protéger et éditer le texte de documents PDF (y compris les documents scannés via OCR).

---

## Fonctionnalités principales

1. **Modification de texte (avec préservation de la typographie)**
   - Détection automatique de la police, de la taille, du style et de la couleur d'origine.
   - Édition de lignes de texte individuelles.
   - Outil de recherche et remplacement global ou par page.
   - Support des documents scannés et des images grâce au moteur OCR intégré (RapidOCR).

2. **Organiseur visuel de pages**
   - Affichage des vignettes de chaque page en temps réel.
   - Rotation (+90°, -90°, 180°).
   - Réorganisation de l'ordre des pages par déplacement.
   - Suppression et extraction sélective de pages.

3. **Fusion et découpage**
   - Assemblage de plusieurs fichiers PDF en un document unique.
   - Découpage par plages de pages, extraction page par page, ou par lots réguliers.

4. **Filigranes et numérotation**
   - Insertion de mentions textuelles personnalisées (angle, taille, couleur, opacité).
   - Numérotation automatique des pages avec choix de l'emplacement et du format.

5. **Conversion d'images**
   - Export de pages PDF sous forme d'images haute résolution (PNG / JPG).
   - Création de PDF à partir d'une collection d'images.

6. **Sécurité et optimisation**
   - Chiffrement AES-256 avec mot de passe.
   - Déverrouillage de documents protégés.
   - Compression et réduction du poids des fichiers.
   - Extraction intégrale du texte brut.

---

## Installation et démarrage

### Prérequis
- Python 3.10 ou supérieur

### Installation des dépendances
```bash
pip install -r requirements.txt
```

### Lancement
- **Version bureau (Interface graphique)** :
  Double-cliquer sur `Lancer_Editeur_PDF.bat` ou exécuter :
  ```bash
  python app_gui.py
  ```
- **Version Web (Navigateur)** :
  Double-cliquer sur `Lancer_Version_Web.bat` ou exécuter :
  ```bash
  streamlit run app_web.py
  ```

---

## Structure du projet

- `app_gui.py` : Application de bureau principale (Tkinter).
- `app_web.py` : Interface web alternative (Streamlit).
- `pdf_core.py` : Moteur de manipulation de documents et intégration OCR.
- `requirements.txt` : Liste des bibliothèques nécessaires.
- `Lancer_Editeur_PDF.bat` : Script de démarrage pour l'application bureau sous Windows.
- `Lancer_Version_Web.bat` : Script de démarrage pour la version web.
- `Lancer_Silencieux.vbs` : Lanceur sans console visible.
- `exemple_document.pdf` : Fichier de démonstration inclus pour les tests.
