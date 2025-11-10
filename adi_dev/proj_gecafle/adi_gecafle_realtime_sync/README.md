# GeCaFle - Module de Synchronisation Temps Réel

## 🎯 Objectif
Ce module résout le problème de synchronisation entre les réceptions et les ventes en temps réel.
Plus besoin d'appuyer sur F5 pour voir les nouvelles réceptions dans les ventes !

## 📦 Installation

### Étape 1: Copier le module
```bash
cp -r adi_gecafle_realtime_sync /chemin/vers/odoo/addons/
```

### Étape 2: Redémarrer Odoo
```bash
sudo systemctl restart odoo
# ou
sudo service odoo restart
```

### Étape 3: Mettre à jour la liste des modules
1. Aller dans Odoo
2. Mode développeur: Settings → Activate Developer Mode
3. Apps → Update Apps List

### Étape 4: Installer le module
1. Apps → Rechercher "GeCaFle - Synchronisation Temps Réel"
2. Cliquer sur "Install"

## ⚙️ Configuration

### Vérifier que le Bus est activé
Le module utilise le système de Bus d'Odoo. Vérifiez dans le fichier de configuration Odoo:

```ini
[options]
# Pour WebSocket (recommandé, plus performant)
gevent_port = 8072

# OU pour Longpolling
longpolling_port = 8072
```

Redémarrer Odoo après modification.

## 🚀 Fonctionnement

### Ce qui se passe automatiquement:

1. **Création d'une réception** → Notification envoyée → Ventes rafraîchies
2. **Modification d'une réception** → Notification envoyée → Ventes rafraîchies
3. **Suppression d'une réception** → Notification envoyée → Ventes rafraîchies
4. **Ajout/modification de lignes** → Notification envoyée → Ventes rafraîchies

### Dans la pratique:

**Avant (avec ce problème):**
- Ouvrir réception
- Enregistrer
- Ouvrir vente dans nouvel onglet
- **Appuyer sur F5** 😫
- Voir les réceptions

**Après (avec ce module):**
- Ouvrir réception
- Enregistrer
- Ouvrir vente dans nouvel onglet
- ✅ Les réceptions sont **automatiquement** visibles ! 🎉

## 🔧 Architecture Technique

### Backend (Python)
- `models/reception_realtime.py`: Hérite du modèle `gecafle.reception`
- Override des méthodes `create()`, `write()`, `unlink()`
- Envoi de notifications via `bus.bus`

### Frontend (JavaScript)
- `realtime_sync_service.js`: Service qui écoute le bus
- `reception_realtime.js`: Patch des contrôleurs List/Form
- Auto-refresh des vues de vente

### Communication
```
[Réception créée] 
    ↓
[Python: _notify_reception_change()] 
    ↓
[bus.bus: Envoi notification] 
    ↓
[JavaScript: Service écoute] 
    ↓
[Vue de vente rafraîchie automatiquement]
```

## 🧪 Test

1. Ouvrir un onglet avec la liste des ventes
2. Ouvrir un autre onglet avec les réceptions
3. Créer une nouvelle réception
4. Revenir sur l'onglet des ventes
5. ✅ La liste est automatiquement rafraîchie !

## 📊 Performance

- Utilise le système natif de Bus d'Odoo (WebSocket/Longpolling)
- Consommation minimale de ressources
- Pas de polling HTTP continu
- Notifications ciblées uniquement

## 🐛 Dépannage

### Les notifications ne fonctionnent pas:
1. Vérifier que le module `bus` est installé
2. Vérifier la configuration du port dans odoo.conf
3. Vérifier les logs Odoo: `tail -f /var/log/odoo/odoo.log`
4. Vérifier la console JavaScript du navigateur (F12)

### Les vues ne se rafraîchissent pas:
1. Vider le cache du navigateur (Ctrl+Shift+Del)
2. Vérifier la console JavaScript (F12)
3. Vérifier que le module est bien installé

## 👨‍💻 Développé par
**ADICOPS** - info@adicops.com

## 📝 Version
17.1.0 - Compatible Odoo 17
