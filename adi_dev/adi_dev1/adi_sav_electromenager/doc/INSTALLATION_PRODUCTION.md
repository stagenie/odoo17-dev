# Installation en Production - adi_sav_electromenager

## 📋 Prérequis

- Odoo 17.0
- Modules dépendants : `base`, `mail`, `product`, `sale`, `stock`
- Sauvegarde complète de la base de données

---

## ✅ NOUVELLE INSTALLATION (Base Vierge)

### Procédure Standard

```bash
# 1. Arrêter le serveur Odoo
sudo systemctl stop odoo

# 2. Mettre à jour le module
PGPASSWORD='votre_mot_de_passe' ./.venv/bin/python ./odoo-bin \
  -c /etc/odoo/odoo.conf \
  -d nom_base_prod \
  -i adi_sav_electromenager \
  --stop-after-init

# 3. Redémarrer le serveur
sudo systemctl start odoo
```

**Résultat attendu** : Installation propre sans erreur

---

## ⚠️ MISE À JOUR (Ancienne Version Installée)

### ⚠️ IMPORTANT : Sauvegarde Obligatoire

```bash
# Sauvegarder la base de données
pg_dump -U odoo nom_base_prod > backup_avant_maj_sav_$(date +%Y%m%d_%H%M%S).sql
```

### Méthode 1 : Avec Script de Migration (RECOMMANDÉE)

Le script de migration `migrations/17.0.1.0.0/pre-migrate.py` nettoie automatiquement les champs orphelins.

```bash
# 1. Arrêter le serveur Odoo
sudo systemctl stop odoo

# 2. Mettre à jour le module
PGPASSWORD='votre_mot_de_passe' ./.venv/bin/python ./odoo-bin \
  -c /etc/odoo/odoo.conf \
  -d nom_base_prod \
  -u adi_sav_electromenager \
  --stop-after-init

# 3. Redémarrer le serveur
sudo systemctl start odoo
```

### Méthode 2 : Nettoyage Manuel (Si la méthode 1 échoue)

Si la mise à jour échoue avec des erreurs `KeyError` sur des champs, exécutez ce script SQL **AVANT** la mise à jour :

```bash
# Se connecter à PostgreSQL
psql -U odoo -d nom_base_prod

# Exécuter le script de nettoyage
DELETE FROM ir_model_fields
WHERE model = 'sav.return'
AND name IN (
    'doc_state', 'action_taken', 'picking_id', 'sale_order_id',
    'product_id', 'serial_number', 'product_condition', 'sale_date',
    'filter_from_picking', 'available_product_ids', 'delivery_date',
    'color', 'diagnostic', 'repair_notes', 'reception_date',
    'repair_start_date', 'repair_end_date', 'sent_to_repairer_date',
    'returned_to_center_date', 'sent_to_sales_point_date'
);

DELETE FROM ir_model_data
WHERE module = 'adi_sav_electromenager'
AND name LIKE '%doc_state%';

-- Quitter psql
\q
```

Puis réessayez la mise à jour.

---

## 🧪 TEST SUR ENVIRONNEMENT DE STAGING

**FORTEMENT RECOMMANDÉ** : Testez d'abord sur une copie de la base de production

```bash
# 1. Créer une copie de la base prod
createdb -U odoo -T nom_base_prod nom_base_staging

# 2. Tester la mise à jour sur le staging
PGPASSWORD='votre_mot_de_passe' ./.venv/bin/python ./odoo-bin \
  -c /etc/odoo/odoo.conf \
  -d nom_base_staging \
  -u adi_sav_electromenager \
  --stop-after-init

# 3. Si succès, appliquer sur production
# Si échec, analyser les logs et corriger
```

---

## 📊 Vérifications Post-Installation

### 1. Vérifier les nouveaux champs res.partner

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'res_partner'
AND column_name IN ('is_sales_point', 'is_return_center', 'is_repairer', 'sales_point_code', 'parent_return_center_id');
```

**Résultat attendu** : 5 colonnes trouvées

### 2. Vérifier les modèles SAV

```sql
SELECT model
FROM ir_model
WHERE model LIKE 'sav.%'
ORDER BY model;
```

**Résultat attendu** :
```
sav.category
sav.fault.type
sav.return
sav.return.line
```

### 3. Tester dans l'interface Odoo

1. Aller dans **SAV Électroménager** > **Configuration** > **Points de Vente**
2. Créer un nouveau point de vente test
3. Vérifier que les champs `Code Point de Vente` et `Centre de Retour Rattaché` sont visibles
4. Créer un nouveau retour SAV test

---

## 🔧 Dépannage

### Erreur : `column res_partner.is_sales_point does not exist`

**Cause** : Les colonnes n'ont pas été créées dans la base de données

**Solution** :
```bash
# Forcer la mise à jour du modèle res.partner
PGPASSWORD='votre_mot_de_passe' ./.venv/bin/python ./odoo-bin \
  -c /etc/odoo/odoo.conf \
  -d nom_base_prod \
  -u adi_sav_electromenager \
  --stop-after-init \
  --log-level=debug
```

### Erreur : `KeyError: 'doc_state'` ou autres champs

**Cause** : Champs orphelins de l'ancienne version

**Solution** : Utiliser la Méthode 2 (nettoyage manuel) ci-dessus

### Erreur : `domain of python field 'parent_return_center_id' ([('company_type', '=', 'company')])`

**Cause** : Version obsolète du code source

**Solution** : Vérifier que vous avez bien la dernière version où le domaine est :
```python
domain="[('is_return_center', '=', True)]"
```

---

## 📞 Support

En cas de problème lors de la mise en production, documenter :
1. Le message d'erreur complet
2. Les logs Odoo (`/var/log/odoo/odoo.log`)
3. La version d'Odoo et du module
4. Si c'est une installation ou une mise à jour

---

## 🎯 Checklist Finale

- [ ] Sauvegarde de la base de données effectuée
- [ ] Test sur environnement de staging réussi
- [ ] Serveur Odoo arrêté
- [ ] Mise à jour du module effectuée sans erreur
- [ ] Vérifications post-installation OK
- [ ] Test de création d'un retour SAV fonctionnel
- [ ] Serveur Odoo redémarré
- [ ] Utilisateurs informés de la nouvelle version
