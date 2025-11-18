# Synchronisation Temps Réel - Version Simplifiée V2

## Pourquoi Cette Nouvelle Version ?

La version précédente utilisait le système de bus Odoo qui s'est avéré complexe et source de problèmes. Cette nouvelle version adopte une approche **simple, fiable et testée**.

## Principe de Fonctionnement

### Architecture Simplifiée

```
┌──────────────────────────────────────────────────────────┐
│          CRÉATION/MODIFICATION RÉCEPTION                  │
│                    (N'importe quel onglet)                │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  Python: _mark_reception_changed()                       │
│  • Met à jour ir_config_parameter                        │
│  • Stocke timestamp: gecafle.reception.last_change       │
│  • Invalide le cache des modèles                         │
└──────────────────────────────────────────────────────────┘
                      │
                      │ Stockage en DB
                      ▼
┌──────────────────────────────────────────────────────────┐
│         ir_config_parameter (Base de données)            │
│  Key: gecafle.reception.last_change                      │
│  Value: 1705576234.123 (timestamp Unix)                  │
└──────────────────────────────────────────────────────────┘
                      │
                      │ Polling toutes les 3s
                      ▼
┌──────────────────────────────────────────────────────────┐
│   JavaScript: realtime_sync_service.js                   │
│   • Vérifie le timestamp toutes les 3 secondes           │
│   • Compare avec lastKnownTimestamp                      │
│   • Si différent → Rafraîchir les vues                   │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│            Rafraîchissement Silencieux                    │
│  • Aucune notification visuelle                          │
│  • Event: gecafle_reception_updated                      │
│  • Recharge les vues de vente automatiquement            │
└──────────────────────────────────────────────────────────┘
```

### Avantages de Cette Approche

✅ **Simple**: Pas de bus, pas de canaux, pas de complications
✅ **Fiable**: Le polling fonctionne toujours, même avec plusieurs onglets/postes
✅ **Léger**: Vérification toutes les 3 secondes seulement
✅ **Optimisé**: S'arrête quand la fenêtre est cachée
✅ **Silencieux**: Aucune notification intrusive
✅ **Testable**: Facile de déboguer dans la console

## Fichiers du Module

### 1. Python - `models/reception_realtime.py`

**Changements clés:**
- ❌ Supprimé: Bus, notifications, messages complexes
- ✅ Ajouté: Système de timestamp simple
- ✅ Ajouté: Méthode `get_last_change_timestamp()` pour le RPC

```python
def _mark_reception_changed(self):
    """Marque qu'une réception a changé"""
    timestamp = str(time.time())
    self.env['ir.config_parameter'].sudo().set_param(
        'gecafle.reception.last_change',
        timestamp
    )
    self.invalidate_model()  # Invalide le cache
```

### 2. JavaScript - `static/src/js/realtime_sync_service.js`

**Changements clés:**
- ❌ Supprimé: bus_service, notifications visuelles
- ✅ Ajouté: Polling avec setInterval
- ✅ Ajouté: Appels RPC pour vérifier le timestamp
- ✅ Ajouté: Gestion visibility (pause quand fenêtre cachée)

```javascript
// Vérification toutes les 3 secondes
setInterval(checkForChanges, 3000);

async function checkForChanges() {
    const currentTimestamp = await rpc(
        '/web/dataset/call_kw/gecafle.reception/get_last_change_timestamp',
        {...}
    );

    if (currentTimestamp !== lastKnownTimestamp) {
        // Rafraîchir!
        await refreshVenteViews();
    }
}
```

### 3. Patches des Contrôleurs - `static/src/js/reception_realtime.js`

**Simplifications:**
- Code minimal, juste l'essentiel
- Écoute l'événement `gecafle_reception_updated`
- Recharge le modèle silencieusement
- Gestion des erreurs silencieuse (pas de perturbation)

### 4. Patch Many2one - `static/src/js/many2one_refresh.js`

**Simplifications:**
- Juste l'invalidation du cache
- Pas de notifications
- Pas de rechargement forcé (trop perturbant)

## Installation

### Méthode Automatique

```bash
cd /home/stadev/odoo17-dev/adi_dev/proj_gecafle
./update_realtime_sync.sh
```

Puis redémarrer Odoo:
```bash
python3 /home/stadev/odoo17-dev/odoo-bin -c /etc/odoo/odoo17.conf
```

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

## Test de Fonctionnement

### Test 1: Deux Onglets

1. **Onglet 1**: Ouvrir la liste des ventes
2. **Onglet 2**: Créer une nouvelle réception
3. **Vérification Onglet 1**:
   - Attendez max 3 secondes
   - La liste se rafraîchit automatiquement (silencieusement)
   - Ouvrir la console (F12): voir `[GeCaFle Sync] Changement détecté!`

### Test 2: Formulaire de Vente

1. **Onglet 1**: Créer une nouvelle vente (formulaire vide)
2. **Onglet 2**: Créer une nouvelle réception
3. **Vérification Onglet 1**:
   - Attendez 3 secondes
   - Cliquez sur le champ "Réception"
   - La nouvelle réception devrait apparaître dans la liste

### Test 3: Multi-postes

1. **Poste 1**: Ouvrir une vue de vente
2. **Poste 2**: Créer plusieurs réceptions
3. **Vérification Poste 1**:
   - Toutes les 3 secondes, la vue se rafraîchit
   - Les nouvelles réceptions sont disponibles

## Debugging

### Console JavaScript (F12)

**Logs normaux lors du démarrage:**
```
[GeCaFle Sync] Service démarré
[GeCaFle Sync] Démarrage du polling (toutes les 3 secondes)
[GeCaFle Sync] Timestamp initial: 1705576234.123
[GeCaFle Sync] Patches appliqués
```

**Logs lors d'un changement:**
```
[GeCaFle Sync] Changement détecté! Rafraîchissement...
[GeCaFle Sync] Vue de vente détectée, rafraîchissement silencieux
```

**Logs lors du masquage de la fenêtre:**
```
[GeCaFle Sync] Fenêtre cachée, pause du polling
[GeCaFle Sync] Fenêtre visible, reprise du polling
```

### Vérifier le Timestamp en Base de Données

```sql
-- Voir le timestamp actuel
SELECT key, value
FROM ir_config_parameter
WHERE key = 'gecafle.reception.last_change';

-- Résultat attendu:
-- key: gecafle.reception.last_change
-- value: 1705576234.123456
```

### Forcer un Changement Manuel

```sql
-- Pour tester, changer le timestamp manuellement
UPDATE ir_config_parameter
SET value = EXTRACT(EPOCH FROM NOW())::text
WHERE key = 'gecafle.reception.last_change';
```

Dans les 3 secondes, toutes les vues de vente ouvertes devraient se rafraîchir!

## Optimisations

### Fréquence de Polling

Par défaut: **3 secondes**

Pour changer (dans `realtime_sync_service.js`):
```javascript
// Plus rapide (1 seconde) - plus de charge
pollingInterval = setInterval(checkForChanges, 1000);

// Plus lent (5 secondes) - moins de charge
pollingInterval = setInterval(checkForChanges, 5000);
```

### Pause Automatique

Le polling s'arrête automatiquement quand:
- La fenêtre est minimisée
- L'utilisateur change d'onglet
- L'écran est verrouillé

Et reprend automatiquement quand la fenêtre redevient visible.

## Comparaison avec l'Ancienne Version

| Aspect | V1 (Bus) | V2 (Polling) |
|--------|----------|--------------|
| **Complexité** | ⚠️ Élevée | ✅ Simple |
| **Fiabilité** | ⚠️ Problèmes de canal | ✅ Toujours fiable |
| **Notifications** | ⚠️ Intrusives | ✅ Silencieuses |
| **Performance** | ✅ Temps réel | ✅ Max 3s de délai |
| **Debugging** | ⚠️ Difficile | ✅ Facile |
| **Compatibilité** | ⚠️ Dépend du bus | ✅ Fonctionne partout |
| **Maintenance** | ⚠️ Complexe | ✅ Simple |

## Dépendances

- ❌ ~~bus~~ (supprimé)
- ✅ base
- ✅ adi_gecafle_receptions
- ✅ adi_gecafle_ventes

## Fichiers Modifiés

1. ✅ `models/reception_realtime.py` - Système de timestamp
2. ✅ `static/src/js/realtime_sync_service.js` - Polling
3. ✅ `static/src/js/reception_realtime.js` - Patches simplifiés
4. ✅ `static/src/js/many2one_refresh.js` - Cache invalidation
5. ✅ `__manifest__.py` - Suppression dépendance bus
6. ✅ `security/ir.model.access.csv` - Nettoyage

## Performance

### Charge Système

- **Requête RPC**: 1 par utilisateur toutes les 3 secondes
- **Taille de la requête**: ~200 bytes
- **Taille de la réponse**: ~50 bytes (juste un timestamp)
- **Impact**: Négligeable même avec 100 utilisateurs

### Calcul:
- 100 utilisateurs × 1 requête/3s = ~33 requêtes/seconde
- ~33 × 250 bytes = ~8 KB/s
- **Impact réseau**: Minimal

## Problèmes Connus et Solutions

### Problème: Le rafraîchissement ne se fait pas

**Solution:**
1. Ouvrir la console (F12)
2. Vérifier les logs `[GeCaFle Sync]`
3. Vérifier le timestamp en BDD:
   ```sql
   SELECT value FROM ir_config_parameter
   WHERE key = 'gecafle.reception.last_change';
   ```

### Problème: Erreur RPC dans la console

**Solution:**
1. Vérifier que le module est bien installé
2. Redémarrer Odoo
3. Vider le cache du navigateur (Ctrl+Shift+Delete)

### Problème: Trop lent (> 3 secondes)

**Solution:**
1. Diminuer l'intervalle de polling dans le code
2. Vérifier la performance du serveur
3. Optimiser les requêtes SQL

## Améliorations Futures Possibles

- [ ] Ajouter un paramètre système pour configurer la fréquence de polling
- [ ] Implémenter un système de "backoff" si le serveur est lent
- [ ] Ajouter des statistiques de synchronisation dans les paramètres
- [ ] Étendre à d'autres modèles (produits, clients)
- [ ] Ajouter une API pour que d'autres modules puissent s'abonner aux changements

## Conclusion

Cette version V2 utilise une approche **simple et éprouvée**:
- Pas de technologie complexe
- Pas de notifications intrusives
- Juste un polling léger qui fonctionne **toujours**

**Résultat:** Les réceptions créées dans n'importe quel onglet ou poste sont visibles partout en **maximum 3 secondes**, silencieusement et de manière fiable.

---

**Date:** 2025-01-18
**Version:** 17.1.0 (V2 - Polling)
**Statut:** ✅ Simplifié et Prêt pour Production
