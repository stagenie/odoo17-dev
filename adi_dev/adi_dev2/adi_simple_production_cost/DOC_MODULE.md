# ADI - Coût de Production Simplifié

## Documentation Utilisateur

---

## 1. Présentation du Module

Ce module permet de calculer le **prix de revient journalier** de production sans utiliser le module MRP (Manufacturing). Il est conçu pour une production de type biscuiterie avec deux gammes de produits :

- **SOLO / CLASSICO** : Deux produits issus de la même pâte avec un ratio de coût
- **Sandwich Grand Format** : Produit indépendant (production séparée)

### Architecture des Dépôts

| Dépôt | Rôle | Méthode de Valorisation |
|-------|------|------------------------|
| **DMP** (Dépôt Matière Première) | Stock des matières premières | AVCO |
| **DPR** (Dépôt Production) | Simulation de la consommation via BL | - |
| **DPF** (Dépôt Produits Finis) | Réception des produits finis via achat | AVCO |

---

## 2. Configuration Initiale

### Accès : Menu `Coût Production` > `Configuration`

### Onglet "Produits Finis"

#### SOLO / CLASSICO
| Champ | Description | Exemple |
|-------|-------------|---------|
| Produit SOLO | Produit fini SOLO | `[PROD] SOLO` |
| Poids/Carton (kg) | Poids d'un carton SOLO | `8.5` |
| Unités/Carton | Nombre d'unités par carton | `192` |
| Produit CLASSICO | Produit fini CLASSICO | `[PROD] CLASSICO` |
| Poids/Carton (kg) | Poids d'un carton CLASSICO | `9.0` |
| Unités/Carton | Nombre d'unités par carton | `312` |
| **Ratio Coût** | Coût SOLO = Ratio × Coût CLASSICO | `1.65` |

#### Sandwich Grand Format
| Champ | Description | Exemple |
|-------|-------------|---------|
| Produit Sandwich GF | Produit fini Sandwich | `[PROD] SANDWICH GF` |
| Poids/Carton (kg) | Poids d'un carton | `12.0` |
| Unités/Carton | Nombre d'unités par carton | `144` |

### Onglet "Dépôts"

| Champ | Description |
|-------|-------------|
| Dépôt Matière Première (DMP) | Entrepôt des matières premières |
| Dépôt Production (DPR) | Entrepôt de production (intermédiaire) |
| Dépôt Produits Finis (DPF) | Entrepôt des produits finis |
| Emplacement Production | Emplacement spécifique pour la production |

### Onglet "Partenaires"

| Champ | Description |
|-------|-------------|
| Contact Consommation | Partenaire fictif pour les BL de déstockage |
| Fournisseur Production | Partenaire fictif pour les achats de produits finis |

### Onglet "Paramètres"

| Champ | Description |
|-------|-------------|
| Créer BL automatiquement | Génère le BL de consommation à la validation |
| Créer Achats automatiquement | Génère les achats (produits finis, rebuts, pâte) |
| Produit Pâte Récupérable | Produit par défaut pour la pâte récupérable |

---

## 3. Configuration des Produits Rebuts

### Marquer un produit comme "Rebut Récupérable"

1. Aller dans `Inventaire` > `Produits`
2. Ouvrir la fiche du produit (ex: "Rebut Crème", "Rebut Sec")
3. Cocher **"Est un Rebut Récupérable"** (sous le nom du produit)
4. Sauvegarder

> **Note** : Seuls les produits marqués apparaîtront dans la sélection de l'onglet "Rebuts Récupérables"

---

## 4. Création d'une Production Journalière

### Accès : Menu `Coût Production` > `Production Journalière`

### Étape 1 : Informations Générales

| Champ | Description |
|-------|-------------|
| Date de Production | Date du jour de production |
| Type de Production | `SOLO / CLASSICO` ou `Sandwich Grand Format` |

### Étape 2 : Onglet "Consommations"

Saisir les matières premières consommées :

| Champ | Description |
|-------|-------------|
| Produit | Matière première (ex: Farine, Sucre, Beurre) |
| Quantité | Quantité consommée |
| Unité | Unité de mesure |
| Poids/Unité | Poids unitaire en kg |
| Poids (kg) | Calculé automatiquement |
| Coût Unitaire | Récupéré depuis le coût standard du produit |
| Coût Total | Calculé automatiquement |

**Totaux calculés :**
- Total Poids Consommé (kg)
- Total Coût Consommation
- Coût/Kg

### Étape 3 : Onglet "Rebuts Récupérables"

Saisir les rebuts vendables issus de la production :

| Champ | Description |
|-------|-------------|
| Produit | Produit rebut (filtré sur "Est un Rebut Récupérable") |
| Poids (kg) | Poids du rebut |
| Coût/Kg | Coût par kg (récupéré depuis la production) |
| Coût Total | Calculé automatiquement |
| Raison | Défaut Qualité, Problème Machine, etc. |

### Étape 4 : Onglet "Pâte Récupérable"

Saisir la pâte récupérable (réutilisable le lendemain) :

| Champ | Description |
|-------|-------------|
| Produit | Produit pâte (défaut depuis configuration) |
| Poids (kg) | Poids de la pâte récupérée |
| Coût/Kg | Coût par kg |
| Coût Total | Calculé automatiquement |

### Étape 5 : Onglet "Produits Finis"

Saisir les quantités produites :

**Pour SOLO/CLASSICO :**
| Champ | Description |
|-------|-------------|
| Type | SOLO ou CLASSICO |
| Quantité (Cartons) | Nombre de cartons produits |
| Unités/Carton | Automatique depuis config |
| Poids/Carton | Automatique depuis config |
| Prix Vente | Prix de vente du carton |

**Pour Sandwich GF :**
- Un seul type disponible (Sandwich Grand Format)

### Étape 6 : Onglet "Emballage"

Saisir les coûts d'emballage :

| Type | Saisie | Calcul |
|------|--------|--------|
| Carton | Nombre × Prix unitaire | Coût Total |
| Film Ondulé | Poids (kg) × Prix/kg | Coût Total |
| Étiquettes | Nombre × Prix unitaire | Coût Total |
| Autre | Quantité × Prix | Coût Total |

---

## 5. Workflow de Production

```
┌─────────┐     ┌───────────────────┐     ┌──────────┐     ┌────────┐
│BROUILLON│ --> │ CONFIRMÉ/CALCULÉ  │ --> │ VALIDÉ   │ --> │TERMINÉ │
└─────────┘     └───────────────────┘     └──────────┘     └────────┘
                         │                      │
                         v                      v
                    Calcul auto            Génération:
                    des coûts/carton       - BL Consommation
                                           - Achat Prod. Finis
                                           - Achat Rebuts
                                           - Achat Pâte
```

### Actions par État

| État | Action | Description |
|------|--------|-------------|
| Brouillon | `Confirmer et Calculer` | Calcule automatiquement les coûts |
| Confirmé | `Valider et Générer Documents` | Vérifie le stock et crée les documents |
| Validé | `Terminer` | Clôture la production et met à jour les prix de revient |
| Tout état | `Remettre en Brouillon` | Annule et permet modification |

---

## 6. Formules de Calcul

### Poids Bon (Production Nette)

```
Poids Bon = Poids Consommé - Rebuts Récupérables - Pâte Récupérable
```

### Coût Total de Production

```
Coût Total = Coût Matières Premières + Coût Emballage
```

> **Note** : Les rebuts et la pâte récupérable ne sont PAS déduits du coût (ils sont comptabilisés séparément)

### Coût/Kg Bon

```
Coût/Kg Bon = Coût Total / Poids Bon
```

### Calcul SOLO/CLASSICO (avec Ratio)

Le ratio par défaut est **1.65** (configurable).

```
Soit R = Ratio (1.65)
Soit N_solo = Nombre cartons SOLO
Soit N_classico = Nombre cartons CLASSICO
Soit C_total = Coût Total Production

Coût CLASSICO/carton = C_total / (N_classico + R × N_solo)
Coût SOLO/carton = R × Coût CLASSICO/carton
```

**Exemple :**
- Coût Total : 100 000 DA
- SOLO : 50 cartons
- CLASSICO : 100 cartons
- Ratio : 1.65

```
Coût CLASSICO = 100 000 / (100 + 1.65 × 50) = 100 000 / 182.5 = 547.95 DA
Coût SOLO = 1.65 × 547.95 = 904.12 DA
```

### Calcul Sandwich GF (Direct)

```
Coût Sandwich/carton = Coût Total / Nombre Cartons
```

---

## 7. Documents Générés

### BL Consommation (Stock Picking)
- **Type** : Livraison sortante
- **Origine** : DMP → Client "Consommation"
- **Contenu** : Toutes les matières premières consommées

### Achat Produits Finis (Purchase Order)
- **Fournisseur** : "Production"
- **Destination** : DPF
- **Contenu** : Produits finis avec coût calculé
- **Effet** : Entrée en stock au coût de revient

### Achat Rebuts Récupérables
- **Fournisseur** : "Production"
- **Contenu** : Produits rebuts avec leur valorisation
- **Effet** : Entrée en stock (vendable)

### Achat Pâte Récupérable
- **Fournisseur** : "Production"
- **Contenu** : Pâte récupérable
- **Effet** : Entrée en stock AVCO (réutilisable)

---

## 8. Onglet "Résumé des Coûts"

Vue consolidée de la production :

| Section | Champs |
|---------|--------|
| Consommation Matières | Poids total, Coût total, Coût/kg |
| Emballage | Cartons, Film, Total emballage |
| Pertes | Rebuts (kg), Pâte (kg), Total pertes |
| Production Bonne | Poids bon, Coût total, Coût/kg bon |
| Documents Générés | Liens vers BL et Achats créés |

---

## 9. Rapport PDF

### Accès : Bouton `Imprimer` (orange) dans le formulaire

Le rapport contient :
1. Informations générales (date, type, état)
2. Tableau des consommations
3. Tableau des rebuts et pâte
4. Tableau des produits finis
5. Résumé production (poids)
6. Résumé coûts
7. Tableau des coûts de revient par produit

---

## 10. Smart Buttons

| Bouton | Action |
|--------|--------|
| 🚚 BL Consommation | Ouvre le bon de livraison des matières premières |
| 🛒 Achat Prod. Finis | Ouvre la commande d'achat des produits finis |
| ♻️ Achat Rebuts | Ouvre la commande d'achat des rebuts |
| ⚫ Achat Pâte | Ouvre la commande d'achat de la pâte |

---

## 11. Cas d'Usage - Exemple Complet

### Scénario : Production SOLO/CLASSICO du 30/12/2024

**1. Consommations :**
| Produit | Qté | Poids/U | Poids Total | Coût/U | Coût Total |
|---------|-----|---------|-------------|--------|------------|
| Farine | 100 kg | 1 | 100 kg | 50 DA | 5 000 DA |
| Sucre | 50 kg | 1 | 50 kg | 80 DA | 4 000 DA |
| Beurre | 30 kg | 1 | 30 kg | 200 DA | 6 000 DA |
| **TOTAL** | | | **180 kg** | | **15 000 DA** |

**2. Rebuts Récupérables :**
| Produit | Poids | Coût/kg | Coût Total |
|---------|-------|---------|------------|
| Rebut Crème | 5 kg | 83.33 DA | 416.65 DA |

**3. Pâte Récupérable :**
| Produit | Poids | Coût/kg | Coût Total |
|---------|-------|---------|------------|
| Pâte Récup | 10 kg | 83.33 DA | 833.30 DA |

**4. Emballage :**
| Type | Qté | Prix Unit | Coût Total |
|------|-----|-----------|------------|
| Cartons | 150 | 20 DA | 3 000 DA |
| Film Ondulé | 5 kg | 100 DA/kg | 500 DA |
| **TOTAL** | | | **3 500 DA** |

**5. Produits Finis :**
| Type | Cartons |
|------|---------|
| SOLO | 50 |
| CLASSICO | 100 |

**6. Calculs :**
```
Poids Bon = 180 - 5 - 10 = 165 kg
Coût Total = 15 000 + 3 500 = 18 500 DA
Coût/kg Bon = 18 500 / 165 = 112.12 DA/kg

Coût CLASSICO = 18 500 / (100 + 1.65 × 50) = 101.37 DA/carton
Coût SOLO = 1.65 × 101.37 = 167.26 DA/carton
```

---

## 12. Contrôles et Validations

### Contrôle de Stock

Avant de valider une production, le système vérifie automatiquement que **toutes les matières premières** sont disponibles en stock.

**Emplacement vérifié :**
- L'emplacement source du type de picking sortant (BL) du dépôt Matière Première
- Inclut automatiquement tous les emplacements enfants
- C'est le même emplacement qui sera utilisé pour le BL de consommation

**Comportement :**
- Si le stock est insuffisant pour un ou plusieurs produits, un message d'erreur s'affiche avec :
  - Nom de l'emplacement vérifié
  - Produit concerné
  - Quantité requise
  - Quantité disponible
  - Quantité manquante

### Protection contre la Suppression

- Une production à l'état **"Terminé"** ne peut pas être supprimée directement
- Il faut d'abord la **remettre en brouillon** via le bouton correspondant

---

## 13. Validation Automatique des Opérations

### Configuration

Dans `Configuration` > `Paramètres` :

| Option | Par défaut | Description |
|--------|------------|-------------|
| **Valider Opérations Automatiquement** | Non | Active la validation auto des BL et achats |
| **Créer Facture Fournisseur Auto** | Non | Crée les factures fournisseur (si validation auto activée) |

### Comportement si activé

Lors du clic sur **"Valider et Générer Documents"** :

1. **BL Consommation** :
   - Confirmation du picking
   - Attribution des quantités
   - Validation du transfert (sortie de stock)

2. **Achats (Produits Finis, Rebuts, Pâte)** :
   - Confirmation de la commande (Demande → Commande)
   - Réception automatique (entrée en stock)
   - Création de la facture fournisseur (si option activée)

### Flux sans validation automatique

| Document | État après validation production |
|----------|----------------------------------|
| BL Consommation | Brouillon (à valider manuellement) |
| Achats | Demande de prix (à confirmer) |

### Flux avec validation automatique

| Document | État après validation production |
|----------|----------------------------------|
| BL Consommation | Fait (stock sorti) |
| Achats | Commande confirmée + Réception faite |
| Factures | Créées (si option activée) |

---

## 14. Points d'Amélioration Possibles

- [ ] Ajout d'un tableau de bord avec KPIs
- [ ] Historique des coûts par produit
- [ ] Comparaison inter-journalière
- [ ] Alertes sur les écarts de coût
- [ ] Intégration avec la comptabilité analytique
- [ ] Gestion des lots de matières premières

---

## 15. Support

Pour toute question ou amélioration :
- Module : `adi_simple_production_cost`
- Version : 17.0.1.0.0
- Auteur : ADICOPS

---

*Documentation générée le 30/12/2024*
