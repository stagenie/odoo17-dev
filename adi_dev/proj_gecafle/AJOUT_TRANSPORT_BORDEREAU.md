# Ajout du champ Transport dans les Bordereaux Avancés

## Date de modification
2025-11-16

## Modifications Effectuées

### 1. Ajout du champ Transport dans les rapports de bordereau avancé

Le champ `transport` (frais de transport) a été ajouté dans les **4 rapports de bordereau avancé** :

#### Rapports Modifiés

1. **report_bordereau_grouped_fr.xml** (Français - Regroupé)
2. **report_bordereau_simple_fr.xml** (Français - Simple)
3. **report_bordereau_grouped_ar.xml** (Arabe - Regroupé)
4. **report_bordereau_simple_ar.xml** (Arabe - Simple)

#### Position dans le rapport

Le champ `transport` apparaît maintenant dans la section **"CALCUL DU NET À PAYER"**, après l'Avance Producteur et avant les Emballages Achetés :

```
Total Ventes:                   XXXXX DA
Total Commission (-):          - XXXXX DA
Avance Producteur (-):         - XXXXX DA   ← Déjà existant
Transport (-):                 - XXXXX DA   ← NOUVEAU
Emballages Achetés (+):        + XXXXX DA
─────────────────────────────────────────
SOLDE FOURNISSEUR:               XXXXX DA
```

#### Code Ajouté (Français)

```xml
<t t-if="o.reception_id and o.reception_id.transport">
    <tr>
        <td class="text-right"><strong>Transport (-):</strong></td>
        <td class="text-right text-danger">
            - <span t-field="o.reception_id.transport"/>
        </td>
    </tr>
</t>
```

#### Code Ajouté (Arabe)

```xml
<t t-if="o.reception_id and o.reception_id.transport">
    <tr>
        <td><strong>النقل (-):</strong></td>
        <td class="text-left text-danger">
            <span dir="ltr">- <span t-field="o.reception_id.transport"/></span>
        </td>
    </tr>
</t>
```

### 2. Affichage du bouton "Imprimer Bordereau Avancé" sans condition d'état

**Avant** : Le bouton n'apparaissait que si la récap était à l'état "Validé" ou "Facturé"

**Après** : Le bouton est toujours visible, quel que soit l'état de la récap

#### Fichier Modifié

**adi_gecafle_reception_extended/views/recap_views_extended.xml**

#### Modification

```xml
<!-- AVANT -->
<button name="%(adi_gecafle_reception_extended.action_bordereau_print_wizard)d"
        string="🖨️ Imprimer Bordereau Avancé"
        type="action"
        class="btn-info"
        icon="fa-print"
        invisible="state not in ['valide', 'facture']"    ← SUPPRIMÉ
        context="{'default_recap_id': id}"/>

<!-- APRÈS -->
<button name="%(adi_gecafle_reception_extended.action_bordereau_print_wizard)d"
        string="🖨️ Imprimer Bordereau Avancé"
        type="action"
        class="btn-info"
        icon="fa-print"
        context="{'default_recap_id': id}"/>
```

## Impact

### Comportement Attendu

1. **Champ Transport visible** :
   - Le montant du transport s'affiche automatiquement dans tous les bordereaux avancés (FR et AR)
   - Le champ ne s'affiche que s'il y a un montant de transport (> 0)
   - Le montant est déduit du solde fournisseur

2. **Bouton toujours accessible** :
   - Le bouton "Imprimer Bordereau Avancé" est visible même pour les récaps en brouillon
   - Plus besoin de valider la récap pour imprimer le bordereau
   - Permet d'imprimer des aperçus avant validation

### Calcul du Solde Fournisseur

Le calcul du solde fournisseur dans le bordereau prend maintenant en compte :

```
Total Ventes
- Total Commission
- Avance Producteur
- Transport (NOUVEAU)
+ Emballages Achetés
= SOLDE FOURNISSEUR
```

## Mise en Application

### Base de Données Déjà Mise à Jour

- ✅ **o17_gecafle_final_tests_f** - Testée et validée

### Pour Appliquer sur d'Autres Bases

```bash
cd /home/stadev/odoo17-dev
./odoo-bin -c odoo17.conf -d NOM_DE_LA_BASE -u adi_gecafle_reception_extended --stop-after-init --no-http
```

## Tests à Effectuer

### Test 1 : Affichage du Transport dans le Bordereau

1. Créer une réception avec transport
2. Valider un paiement de transport
3. Créer un récap
4. Imprimer le bordereau avancé (FR et AR)
5. Vérifier que le transport apparaît dans la section financière

### Test 2 : Bouton Imprimer Visible en Brouillon

1. Créer un récap (laisser en état brouillon)
2. Vérifier que le bouton "🖨️ Imprimer Bordereau Avancé" est visible
3. Cliquer sur le bouton et vérifier que le wizard s'ouvre
4. Imprimer et vérifier le résultat

### Test 3 : Calcul Correct du Solde

1. Créer une réception avec :
   - Total ventes : 100 000 DA
   - Commission : 5 000 DA
   - Avance producteur : 10 000 DA
   - Transport : 2 000 DA
   - Emballages achetés : 3 000 DA

2. Vérifier que le solde fournisseur = 100 000 - 5 000 - 10 000 - 2 000 + 3 000 = **86 000 DA**

## Fichiers Modifiés

```
adi_gecafle_reception_extended/
├── reports/
│   ├── report_bordereau_grouped_fr.xml      ← Modifié (ligne 309-319)
│   ├── report_bordereau_simple_fr.xml       ← Modifié (ligne 241-248)
│   ├── report_bordereau_grouped_ar.xml      ← Modifié (ligne 226-233)
│   └── report_bordereau_simple_ar.xml       ← Modifié (ligne 232-239)
└── views/
    └── recap_views_extended.xml             ← Modifié (ligne 18 supprimée)
```

## Notes Techniques

- Les modifications sont rétrocompatibles
- Aucune migration de données nécessaire
- Le champ transport utilise la synchronisation automatique implémentée précédemment (champs compute)
- L'affichage conditionnel (`t-if`) garantit que le transport n'apparaît que s'il y a un montant

## Support

Si des problèmes surviennent :

1. Vérifier que le module `adi_gecafle_reception_extended` est bien mis à jour
2. Vider le cache du navigateur
3. Redémarrer Odoo si nécessaire
4. Vérifier que les champs `transport` et `avance_producteur` se synchronisent correctement

---

**Module affecté** : `adi_gecafle_reception_extended`
**Version Odoo** : 17.0
**Statut** : ✅ Testé et validé
