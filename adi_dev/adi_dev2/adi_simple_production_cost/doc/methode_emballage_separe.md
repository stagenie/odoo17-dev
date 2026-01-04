# Méthode de Calcul - Séparation des Coûts Emballage

## Introduction

Cette fonctionnalité permet d'affecter les coûts d'emballage de manière précise par type de produit (SOLO/CLASSICO) au lieu de tout répartir avec le ratio.

## Activation

1. Aller dans **Coût Production > Configuration**
2. Onglet **Paramètres**
3. Activer **"Séparer les Coûts Emballage"**

## Modes de Calcul

### Mode Standard (option désactivée)

Tous les coûts (matières + emballage) sont répartis avec le ratio SOLO/CLASSICO.

```
Coût Total = Matières + Emballage Total

Dénominateur = (Qty_SOLO × Ratio) + Qty_CLASSICO

Coût CLASSICO/carton = Coût Total / Dénominateur
Coût SOLO/carton = Coût CLASSICO × Ratio
```

**Exemple Standard :**
- Matières: 10 000 DA
- Emballage total: 2 000 DA
- Production: 100 SOLO + 200 CLASSICO
- Ratio: 1.65

```
Coût Total = 12 000 DA
Dénominateur = (100 × 1.65) + 200 = 365

Coût CLASSICO = 12 000 / 365 = 32.88 DA/carton
Coût SOLO = 32.88 × 1.65 = 54.25 DA/carton
```

---

### Mode Séparation (option activée)

Les emballages sont répartis selon leur **Affectation** :

| Affectation | Description | Calcul |
|-------------|-------------|--------|
| **Commun** | Film ondulé, étiquettes partagées | Réparti avec le ratio |
| **SOLO** | Cartons spécifiques SOLO | Divisé par Qty_SOLO uniquement |
| **CLASSICO** | Cartons spécifiques CLASSICO | Divisé par Qty_CLASSICO uniquement |
| **Sandwich GF** | Cartons Sandwich | Divisé par Qty_Sandwich |

#### Formule détaillée

```
# Étape 1 : Calculer le coût de base (matières + emballages communs)
Total à répartir = Matières + Emballage_Commun
Dénominateur = (Qty_SOLO × Ratio) + Qty_CLASSICO

Base CLASSICO = Total à répartir / Dénominateur
Base SOLO = Base CLASSICO × Ratio

# Étape 2 : Ajouter les emballages dédiés
Emballage SOLO/carton = Emballage_SOLO / Qty_SOLO
Emballage CLASSICO/carton = Emballage_CLASSICO / Qty_CLASSICO

# Étape 3 : Coût final
Coût SOLO final = Base SOLO + Emballage SOLO/carton
Coût CLASSICO final = Base CLASSICO + Emballage CLASSICO/carton
```

**Exemple Séparation :**
- Matières: 10 000 DA
- Emballage Commun (film ondulé): 500 DA
- Emballage SOLO (cartons): 1 000 DA
- Emballage CLASSICO (cartons): 500 DA
- Production: 100 SOLO + 200 CLASSICO
- Ratio: 1.65

```
# Étape 1
Total à répartir = 10 000 + 500 = 10 500 DA
Dénominateur = (100 × 1.65) + 200 = 365

Base CLASSICO = 10 500 / 365 = 28.77 DA
Base SOLO = 28.77 × 1.65 = 47.47 DA

# Étape 2
Emballage SOLO/carton = 1 000 / 100 = 10.00 DA
Emballage CLASSICO/carton = 500 / 200 = 2.50 DA

# Étape 3
Coût SOLO final = 47.47 + 10.00 = 57.47 DA/carton
Coût CLASSICO final = 28.77 + 2.50 = 31.27 DA/carton
```

## Interface Utilisateur

### Dans la Production Journalière (onglet Emballage)

Quand l'option est activée, une colonne **"Affectation"** apparaît :

| Type | Affectation | Produit | Qté | Prix Unit. | Total |
|------|-------------|---------|-----|------------|-------|
| Carton | SOLO | Carton SOLO | 100 | 10.00 | 1 000 |
| Carton | CLASSICO | Carton CLASSICO | 200 | 2.50 | 500 |
| Film Ondulé | Commun | Film PE | 50 kg | 10.00 | 500 |

### Dans la Configuration

Section **"Calcul des Coûts Emballage"** avec :
- Toggle pour activer/désactiver
- Explication du mode actif

---

## Cas Sandwich Grand Format

### Différence avec SOLO/CLASSICO

| Aspect | SOLO/CLASSICO | Sandwich GF |
|--------|---------------|-------------|
| Nombre de produits | 2 | 1 |
| Ratio | Oui (1.65) | **Non** |
| Calcul | Répartition proportionnelle | Division simple |

### Mode Standard - Sandwich GF

```
Coût Sandwich = Coût Total / Quantité

Exemple:
- Matières: 10 000 DA
- Emballage: 2 000 DA
- Production: 300 cartons Sandwich

Coût Sandwich = 12 000 / 300 = 40.00 DA/carton
```

### Mode Séparation - Sandwich GF

Pour Sandwich GF, le mode séparation est **plus simple** car il n'y a qu'un seul produit.
Tous les emballages (Commun + Sandwich GF) vont au même produit.

```
Coût Sandwich = (Matières + Emballage Commun + Emballage Sandwich) / Quantité
```

**Note :** La distinction "Commun" vs "Sandwich GF" reste utile pour :
- La traçabilité (savoir quel emballage est utilisé)
- La cohérence si on produit SOLO/CLASSICO et Sandwich le même jour (futur)

### Exemple Sandwich GF avec Séparation

| Type | Affectation | Coût |
|------|-------------|------|
| Film ondulé | Commun | 500 DA |
| Carton Sandwich | Sandwich GF | 1 500 DA |
| **Total Emballage** | | **2 000 DA** |

```
Coût = (10 000 + 500 + 1 500) / 300 = 40.00 DA/carton
```

*Résultat identique au mode standard car un seul produit*

---

## Cas d'Usage

### Quand utiliser le Mode Séparation ?

1. **Cartons différents** : Les cartons SOLO et CLASSICO ont des tailles/prix différents
2. **Traçabilité précise** : Besoin de connaître le coût exact par produit
3. **Analyse des marges** : Comparaison précise des rentabilités

### Quand garder le Mode Standard ?

1. **Emballage identique** : Mêmes cartons pour tous les produits
2. **Simplicité** : Pas besoin de traçabilité détaillée
3. **Historique** : Garder la compatibilité avec les anciens calculs

## Notes Techniques

### Fichiers concernés

- `models/ron_config.py` : Champ `separate_packaging_costs`
- `models/ron_packaging_line.py` : Champ `target_product_type`
- `models/ron_daily_production.py` : Logique de calcul dans `_compute_finished_totals()`
- `views/ron_config_views.xml` : Interface configuration
- `views/ron_daily_production_views.xml` : Colonne conditionnelle

### Dépendances du calcul

Le champ `_compute_finished_totals` dépend de :
- `packaging_line_ids.total_cost`
- `packaging_line_ids.target_product_type`
- `total_consumption_cost`
- `finished_product_ids.quantity`

---

*Document créé le 04/01/2026 - Module adi_simple_production_cost*
