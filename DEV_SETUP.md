# Odoo 17 - Environnement de Développement

## ⚠️ Important

Ce dépôt contient **uniquement les modules personnalisés** ADICOPS pour Odoo 17.
Le code source d'Odoo 17 doit être installé séparément.

## Configuration

- **Python**: 3.12.3
- **PostgreSQL**: 16.10
- **Odoo**: 17.0 (à installer séparément)
- **Environnement virtuel**: `/home/stadev/odoo17-dev/venv`
- **Port HTTP**: 8017

## Installation d'Odoo 17

### Option 1: Cloner le dépôt officiel Odoo (Recommandé)

```bash
cd /home/stadev
git clone https://github.com/odoo/odoo.git --depth 1 --branch 17.0 --single-branch odoo17
```

### Option 2: Installer via pip

```bash
cd /home/stadev/odoo17-dev
source venv/bin/activate
pip install odoo==17.0
```

## Structure des dossiers

```
/home/stadev/
├── odoo17/                # Code source Odoo 17 (à installer)
│   ├── odoo/              # Core Odoo
│   ├── addons/            # Modules officiels
│   └── odoo-bin           # Script de lancement
│
└── odoo17-dev/            # Ce dépôt - modules personnalisés
    ├── adi_dev/           # Modules de développement
    ├── adi_premium/       # Modules premium
    ├── adi_third_party/   # Modules tiers
    ├── venv/              # Environnement virtuel
    └── odoo.conf          # Configuration
```

## Configuration

Après avoir installé Odoo 17, éditez `odoo.conf` et mettez à jour le chemin `addons_path`:

```ini
addons_path = /home/stadev/odoo17/addons,/home/stadev/odoo17-dev/adi_dev/...
```

## Démarrer Odoo 17

### Via ligne de commande

```bash
cd /home/stadev/odoo17-dev
source venv/bin/activate
python /home/stadev/odoo17/odoo-bin -c odoo.conf
```

### Via VS Code

1. Ouvrir le projet: `code /home/stadev/odoo17-dev`
2. Appuyer sur `F5` ou aller dans "Run and Debug"
3. Sélectionner "Odoo 17 - Debug"

## Créer une base de données

Le filtre de base de données est configuré pour `^o17_`, donc les bases doivent commencer par "o17_".

```bash
source venv/bin/activate
python /home/stadev/odoo17/odoo-bin -c odoo.conf -d o17_dev -i base
```

Ou via l'interface web: http://localhost:8017

## Mettre à jour les modules

```bash
python /home/stadev/odoo17/odoo-bin -c odoo.conf -d o17_dev -u nom_du_module
```

## Synchronisation avec GitHub

Ce dépôt contient uniquement vos modules personnalisés.

```bash
cd /home/stadev/odoo17-dev
git status
git add .
git commit -m "Description des changements"
git push origin main
```

## Extensions VS Code recommandées

Les extensions seront suggérées automatiquement:
- Python
- Pylance
- XML
- Odoo Snippets
- GitLens

## Logs

Les logs d'Odoo sont dans: `/home/stadev/odoo17-dev/odoo.log`

## Ports des différentes versions

- **Odoo 15**: 8069
- **Odoo 17**: 8017
- **Odoo 18**: 8118

Tous peuvent fonctionner simultanément grâce aux ports différents.

## Troubleshooting

### Odoo 17 non trouvé

Vérifiez que vous avez bien installé Odoo 17:
```bash
ls -la /home/stadev/odoo17
```

Si le dossier n'existe pas, suivez les instructions d'installation ci-dessus.

### Problème de dépendances Python

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Port déjà utilisé

Le port 8017 est configuré par défaut. Pour le modifier, éditez `odoo.conf` (ligne `http_port`)

## Conventions de commit

- `[ADD]` : Nouveau module
- `[FIX]` : Correction de bug
- `[IMP]` : Amélioration
- `[REF]` : Refactoring
