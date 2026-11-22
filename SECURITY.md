# Guide d'Audit et Politique de Sécurité - PDF Studio Express

Ce document synthétise les points d'entrée critiques, l'architecture de sécurité et les fichiers prioritaires à auditer pour tout développeur ou auditeur de sécurité.

---

## 🎯 Périmètre et Fichiers Prioritaires pour l'Audit

Pour un audit de sécurité efficace, voici les **4 fichiers critiques** classés par niveau de priorité :

| Priorité | Fichier | Rôle dans l'application | Points clés à auditer |
| :--- | :--- | :--- | :--- |
| **P1 (Critique)** | [`pdf_core.py`](pdf_core.py) | **Moteur de traitement PDF & OCR** | • Traitement des fichiers PDF non fiables via PyMuPDF.<br>• Gestion de la mémoire et parsing des flux graphiques.<br>• Chiffrement AES-256 (`protect_pdf` / `unlock_pdf`).<br>• Exécution locale du modèle ONNX (`RapidOCR`).<br>• Prévention des dénis de service (bombes PDF). |
| **P2 (Élevée)** | [`app_web.py`](app_web.py) | **Interface Web (Streamlit)** | • Validation des types de fichiers uploadés.<br>• Isolation et suppression garantie des fichiers temporaires dans `%TEMP%`.<br>• Protection contre les attaques de type Path Traversal.<br>• Gestion des sessions et des tampons mémoire (`BytesIO`). |
| **P3 (Moyenne)** | [`app_gui.py`](app_gui.py) | **Interface Bureau (Tkinter)** | • Gestion du cycle de vie des fichiers temporaires de travail.<br>• Nettoyage à la fermeture de l'application (`WM_DELETE_WINDOW`).<br>• Gestion des mots de passe en mémoire lors de la saisie utilisateur. |
| **P4 (Chaîne logistique)** | [`requirements.txt`](requirements.txt) | **Dépendances tierces** | • Vérification des versions des bibliothèques (`pip-audit` / CVE).<br>• Intégrité des modèles ONNX et des paquets Python. |

---

## 🛡️ Modèle de Menace et Principes de Conception

1. **Traitement 100% Local (Zéro Télémétrie)** :
   - L'application n'effectue aucun appel réseau sortant.
   - Tous les traitements PDF et les inférences OCR sont exécutés localement sur le processeur (CPU).
   - Les documents de l'utilisateur ne quittent jamais la machine hôte.

2. **Cycle de vie des fichiers temporaires** :
   - Chaque modification crée un fichier temporaire isolé via `tempfile.NamedTemporaryFile`.
   - Les fichiers temporaires intermédiaires sont immédiatement supprimés dès qu'une nouvelle version est générée ou lors de la fermeture de l'application.

3. **Chiffrement** :
   - Utilisation du standard de l'industrie **AES-256 bits** (`fitz.PDF_ENCRYPT_AES_256`) pour le verrouillage des documents sensibles.

---

## 🔍 Outils recommandés pour auditer le projet

Les auditeurs peuvent exécuter les commandes suivantes pour un audit automatisé du code source :

### 1. Analyse statique de vulnérabilités (SAST avec Bandit) :
```bash
pip install bandit
bandit -r pdf_core.py app_gui.py app_web.py
```

### 2. Audit des dépendances (CVE connues) :
```bash
pip install pip-audit
pip-audit -r requirements.txt
```

### 3. Analyse de qualité et typage :
```bash
pip install flake8
flake8 pdf_core.py app_gui.py --max-line-length=120
```

---

## 📩 Signalement de Vulnérabilité

Si vous découvrez une faille de sécurité dans ce projet, merci de ne pas ouvrir d'issue publique. Veuillez contacter l'auteur via GitHub ou par courriel.
