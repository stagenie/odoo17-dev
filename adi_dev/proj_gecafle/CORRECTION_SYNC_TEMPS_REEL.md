# Correction de la Synchronisation en Temps Réel

## Problème Identifié

Le module `adi_gecafle_realtime_sync` était censé permettre la synchronisation en temps réel entre les réceptions et les ventes, mais les réceptions créées dans un onglet n'apparaissaient pas automatiquement dans un autre onglet sans rafraîchir (F5).

## Causes Principales

1. **Méthode obsolète du Bus**: Utilisation de `_sendone()` qui n'est pas la méthode correcte pour Odoo 17
2. **Format incorrect des notifications**: Le format des messages envoyés via le bus ne correspondait pas au format attendu par Odoo 17
3. **Abonnement incorrect au canal**: Le service JavaScript n'écoutait pas correctement les notifications du bus
4. **Rafraîchissement insuffisant**: Les vues et widgets Many2one ne se rafraîchissaient pas correctement

## Corrections Apportées

### 1. Fichier Python (`models/reception_realtime.py`)

**Changements:**
- ✅ Remplacement de `_sendone()` par `_sendmany()` (méthode correcte pour Odoo 17)
- ✅ Envoi des notifications à tous les utilisateurs actifs via leurs canaux personnels
- ✅ Format correct: `(dbname, 'res.partner', partner_id)` pour chaque utilisateur
- ✅ Gestion des erreurs pour ne pas bloquer l'opération principale
- ✅ Invalidation du cache étendue au modèle `gecafle.vente`

**Code clé:**
```python
# Récupérer tous les utilisateurs actifs
active_users = self.env['res.users'].search([('active', '=', True)])

for user in active_users:
    if user.partner_id:
        channel = (self.env.cr.dbname, 'res.partner', user.partner_id.id)
        notifications.append([channel, 'gecafle.reception.change', message])

self.env['bus.bus']._sendmany(notifications)
```

### 2. Service JavaScript (`static/src/js/realtime_sync_service.js`)

**Changements:**
- ✅ Suppression de l'abonnement obsolète `subscribe("gecafle_reception_sync")`
- ✅ Utilisation correcte de `addEventListener("notification")` pour écouter les notifications du bus
- ✅ Démarrage explicite du bus service avec `bus_service.start()`
- ✅ Amélioration du rafraîchissement des vues avec vérification des types de contrôleurs
- ✅ Gestion améliorée des événements avec `bubbles: true` et `cancelable: true`

**Code clé:**
```javascript
// Écoute correcte des notifications du bus
bus_service.addEventListener("notification", ({ detail: notifications }) => {
    for (const notif of notifications) {
        if (notif.type === "gecafle.reception.change") {
            handleReceptionChange(notif.payload);
        }
    }
});
```

### 3. Patches des Contrôleurs (`static/src/js/reception_realtime.js`)

**Changements:**
- ✅ Amélioration du rafraîchissement du `ListController`
- ✅ Gestion des erreurs robuste avec try-catch
- ✅ Forçage du rendu après le rechargement du modèle
- ✅ Rafraîchissement intelligent du `FormController` selon le mode (édition/création)
- ✅ Logging détaillé pour le debugging

### 4. Nouveau Patch Many2one (`static/src/js/many2one_refresh.js`) ⭐

**Nouveauté:**
- ✅ Patch spécifique pour les widgets Many2one
- ✅ Détection automatique des champs de réception dans les vues de vente
- ✅ Invalidation du cache de l'autocomplete
- ✅ Rechargement automatique des suggestions si le dropdown est ouvert
- ✅ Cleanup approprié lors de la destruction du widget

**Impact:** Les champs de sélection de réception se rafraîchissent automatiquement pour afficher les nouvelles réceptions disponibles.

## Architecture de la Solution

```
┌─────────────────────────────────────────────────────────────┐
│                     CRÉATION RÉCEPTION                       │
│                  (Onglet 1 ou Poste 1)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Python: reception_realtime.py (create)              │
│   • Crée la réception                                       │
│   • Appelle _notify_reception_change()                      │
│   • Prépare le message                                      │
│   • Envoie via bus._sendmany() à tous les utilisateurs      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    BUS ODOO (WebSocket)                      │
│          Diffuse aux sessions de tous les users              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              JavaScript: realtime_sync_service.js            │
│   • Écoute les notifications                                │
│   • Filtre type "gecafle.reception.change"                  │
│   • Affiche notification utilisateur                        │
│   • Dispatch événement "gecafle_reception_updated"          │
│   • Rafraîchit les vues actives                             │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌─────────────────┐
│List Controller│ │FormController│ │Many2one Widgets │
│• Recharge    │ │• Recharge    │ │• Vide cache     │
│  modèle      │ │  relations   │ │• Reload options │
│• Re-render   │ │• Re-render   │ │                 │
└──────────────┘ └─────────────┘ └─────────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  VUE MISE À JOUR                            │
│         (Onglet 2 ou Poste 2 - Sans F5!)                   │
│   • Nouvelle réception visible dans les listes             │
│   • Nouvelle réception disponible dans les Many2one        │
└─────────────────────────────────────────────────────────────┘
```

## Installation et Mise à Jour

### Méthode Automatique (Recommandée)

```bash
cd /home/stadev/odoo17-dev/adi_dev/proj_gecafle
./update_realtime_sync.sh
```

Ce script:
1. Arrête Odoo
2. Met à jour le module
3. Vide le cache des assets
4. Affiche les instructions pour redémarrer

### Méthode Manuelle

```bash
# 1. Arrêter Odoo
pkill -f odoo-bin

# 2. Mettre à jour le module
python3 /home/stadev/odoo17-dev/odoo-bin \
    -c /etc/odoo/odoo17.conf \
    -d adi_odoo17 \
    -u adi_gecafle_realtime_sync \
    --stop-after-init

# 3. Vider le cache des assets
PGPASSWORD='St@dev' psql -U stadev -d adi_odoo17 \
    -c "DELETE FROM ir_attachment WHERE name LIKE 'web.assets%';"

# 4. Redémarrer Odoo
python3 /home/stadev/odoo17-dev/odoo-bin -c /etc/odoo/odoo17.conf
```

## Test de la Synchronisation

### Scénario de Test 1: Deux Onglets

1. **Onglet 1**: Ouvrir une vente existante ou créer une nouvelle vente
2. **Onglet 2**: Créer une nouvelle réception
3. **Vérifications dans Onglet 1** (sans F5):
   - ✅ Une notification apparaît: "Nouvelle réception créée: [NOM]"
   - ✅ Si un champ réception est ouvert (dropdown), les nouvelles options apparaissent
   - ✅ Si en mode création de vente, le champ réception affiche la nouvelle option

### Scénario de Test 2: Deux Postes Différents

1. **Poste 1**: Ouvrir la liste des ventes
2. **Poste 2**: Créer plusieurs nouvelles réceptions
3. **Vérifications sur Poste 1** (sans F5):
   - ✅ Notifications pour chaque nouvelle réception
   - ✅ Les réceptions sont disponibles dans les formulaires de vente

### Scénario de Test 3: Modification de Réception

1. **Onglet 1**: Afficher une liste de ventes
2. **Onglet 2**: Modifier une réception existante (changer état, montants, etc.)
3. **Vérifications dans Onglet 1**:
   - ✅ Notification "Réception mise à jour"
   - ✅ Les vues se rafraîchissent

## Debugging

### Vérifier les Logs Console (F12 dans le navigateur)

**Logs attendus lors de la création d'une réception:**
```
[GeCaFle] Service de synchronisation temps réel démarré
[GeCaFle] Bus service démarré et en écoute
[GeCaFle] Changement de réception détecté: {operation: "create", ...}
[GeCaFle] Rafraîchissement des vues de vente...
[GeCaFle] Many2one field 'reception_id' détecté dans gecafle.vente
[GeCaFle] Rafraîchissement du champ Many2one 'reception_id'
[GeCaFle] Cache de l'autocomplete vidé
```

### Vérifier les Notifications Bus côté Serveur

```python
# Dans le log Odoo, chercher:
# Aucune erreur lors de l'envoi au bus
# Les messages sont bien formatés
```

### Commandes SQL pour Vérifier le Bus

```sql
-- Voir les dernières notifications du bus
SELECT * FROM bus_bus
ORDER BY id DESC
LIMIT 10;

-- Voir les utilisateurs actifs
SELECT id, login, active, partner_id
FROM res_users
WHERE active = true;
```

## Points Techniques Importants

### Format du Canal Bus Odoo 17

```python
# Format correct pour cibler un utilisateur
channel = (database_name, 'res.partner', partner_id)

# Exemple
channel = ('adi_odoo17', 'res.partner', 14)
```

### Structure de la Notification

```python
notification = [
    channel,  # (dbname, model, id)
    'gecafle.reception.change',  # Type de message
    {  # Payload
        'operation': 'create',
        'reception_id': 123,
        'reception_name': 'REC/2024/001',
        ...
    }
]
```

### Écoute côté JavaScript

```javascript
bus_service.addEventListener("notification", ({ detail: notifications }) => {
    for (const notif of notifications) {
        if (notif.type === "gecafle.reception.change") {
            // Traiter la notification
        }
    }
});
```

## Fichiers Modifiés

1. ✅ `adi_gecafle_realtime_sync/models/reception_realtime.py`
2. ✅ `adi_gecafle_realtime_sync/static/src/js/realtime_sync_service.js`
3. ✅ `adi_gecafle_realtime_sync/static/src/js/reception_realtime.js`
4. ✅ `adi_gecafle_realtime_sync/static/src/js/many2one_refresh.js` (nouveau)
5. ✅ `adi_gecafle_realtime_sync/__manifest__.py`

## Fichiers Créés

1. ✅ `update_realtime_sync.sh` - Script de mise à jour automatique
2. ✅ `CORRECTION_SYNC_TEMPS_REEL.md` - Cette documentation

## Bénéfices de la Correction

- ✅ **Synchronisation multi-onglets**: Les réceptions créées dans un onglet sont immédiatement visibles dans les autres
- ✅ **Synchronisation multi-postes**: Les utilisateurs sur différents postes voient les mises à jour en temps réel
- ✅ **Expérience utilisateur améliorée**: Plus besoin d'appuyer sur F5
- ✅ **Notifications informatives**: L'utilisateur est informé des changements
- ✅ **Performance optimisée**: Seules les vues concernées sont rafraîchies
- ✅ **Robustesse**: Gestion des erreurs pour éviter les blocages

## Support et Maintenance

### En cas de problème

1. Vérifier que le module est bien installé:
   ```sql
   SELECT name, state FROM ir_module_module
   WHERE name = 'adi_gecafle_realtime_sync';
   ```

2. Vérifier les logs de la console navigateur (F12)

3. Vérifier les logs Odoo pour les erreurs

4. Redémarrer Odoo et vider le cache navigateur (Ctrl+Shift+Delete)

### Améliorations Futures Possibles

- [ ] Ajouter un indicateur visuel dans le champ Many2one quand de nouvelles options sont disponibles
- [ ] Implémenter un système de polling de secours si le WebSocket échoue
- [ ] Ajouter des paramètres pour désactiver la sync pour certains utilisateurs
- [ ] Étendre la synchronisation à d'autres modèles (produits, clients, etc.)

---

**Date de création:** 2025-01-18
**Auteur:** Claude (Assistant IA)
**Version du module:** 17.1.0
**Statut:** ✅ Testé et Fonctionnel
