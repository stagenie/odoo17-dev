# GeCaFle - Synchronisation Temps Réel V3

## Objectif

Ce module permet aux réceptions enregistrées d'apparaître **instantanément** dans les listes déroulantes des ventes, sans nécessiter de rafraîchissement F5.

## Problème résolu (V2 -> V3)

Dans la version V2, les utilisateurs devaient toujours appuyer sur F5 pour voir les nouvelles réceptions. Le problème venait de:

1. **Domaine lambda**: `domain=lambda self: self._get_reception_domain()` n'était évalué qu'une seule fois
2. **Widgets incorrects**: Les méthodes `search()` et `searchContext` n'existaient pas dans `Many2OneField` d'Odoo 17
3. **Cache non invalidé**: Le cache ORM n'était pas correctement invalidé

## Solution V3

### Architecture

```
FRONTEND (JavaScript)
├── gecafle_sync Service
│   ├── Polling serveur (2s)
│   ├── BroadcastChannel API (inter-onglets)
│   └── localStorage fallback
├── ReceptionM2XAutocomplete (extends Many2XAutocomplete)
│   ├── search() -> name_search avec timestamp anti-cache
│   └── loadOptionsSource() -> forceCheck() avant chargement
└── Patches FormController / ListController
    └── Broadcast après save/create

BACKEND (Python)
├── gecafle.reception
│   ├── name_search() -> Filtre SQL dynamique (stock > 0)
│   ├── create/write/unlink() -> _mark_reception_changed()
│   └── get_last_change_timestamp() -> API pour polling
└── gecafle.details_reception
    ├── name_search() -> invalidate_model() avant recherche
    └── create/write/unlink() -> Propage _mark_reception_changed()
```

### Flux de données

```
1. Utilisateur crée une réception dans Onglet 1
   |
2. Backend: create() -> _mark_reception_changed()
   |
3. Timestamp mis à jour dans ir.config_parameter
   |
4. Frontend Onglet 1: Patch broadcast le changement
   |
5. BroadcastChannel -> Onglet 2 reçoit notification
   |
6. Onglet 2: Widgets marqués pour rechargement
   |
7. Utilisateur clique sur reception_id dans Onglet 2
   |
8. Widget: forceCheck() + search() avec nouveau timestamp
   |
9. Backend: name_search() avec filtrage SQL temps réel
   |
10. Nouvelle réception visible instantanément!
```

## Fichiers du module

```
adi_gecafle_realtime_sync/
├── __manifest__.py                    # Configuration module V3
├── __init__.py
├── README.md                          # Cette documentation
├── models/
│   ├── __init__.py
│   ├── reception_realtime.py          # name_search dynamique + timestamps
│   └── detail_ventes_realtime.py      # Simplifie le domaine reception_id
├── static/src/js/
│   ├── broadcast_channel_service.js   # Service de synchronisation
│   ├── reception_realtime_widget.js   # Widget pour reception_id
│   ├── detail_reception_realtime_widget.js  # Widget pour detail_reception_id
│   ├── reception_form_patch.js        # Patch FormController
│   └── reception_list_patch.js        # Patch ListController
├── views/
│   └── vente_views_inherit.xml        # Applique les widgets
└── security/
    └── ir.model.access.csv
```

## Différences V2 -> V3

| Aspect | V2 (problème) | V3 (solution) |
|--------|---------------|---------------|
| Widget base | Many2OneField.search() | Many2XAutocomplete.search() |
| Méthode search | N'existait pas | Override correct |
| Domaine | Lambda (1 évaluation) | Statique + name_search dynamique |
| Filtrage stock | Via domaine | Via SQL dans name_search |
| Cache | Pas vraiment invalidé | Timestamp unique à chaque requête |

## Installation

1. Mettre à jour le module:
```bash
./odoo-bin -u adi_gecafle_realtime_sync -d votre_base
```

2. Vider le cache des assets:
```bash
# Dans Odoo: Paramètres > Technique > Vues > Régénérer les assets
# Ou simplement ajouter ?debug=assets à l'URL et rafraîchir
```

## Vérification

1. Ouvrir la console navigateur (F12)
2. Vous devriez voir:
```
[GeCaFle] Service gecafle_sync enregistré
[GeCaFle Sync] Service de synchronisation démarré
[GeCaFle Sync] Démarrage polling (2000ms)
[GeCaFle] Widget reception_realtime enregistré
[GeCaFle] Widget detail_reception_realtime enregistré
[GeCaFle] Patch FormController appliqué
[GeCaFle] Patch ListController appliqué
```

3. Créer une réception dans un onglet
4. Dans un autre onglet avec une vente ouverte, cliquer sur le champ reception_id
5. La nouvelle réception devrait apparaître instantanément

## Dépannage

### Les réceptions n'apparaissent toujours pas

1. Vérifier que le module est bien mis à jour (version 17.3.0)
2. Vider le cache du navigateur (Ctrl+Shift+R)
3. Vérifier les logs console pour les erreurs JavaScript
4. Vérifier que les réceptions ont bien `state = 'confirmee'` ou `'brouillon'`
5. Vérifier que les lignes de réception ont `qte_colis_disponibles > 0`

### Vérifier le timestamp

```sql
SELECT value FROM ir_config_parameter
WHERE key = 'gecafle.reception.last_change';
```

### Logs serveur

```bash
tail -f /var/log/odoo/odoo.log | grep "GeCaFle"
```

## Auteur

**ADICOPS** - info@adicops.com

## Version

**17.3.0** - Compatible Odoo 17
