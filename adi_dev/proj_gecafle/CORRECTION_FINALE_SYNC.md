# ⚠️ CORRECTION FINALE - Synchronisation des Paiements

## 🔴 PROBLÈME IDENTIFIÉ

**Dans Odoo 17, la colonne `state` N'EXISTE PAS dans `account_payment` !**

L'état est géré dans `account_move` (l'écriture comptable) via le champ `move_id.state`.

## ✅ CORRECTIONS EFFECTUÉES

### 1. Fichier `/adi_gecafle_receptions/models/account_payment.py`

#### Modifications :
- **Méthode `create()`** : Utilise `payment.move_id.state` au lieu de `payment.state`
- **Méthode `write()`** : Utilise `payment.move_id.state` au lieu de `payment.state`
- **Méthode `unlink()`** : Utilise `payment.move_id.state` au lieu de `payment.state`

### 2. Nouveau Fichier `/adi_gecafle_receptions/models/account_move_inherit.py`

Création d'un héritage de `account.move` pour gérer la synchronisation lors des changements d'état :
- **`action_post()`** : Synchronise lors de la validation
- **`button_draft()`** : Réinitialise lors de la remise en brouillon
- **`button_cancel()`** : Réinitialise lors de l'annulation

### 3. Mise à jour de `/adi_gecafle_receptions/models/__init__.py`

Ajout de l'import : `from . import account_move_inherit`

## 🚀 ACTIONS REQUISES POUR ACTIVER LA CORRECTION

### Étape 1 : REDÉMARRER ODOO (OBLIGATOIRE)

```bash
# Option 1 : Service systemd
sudo systemctl restart odoo17

# Option 2 : Mode développement
# Arrêter Odoo (Ctrl+C) puis :
cd /home/stadev/odoo17-dev
./odoo-bin -c odoo17.conf -d o17_gecafle_final_base
```

### Étape 2 : METTRE À JOUR LE MODULE

Dans l'interface Odoo :
1. Aller dans **Applications**
2. Retirer le filtre "Apps" pour voir tous les modules
3. Rechercher **"adi_gecafle_receptions"**
4. Cliquer sur **"Mettre à jour"** (icône flèche circulaire)
5. Faire de même pour **"adi_gecafle_reception_extended"**

OU en ligne de commande :
```bash
./odoo-bin -c odoo17.conf -d o17_gecafle_final_base \
    -u adi_gecafle_receptions,adi_gecafle_reception_extended \
    --stop-after-init
```

### Étape 3 : SYNCHRONISER LES PAIEMENTS EXISTANTS

Pour corriger les données existantes :
```bash
cd /home/stadev/odoo17-dev/adi_dev/proj_gecafle
python3 sync_existing_payments.py
```

## 📝 WORKFLOW DE TEST

### Test Manuel dans Odoo

1. **Créer/Ouvrir une réception**
   - Nom contenant "TEST" pour faciliter les tests

2. **Créer une Avance Producteur**
   - Cliquer sur "Enregistrer Avance"
   - Entrer un montant (ex: 5000)
   - **IMPORTANT** : Cliquer sur "Valider" ou "Comptabiliser"
   - Retourner à la réception
   - ✅ Le champ "Avance Producteur" doit afficher 5000

3. **Annuler le paiement**
   - Ouvrir le paiement
   - Cliquer sur "Remettre en brouillon"
   - Retourner à la réception
   - ✅ Le champ "Avance Producteur" doit afficher 0

## 🔍 VÉRIFICATION DES LOGS

Pour confirmer que la synchronisation fonctionne :

```bash
# Suivre les logs en temps réel
tail -f /var/log/odoo/odoo17.log | grep "PAYMENT SYNC"

# Ou si en mode dev
tail -f ~/.odoo/odoo.log | grep "PAYMENT SYNC"
```

Messages attendus lors de la validation :
```
[PAYMENT SYNC - POST] Successfully updated avance_producteur = 5000.0 for reception 123
```

Messages lors de l'annulation :
```
[PAYMENT SYNC - DRAFT] Reset avance_producteur = 0 for reception 123
```

## ⚠️ POINTS D'ATTENTION

### 1. Structure Odoo 17
- **account_payment** : Contient le montant et les flags (is_advance_producer, etc.)
- **account_move** : Contient l'état (draft, posted, cancel)
- La relation : `payment.move_id` → `account_move`

### 2. Flux de Synchronisation

```
Utilisateur valide paiement
    ↓
account_move.action_post()
    ↓
État passe à 'posted'
    ↓
Synchronisation déclenchée
    ↓
Mise à jour gecafle_reception.avance_producteur
```

### 3. Cas Gérés
- ✅ Validation d'un paiement → Mise à jour du montant
- ✅ Annulation d'un paiement → Remise à zéro
- ✅ Remise en brouillon → Remise à zéro
- ✅ Modification du montant → Mise à jour
- ✅ Suppression d'un paiement → Remise à zéro

## 🆘 DÉPANNAGE

### Si la synchronisation ne fonctionne toujours pas :

1. **Vérifier que les modules sont installés**
```sql
SELECT name, state FROM ir_module_module
WHERE name LIKE '%gecafle%reception%';
```

2. **Vérifier les champs dans la base**
```sql
-- Vérifier gecafle_reception
SELECT column_name FROM information_schema.columns
WHERE table_name = 'gecafle_reception'
AND column_name IN ('avance_producteur', 'transport', 'paiement_emballage');

-- Vérifier account_payment
SELECT column_name FROM information_schema.columns
WHERE table_name = 'account_payment'
AND column_name IN ('reception_id', 'is_advance_producer', 'is_advance_transport', 'is_payment_emballage');
```

3. **Créer les champs manquants si nécessaire**
```bash
python3 sync_existing_payments.py
```

4. **Forcer une mise à jour manuelle pour test**
```sql
-- Test direct SQL
UPDATE gecafle_reception
SET avance_producteur = 9999
WHERE id = (SELECT id FROM gecafle_reception WHERE name LIKE '%TEST%' LIMIT 1);
```

Si la mise à jour SQL fonctionne, le problème est dans le code Python → Redémarrer Odoo.

## 📊 RÉSUMÉ DES FICHIERS MODIFIÉS

```
adi_gecafle_receptions/
├── models/
│   ├── __init__.py                 ✏️ MODIFIÉ (ajout import)
│   ├── account_payment.py          ✏️ MODIFIÉ (utilise move_id.state)
│   └── account_move_inherit.py     🆕 NOUVEAU (gère la synchronisation)
```

---

**Date de correction** : 16 novembre 2025
**Version Odoo** : 17.0
**Problème corrigé** : `payment.state` n'existe pas → utilisation de `payment.move_id.state`