# Guide du Processus SAV Electroménager

## Module Odoo 17 - Gestion des Retours et Service Après-Vente

---

**Version:** 17.0.1.0.0
**Date:** Janvier 2026
**Éditeur:** ADI Dev

---

## 1. Présentation Générale

Le module **SAV Electroménager** permet de gérer le cycle complet des retours et réparations d'appareils électroménagers. Il assure une traçabilité totale des articles depuis la déclaration du retour jusqu'à la remise au client final.

### 1.1 Objectifs du module

- Centraliser la gestion des retours SAV
- Assurer la traçabilité des articles par numéro de série
- Coordonner les échanges entre Points de Vente, Centre de Retour et Réparateurs
- Générer automatiquement les documents de suivi (bons de livraison, bons de retour)
- Fournir des statistiques et rapports d'analyse

---

## 2. Les Acteurs du Circuit

Le module définit trois types d'acteurs principaux :

### 2.1 Point de Vente

- **Rôle :** Déclare les retours SAV auprès du Centre de Retour
- **Actions :**
  - Créer un nouveau dossier de retour
  - Saisir les articles retournés avec leurs numéros de série
  - Soumettre le dossier au Centre de Retour
  - Réceptionner les articles réparés et clôturer le dossier

### 2.2 Centre de Retour

- **Rôle :** Centralise les retours et coordonne avec les réparateurs
- **Actions :**
  - Réceptionner les articles des Points de Vente
  - Envoyer les articles au Réparateur
  - Suivre l'avancement des réparations
  - Réceptionner les articles réparés
  - Renvoyer les articles aux Points de Vente

### 2.3 Réparateur

- **Rôle :** Effectue les réparations techniques
- **Actions :**
  - Recevoir les articles à réparer
  - Effectuer le diagnostic et les réparations
  - Signaler le statut de chaque article (Réparé, Changé, Non Réparable, Refusé)

---

## 3. Workflow du Retour SAV

Le processus SAV suit un circuit en **10 étapes** :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WORKFLOW SAV COMPLET                               │
└─────────────────────────────────────────────────────────────────────────────┘

   POINT DE VENTE                 CENTRE DE RETOUR                  RÉPARATEUR
   ─────────────────────────────────────────────────────────────────────────────

   ┌──────────────┐
   │  1. BROUILLON │ ◄── Création du dossier de retour
   └──────┬───────┘
          │ Soumettre
          ▼
   ┌──────────────────┐
   │ 2. SOUMIS AU     │ ◄── Dossier transmis au Centre
   │    CENTRE        │
   └──────┬───────────┘
          │
          ▼
                              ┌──────────────────┐
                              │ 3. REÇU AU       │ ◄── Centre confirme réception
                              │    CENTRE        │
                              └──────┬───────────┘
                                     │ Envoyer au réparateur
                                     ▼
                              ┌──────────────────┐
                              │ 4. ENVOYÉ AU     │ ◄── Articles en transit
                              │    RÉPARATEUR    │
                              └──────┬───────────┘
                                     │
                                     ▼
                                                         ┌──────────────────┐
                                                         │ 5. EN RÉPARATION │
                                                         └──────┬───────────┘
                                                                │ Réparer
                                                                ▼
                                                         ┌──────────────────┐
                                                         │ 6. RÉPARÉ        │
                                                         └──────┬───────────┘
                                     │                          │
                                     ▼◄─────────────────────────┘
                              ┌──────────────────┐
                              │ 7. RETOURNÉ AU   │ ◄── Articles réparés reçus
                              │    CENTRE        │
                              └──────┬───────────┘
                                     │ Renvoyer au Point de Vente
                                     ▼
                              ┌──────────────────┐
                              │ 8. RENVOYÉ AU    │ ◄── Articles en transit
                              │    POINT VENTE   │
                              └──────┬───────────┘
          │◄─────────────────────────┘
          ▼
   ┌──────────────┐
   │ 9. CLÔTURÉ   │ ◄── Dossier terminé
   └──────────────┘

   ┌──────────────┐
   │ 10. ANNULÉ   │ ◄── Possible à tout moment (sauf clôturé)
   └──────────────┘
```

### 3.1 Description des étapes

| N° | État | Description | Acteur responsable |
|:--:|------|-------------|-------------------|
| 1 | **Brouillon** | Création du dossier, saisie des articles | Point de Vente |
| 2 | **Soumis au Centre** | Dossier validé et transmis | Point de Vente |
| 3 | **Reçu au Centre** | Articles physiquement reçus au centre | Centre de Retour |
| 4 | **Envoyé au Réparateur** | Articles expédiés pour réparation | Centre de Retour |
| 5 | **En Réparation** | Réparation en cours | Réparateur |
| 6 | **Réparé** | Réparation terminée | Réparateur |
| 7 | **Retourné au Centre** | Articles réparés reçus au centre | Centre de Retour |
| 8 | **Renvoyé au Point Vente** | Articles expédiés au point de vente | Centre de Retour |
| 9 | **Clôturé** | Dossier terminé avec succès | Point de Vente |
| 10 | **Annulé** | Dossier annulé | Tout acteur autorisé |

---

## 4. Informations Saisies

### 4.1 En-tête du Retour

| Champ | Description | Obligatoire |
|-------|-------------|:-----------:|
| Référence | Numéro automatique (ex: SAV/2026/00001) | Oui |
| Date | Date de création du retour | Oui |
| Point de Vente | Magasin qui déclare le retour | Oui |
| Centre de Retour | Centre qui gère le dossier | Oui |
| Réparateur | Prestataire de réparation | Non* |
| Client Final | Client ayant acheté le produit | Non |
| Commandes Origine | Bons de vente liés | Non |
| BL Origine | Bons de livraison liés | Non |
| Priorité | Normal, Bas, Moyen, Urgent | Non |
| Observations | Remarques générales | Non |

*Le réparateur devient obligatoire lors de l'envoi en réparation.

### 4.2 Lignes d'Articles Retournés

Chaque article retourné est saisi sur une ligne distincte :

| Champ | Description | Obligatoire |
|-------|-------------|:-----------:|
| Article | Produit retourné | Oui |
| Catégorie | Catégorie d'électroménager | Oui |
| N° de Série | Numéro de série unique | Oui |
| Motif de Retour | Type de panne constaté | Oui |
| État du Produit | Bon état, Endommagé, Cassé, Incomplet | Oui |
| Diagnostic | Description technique du problème | Non |
| Statut Réparation | En attente, Réparé, Changé, Non réparable, Refusé | Oui |
| Notes de Réparation | Détails sur l'intervention | Non |

---

## 5. Catégories de Produits

Les articles sont classés dans les catégories suivantes :

| Code | Catégorie | Description |
|------|-----------|-------------|
| CONG | Congélation | Congélateurs, compartiments de congélation |
| REFR | Refroidissement | Réfrigérateurs, climatiseurs |
| CUIS | Cuisson | Cuisinières, fours, plaques de cuisson |
| LAVA | Lavage | Lave-linge, lave-vaisselle |
| SECH | Séchage | Sèche-linge |
| PEM | Petit Electroménager | Robots, mixeurs, cafetières, etc. |
| CHAU | Chauffage | Chauffages, chauffe-eau |
| VENT | Ventilation | Ventilateurs, hottes aspirantes |

---

## 6. Types de Pannes

Les motifs de retour prédéfinis couvrent les pannes les plus courantes :

### Pannes liées au Froid
- Problème de Refroidissement
- Formation de Givre
- Compresseur HS

### Pannes liées au Chauffage
- Problème de Chauffage
- Surchauffe
- Thermostat Défectueux

### Pannes Électriques
- Ne S'allume Pas
- Problème Électrique
- Problème d'Affichage

### Pannes Mécaniques
- Bruit Anormal
- Vibration Excessive
- Problème Moteur

### Pannes liées à l'Eau
- Fuite d'Eau
- Problème de Vidange
- Problème d'Arrivée d'Eau

### Autres Pannes
- Problème de Porte
- Autre

---

## 7. Rôles Utilisateurs et Droits d'Accès

### 7.1 Utilisateur Point de Vente

- **Accès :** Uniquement les retours de son point de vente
- **Droits :**
  - Créer des retours
  - Modifier ses retours
  - Soumettre au centre
  - Clôturer les retours

### 7.2 Gérant Centre de Retour

- **Accès :** Tous les retours de son centre
- **Droits :**
  - Tous les droits du Point de Vente
  - Confirmer les réceptions
  - Envoyer au réparateur
  - Marquer les réparations
  - Renvoyer au point de vente
  - Supprimer des retours

### 7.3 Administrateur SAV

- **Accès :** Tous les retours de toutes les entités
- **Droits :**
  - Accès total en lecture/écriture
  - Gestion de la configuration (catégories, types de pannes)
  - Accès aux statistiques globales

---

## 8. Documents PDF Générés

Le module génère automatiquement trois types de documents :

### 8.1 Bon de Livraison Centre → Réparateur
- Liste des articles envoyés au réparateur
- Détails de chaque article (produit, N° série, motif)
- Généré lors de l'envoi au réparateur

### 8.2 Bon de Retour Réparateur → Centre
- Liste des articles retournés par le réparateur
- Statut de réparation de chaque article
- Généré lors du retour au centre

### 8.3 Bon de Livraison Centre → Point de Vente
- Liste des articles renvoyés au point de vente
- Résultat final de chaque réparation
- Généré lors de l'envoi au point de vente

---

## 9. Traçabilité et Historique

Le module assure une traçabilité complète grâce à :

### 9.1 Dates de suivi automatiques
- Date de soumission
- Date de réception au centre
- Date d'envoi au réparateur
- Date de début de réparation
- Date de fin de réparation
- Date de retour au centre
- Date d'envoi au point de vente
- Date de clôture

### 9.2 Historique des modifications
- Chaque changement d'état est enregistré
- Les modifications sont visibles dans le chatter Odoo
- Audit complet des actions utilisateurs

---

## 10. Statistiques et Rapports

Le module fournit des outils d'analyse :

- **Vue Pivot :** Analyse croisée par point de vente, centre, réparateur, catégorie, type de panne
- **Vue Graphique :** Visualisation des tendances
- **Filtres avancés :** Par état, période, acteur
- **Compteurs :** Nombre d'articles total, réparés, non réparables, en attente

---

## 11. Guide d'Utilisation Rapide

### Pour le Point de Vente

1. Accéder au menu **SAV > Retours SAV**
2. Cliquer sur **Créer**
3. Saisir les informations du client (optionnel)
4. Ajouter les articles retournés avec leurs numéros de série
5. Sélectionner le motif de retour pour chaque article
6. Cliquer sur **Soumettre au Centre**
7. Attendre le retour des articles réparés
8. Cliquer sur **Clôturer** une fois les articles récupérés

### Pour le Centre de Retour

1. Consulter les retours soumis dans la liste
2. Confirmer la réception physique des articles
3. Sélectionner un réparateur et envoyer les articles
4. Suivre l'avancement via les états
5. Réceptionner les articles réparés
6. Renvoyer au point de vente

---

## 12. Contacts et Support

Pour toute question ou assistance technique, contactez votre administrateur système ou l'équipe de support ADI Dev.

---

*Document à usage interne - Confidentiel*

