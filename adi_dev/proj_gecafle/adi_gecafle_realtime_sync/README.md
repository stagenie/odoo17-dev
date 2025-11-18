# GeCaFle - Synchronisation Temps Réel (V2 Simplifiée)

## 🎯 Objectif

Synchronisation automatique des réceptions vers les ventes en temps réel.
**Plus besoin d'appuyer sur F5 !**

## ✨ Nouvelle Version V2

Cette version utilise une approche **simple et fiable**:
- ❌ Pas de bus Odoo (source de problèmes)
- ❌ Pas de notifications intrusives
- ✅ Polling léger toutes les 3 secondes
- ✅ Rafraîchissement silencieux
- ✅ Fonctionne toujours, même avec plusieurs onglets/postes

## 📦 Installation Rapide

```bash
cd /home/stadev/odoo17-dev/adi_dev/proj_gecafle
./update_realtime_sync.sh
```

Puis redémarrer Odoo:
```bash
python3 /home/stadev/odoo17-dev/odoo-bin -c /etc/odoo/odoo17.conf
```

## 🚀 Fonctionnement

### Ce qui se passe automatiquement:

1. **Création d'une réception** → Timestamp mis à jour → Ventes rafraîchies en 3s max
2. **Modification d'une réception** → Timestamp mis à jour → Ventes rafraîchies en 3s max
3. **Suppression d'une réception** → Timestamp mis à jour → Ventes rafraîchies en 3s max

### Dans la pratique:

**Avant:**
- Créer une réception
- Ouvrir une vente
- **Appuyer sur F5** 😫
- Voir les réceptions

**Après (V2):**
- Créer une réception
- Ouvrir une vente
- **Attendez 3 secondes** ⏱️
- ✅ Les réceptions sont **automatiquement** visibles ! 🎉

## 🔧 Architecture Technique

### Backend (Python)
- Stocke un timestamp à chaque modification de réception
- Paramètre système: `gecafle.reception.last_change`
- Méthode RPC: `get_last_change_timestamp()`

### Frontend (JavaScript)
- Polling RPC toutes les 3 secondes
- Compare le timestamp avec la dernière valeur connue
- Si changement: rafraîchit les vues de vente
- Pause automatique quand la fenêtre est cachée

### Communication
```
[Réception créée]
    ↓
[Timestamp mis à jour en DB]
    ↓
[Polling JavaScript détecte le changement]
    ↓
[Vues de vente rafraîchies silencieusement]
```

## 🧪 Test

1. Ouvrir deux onglets
2. **Onglet 1:** Ouvrir une liste ou formulaire de vente
3. **Onglet 2:** Créer une nouvelle réception
4. **Onglet 1:** Attendez max 3 secondes
5. ✅ La vue se rafraîchit automatiquement !

Console (F12):
```
[GeCaFle Sync] Service démarré
[GeCaFle Sync] Changement détecté! Rafraîchissement...
```

## 📊 Performance

- **Requête:** Très légère (~250 bytes toutes les 3s par utilisateur)
- **Impact:** Négligeable même avec 100 utilisateurs
- **Optimisation:** Pause automatique quand fenêtre cachée
- **Délai max:** 3 secondes

## 🐛 Dépannage

### Le rafraîchissement ne fonctionne pas:

1. Ouvrir la console (F12)
2. Vérifier les logs `[GeCaFle Sync]`
3. Vérifier le timestamp:
   ```sql
   SELECT value FROM ir_config_parameter
   WHERE key = 'gecafle.reception.last_change';
   ```

### Erreur RPC:

1. Vérifier que le module est bien installé
2. Redémarrer Odoo
3. Vider le cache navigateur (Ctrl+Shift+Delete)

## 📖 Documentation Complète

Voir: `../SYNCHRONISATION_SIMPLE_V2.md` dans le répertoire du projet

## 👨‍💻 Développé par

**ADICOPS** - info@adicops.com

## 📝 Version

**17.1.0 (V2 - Polling Simple)** - Compatible Odoo 17

---

✅ Simple | ✅ Fiable | ✅ Silencieux | ✅ Performant
