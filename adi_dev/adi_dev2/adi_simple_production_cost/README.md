# ADI - Coût de Production Simplifié

Module Odoo 17 pour le calcul du prix de revient journalier **sans utiliser le module MRP**.

## Présentation

Ce module permet de gérer la production et calculer le coût de revient de manière simplifiée, en utilisant uniquement les modules standard : **Stock**, **Achat**, **Vente** et **Comptabilité**.

### Cas d'usage

Production de biscuits avec deux variantes :
- **SOLO** : Carton = 48 packs × 4 unités = 192 unités
- **CLASSICO** : Carton = 24 packs × 13 unités = 312 unités
- **Ratio** : Coût SOLO = 1.65 × Coût CLASSICO (configurable)

---

## Architecture

### Trois Dépôts

| Dépôt | Code | Description |
|-------|------|-------------|
| Dépôt Matière Première | DMP | Achats de MP avec méthode AVCO |
| Dépôt Production | DPR | Simulation de production via BL |
| Dépôt Produits Finis | DPF | Réception des produits finis |

### Flux de Production

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      DMP        │────▶│      DPR        │────▶│      DPF        │
│ Matière Première│     │   Production    │     │ Produits Finis  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       ▲
        │                       │                       │
   Achats MP              Consommation            Achat interne
   (Fournisseurs)         (BL vers Contact       (Fournisseur
                           Consommation)          Production)
```

---

## Fonctionnalités

### 1. Production Journalière

Chaque jour, saisir :

#### Consommations
- Liste des matières premières utilisées
- Quantité et poids par unité
- Coût automatique (prix AVCO)

#### Rebuts et Pâte
| Type | Description | Impact |
|------|-------------|--------|
| Rebut Vendable | Peut être vendu | Stock + Coût |
| Rebut Non Vendable | Perte sèche | Coût uniquement |
| Pâte Récupérable | Réutilisée demain | Valeur conservée |
| Pâte Irrécupérable | Perte | Coût uniquement |

#### Emballage
- Cartons (lié à la quantité produite)
- Film plastique / Plastification
- Étiquettes
- Autres

#### Produits Finis
- Quantité SOLO (cartons)
- Quantité CLASSICO (cartons)
- Prix de vente pour calcul de marge

### 2. Calculs Automatiques

#### Coût par Kg
```
Coût/Kg = Coût Total Consommation / Poids Total Consommation
```

#### Poids Bon
```
Poids Bon = Poids Consommé - Rebuts - Pâte Irrécupérable - Pâte Récupérable
```

#### Coût Total Production
```
Coût Total = Coût Matières + Coût Emballage - Valeur Pâte Récupérable
```

#### Répartition par Produit (avec ratio)
```
Coût CLASSICO = Coût Total / (Qté SOLO × Ratio + Qté CLASSICO)
Coût SOLO = Coût CLASSICO × Ratio
```

### 3. Génération Automatique de Documents

À la validation, le module génère :

| Document | Description |
|----------|-------------|
| BL Consommation | Bon de livraison vers le contact "Consommation" pour déstocker les MP |
| Achat Produits Finis | Commande d'achat depuis le fournisseur "Production" avec le coût calculé |
| Achat Rebuts | Commande d'achat pour les rebuts vendables |

### 4. Rapport PDF

Fiche de production journalière incluant :
- Détail des consommations
- Détail des rebuts et pâte
- Détail des produits finis
- Résumé des coûts
- Calcul des marges

---

## Configuration

### Accès
Menu : **Coût Production > Configuration > Paramètres**

### Onglets de Configuration

#### 1. Produits Finis
- Produit SOLO et CLASSICO
- Poids par carton
- Ratio de coût (défaut : 1.65)

#### 2. Dépôts et Emplacements
- Dépôt Matière Première (DMP)
- Dépôt Production (DPR)
- Dépôt Produits Finis (DPF)

#### 3. Partenaires
- **Contact Consommation** : Contact fictif pour les BL de déstockage
- **Fournisseur Production** : Fournisseur fictif pour les achats de produits finis

#### 4. Rebuts et Pâte
- Produit Rebut Vendable
- Produit Rebut Non Vendable
- Produit Pâte Récupérable
- Produit Pâte Irrécupérable

#### 5. Paramètres
- Créer BL Consommation automatiquement
- Créer Achat Produits Finis automatiquement

---

## Workflow

```
┌──────────┐    ┌───────────┐    ┌───────────┐    ┌──────────┐    ┌─────────┐
│ Brouillon│───▶│ Confirmé  │───▶│  Calculé  │───▶│  Validé  │───▶│ Terminé │
└──────────┘    └───────────┘    └───────────┘    └──────────┘    └─────────┘
     │               │                │                │               │
   Saisie        Vérification     Calcul des      Génération      Mise à jour
   données       des données      coûts           documents       prix revient
```

### États

| État | Description |
|------|-------------|
| Brouillon | Saisie en cours |
| Confirmé | Données validées, prêt pour calcul |
| Calculé | Coûts calculés, prêt pour validation |
| Validé | Documents générés (BL, Achats) |
| Terminé | Prix de revient mis à jour sur les produits |

---

## Installation

### Prérequis
- Odoo 17
- Modules : `stock`, `purchase`, `sale`, `account`, `mail`

### Étapes
1. Copier le module dans le dossier addons
2. Mettre à jour la liste des applications
3. Installer "ADI - Coût de Production Simplifié"
4. Configurer les paramètres

---

## Groupes de Sécurité

| Groupe | Droits |
|--------|--------|
| Utilisateur Coût Production | Créer, modifier les productions |
| Responsable Coût Production | Valider, configurer, supprimer |

---

## Support

**ADICOPS**
- Site : https://adicops-dz.com
- Email : info@adicops.com

---

## Changelog

### Version 17.0.1.0.0
- Version initiale
- Gestion des consommations
- Gestion des rebuts et pâte
- Gestion des coûts d'emballage
- Calcul automatique du coût de revient
- Génération automatique des documents
- Rapport PDF
