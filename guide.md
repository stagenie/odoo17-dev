# Guide Git - Projet odoo17-dev

Ce guide vous accompagne dans la gestion quotidienne de votre dépôt Git pour le projet Odoo 17.

## Table des matières
- [Workflow quotidien](#workflow-quotidien)
- [Commandes de base](#commandes-de-base)
- [Exemples pratiques](#exemples-pratiques)
- [Bonnes pratiques](#bonnes-pratiques)
- [Commandes utiles](#commandes-utiles)
- [En cas de problème](#en-cas-de-problème)

---

## Workflow quotidien

### 1. Vérifier les fichiers modifiés
```bash
git status
```
Cette commande affiche :
- Les fichiers modifiés
- Les fichiers ajoutés
- Les fichiers supprimés
- Les fichiers non suivis

### 2. Ajouter les fichiers au staging

**Option A - Ajouter tous les fichiers modifiés :**
```bash
git add .
```

**Option B - Ajouter des fichiers spécifiques :**
```bash
git add adi_dev/adi_dev1/mon_module/__manifest__.py
git add adi_dev/adi_dev1/mon_module/models/mon_model.py
```

**Option C - Ajouter un dossier entier :**
```bash
git add adi_dev/adi_dev1/mon_module/
```

### 3. Créer un commit avec un message descriptif
```bash
git commit -m "Description claire de ce que vous avez modifié"
```

**Exemples de bons messages :**
```bash
git commit -m "Ajout du module adi_inventory_management"
git commit -m "Fix: Correction du calcul des prix dans adi_cost_management"
git commit -m "Update: Amélioration du rapport de vente dans proj_gecafle"
git commit -m "Refactor: Optimisation du code dans adi_gecafle_base_stock"
```

### 4. Pousser vers GitHub
```bash
git push
```
ou de manière explicite :
```bash
git push origin main
```

### Workflow complet en une seule ligne
```bash
git add . && git commit -m "Votre message descriptif" && git push
```

---

## Commandes de base

### Voir les modifications
```bash
# Voir toutes les modifications non commitées
git diff

# Voir les modifications d'un fichier spécifique
git diff chemin/vers/fichier.py

# Voir les fichiers modifiés (noms seulement)
git diff --name-only

# Voir les différences après staging
git diff --staged
```

### Voir l'historique
```bash
# Voir tous les commits
git log

# Version condensée (une ligne par commit)
git log --oneline

# Les 10 derniers commits
git log --oneline -10

# Voir les modifications d'un commit spécifique
git show <commit-id>

# Historique avec graphique
git log --oneline --graph --all
```

### Annuler des modifications

**Avant le commit (fichier modifié mais pas encore ajouté) :**
```bash
# Annuler les modifications d'un fichier
git checkout -- nom_fichier.py

# Annuler toutes les modifications
git checkout -- .
```

**Après git add (retirer du staging) :**
```bash
# Retirer un fichier du staging
git reset nom_fichier.py

# Retirer tous les fichiers du staging
git reset
```

**Annuler le dernier commit (garder les modifications) :**
```bash
git reset --soft HEAD~1
```

**Annuler le dernier commit (supprimer les modifications) :**
```bash
git reset --hard HEAD~1
```

---

## Exemples pratiques

### Scénario 1 : Modification d'un module existant
```bash
# Vous avez modifié des fichiers dans adi_gecafle_vente
git status                                          # Voir les modifications
git add adi_dev/proj_gecafle/adi_gecafle_vente/     # Ajouter le module
git commit -m "Update: Ajout de nouveaux champs dans adi_gecafle_vente"
git push
```

### Scénario 2 : Création d'un nouveau module
```bash
# Vous venez de créer un nouveau module
git status
git add adi_dev/adi_dev1/mon_nouveau_module/
git commit -m "Ajout du module mon_nouveau_module pour la gestion des stocks"
git push
```

### Scénario 3 : Modifications multiples
```bash
# Vous avez modifié plusieurs modules
git add .
git commit -m "Mise à jour de plusieurs modules: adi_vente, adi_stock, adi_reports"
git push
```

### Scénario 4 : Correction de bug
```bash
git add adi_dev/adi_dev2/adi_cost_management/models/
git commit -m "Fix: Correction du calcul du prix de revient dans adi_cost_management"
git push
```

### Scénario 5 : Amélioration de rapport
```bash
git add adi_dev/proj_gecafle/adi_arabic_reports/
git commit -m "Update: Amélioration du format des rapports arabes"
git push
```

---

## Bonnes pratiques

### 1. Messages de commit clairs
Utilisez des préfixes pour clarifier le type de modification :
- `Add:` - Ajout de nouvelles fonctionnalités
- `Update:` - Mise à jour de fonctionnalités existantes
- `Fix:` - Correction de bugs
- `Refactor:` - Refactorisation du code
- `Docs:` - Modification de documentation
- `Style:` - Changements de formatage (sans impact fonctionnel)
- `Test:` - Ajout ou modification de tests

### 2. Commits réguliers
- Ne pas attendre d'avoir trop de modifications
- Faire un commit après chaque fonctionnalité terminée
- Pousser régulièrement vers GitHub (backup)

### 3. Commits atomiques
- Un commit = une modification logique
- Éviter de mélanger plusieurs types de modifications

### 4. Vérifier avant de pousser
```bash
git status          # Voir ce qui va être commité
git diff            # Voir les modifications en détail
git log -1          # Voir le dernier commit
```

### 5. Ne pas commiter certains fichiers
Le fichier `.gitignore` est déjà configuré pour ignorer :
- `odoo.conf` (contient des mots de passe)
- `*.pyc`, `__pycache__/` (fichiers compilés Python)
- `filestore/`, `sessions/` (données Odoo)
- `*.log` (fichiers de logs)
- Les fichiers Odoo standard (`addons/`, `odoo/`, `odoo-bin`)

---

## Commandes utiles

### Récupérer les dernières modifications depuis GitHub
```bash
git pull
```

### Voir la configuration du dépôt
```bash
# Voir l'URL du dépôt distant
git remote -v

# Voir la configuration complète
git config --list
```

### Créer une nouvelle branche (pour développement)
```bash
# Créer et basculer sur une nouvelle branche
git checkout -b ma-nouvelle-fonctionnalite

# Pousser la nouvelle branche vers GitHub
git push -u origin ma-nouvelle-fonctionnalite

# Revenir à la branche main
git checkout main
```

### Fusionner une branche
```bash
# Se placer sur main
git checkout main

# Fusionner la branche de développement
git merge ma-nouvelle-fonctionnalite

# Pousser les modifications
git push
```

### Voir les branches
```bash
# Lister les branches locales
git branch

# Lister toutes les branches (locales et distantes)
git branch -a
```

### Mettre à jour depuis GitHub avant de pousser
```bash
# Récupérer et fusionner les modifications
git pull

# Ajouter vos modifications
git add .
git commit -m "Mon message"
git push
```

---

## En cas de problème

### Conflit lors du push
Si vous obtenez une erreur lors du `git push` :
```bash
# Récupérer les modifications distantes
git pull

# Résoudre les conflits si nécessaire
# Puis commiter et pousser
git add .
git commit -m "Résolution des conflits"
git push
```

### Vous avez commité par erreur
```bash
# Annuler le dernier commit (garder les modifications)
git reset --soft HEAD~1

# Modifier ce qui doit l'être
# Puis recommiter
git add .
git commit -m "Nouveau message correct"
git push
```

### Vous voulez voir ce qui a changé dans un fichier
```bash
# Voir l'historique d'un fichier
git log -- chemin/vers/fichier.py

# Voir les modifications d'un fichier dans un commit
git show <commit-id>:chemin/vers/fichier.py
```

### Récupérer un fichier d'une ancienne version
```bash
# Récupérer un fichier d'un commit spécifique
git checkout <commit-id> -- chemin/vers/fichier.py
```

### Ignorer des modifications temporaires
```bash
# Mettre de côté vos modifications temporairement
git stash

# Récupérer les modifications mises de côté
git stash pop
```

---

## Structure du projet

```
odoo17-dev/
├── adi_dev/
│   ├── adi_dev1/          # Modules de développement (rapports, factures, etc.)
│   ├── adi_dev2/          # Modules de production et gestion des coûts
│   ├── proj_gecafle/      # Modules spécifiques au projet Gecafle
│   └── ai_modules/        # Modules d'intelligence artificielle
├── adi_third_party/       # Modules tiers
├── adi_premium/           # Modules premium
├── .gitignore             # Fichiers à ignorer par git
└── guide.md               # Ce guide

```

---

## Aide rapide

| Commande | Description |
|----------|-------------|
| `git status` | Voir l'état actuel |
| `git add .` | Ajouter tous les fichiers |
| `git commit -m "msg"` | Créer un commit |
| `git push` | Envoyer vers GitHub |
| `git pull` | Récupérer depuis GitHub |
| `git log` | Voir l'historique |
| `git diff` | Voir les modifications |

---

## Dépôt GitHub

**URL du dépôt :** https://github.com/stagenie/odoo17-dev

**Clone du dépôt (si besoin) :**
```bash
git clone git@github.com:stagenie/odoo17-dev.git
```

---

**Dernière mise à jour :** 2025-11-10
