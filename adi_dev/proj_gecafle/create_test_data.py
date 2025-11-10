# Script à exécuter dans le shell Odoo : python odoo-bin shell -d votre_base

# 1. Créer les producteurs
producteurs = {
    'ch': env['gecafle.producteur'].create({
        'name': 'ch',
        'phone': '0555000001',
        'currency_id': env.company.currency_id.id,
    }),
    'OR': env['gecafle.producteur'].create({
        'name': 'OR',
        'phone': '0555000002',
        'currency_id': env.company.currency_id.id,
    }),
    'mo': env['gecafle.producteur'].create({
        'name': 'mo',
        'phone': '0555000003',
        'currency_id': env.company.currency_id.id,
    }),
    'omr': env['gecafle.producteur'].create({
        'name': 'omr',
        'phone': '0555000004',
        'currency_id': env.company.currency_id.id,
    }),
}

# 2. Créer les produits
produits = {
    'FARISA': env['gecafle.produit'].create({
        'name': 'FARISA',
        'type': 'fruit',
        'producteur_id': producteurs['ch'].id,
    }),
    'climantine': env['gecafle.produit'].create({
        'name': 'climantine',
        'type': 'fruit',
        'producteur_id': producteurs['mo'].id,
    }),
}

# 3. Créer les qualités
qualites = {
    '2CH': env['gecafle.qualite'].create({
        'name': '2CH',
        'code': '2CH',
    }),
    'FR': env['gecafle.qualite'].create({
        'name': 'FR',
        'code': 'FR',
    }),
}

# 4. Créer les types de colis (emballages)
emballages = {
    'CP 0.3': env['gecafle.emballage'].create({
        'name': 'CP 0.3',
        'code': 'CP03',
        'weight': 0.3,
        'price_unit': 10,
    }),
    'CP': env['gecafle.emballage'].create({
        'name': 'CP',
        'code': 'CP',
        'weight': 0.4,
        'price_unit': 12,
    }),
}

# 5. Créer le client
client = env['gecafle.client'].create({
    'name': 'Yazid akbou',
    'tel_mob': '0555123456',
    'adresse': 'Akbou, Béjaïa',
    'est_fidel': False,  # Pour appliquer la consigne
})

# 6. Créer les réceptions avec données spécifiques
from datetime import datetime

receptions_data = [
    {
        'num': '0007141',
        'producteur': 'ch',
        'produit': 'FARISA',
        'qualite': '2CH',
        'emballage': 'CP 0.3',
        'nb_colis': 100,
        'poids_brut': 403.50,
    },
    {
        'num': '0007142',
        'producteur': 'OR',
        'produit': 'FARISA',
        'qualite': '2CH',
        'emballage': 'CP 0.3',
        'nb_colis': 126,
        'poids_brut': 454.00,
    },
    {
        'num': '0007136',
        'producteur': 'mo',
        'produit': 'climantine',
        'qualite': 'FR',
        'emballage': 'CP',
        'nb_colis': 70,
        'poids_brut': 608.50,
    },
    {
        'num': '0007146',
        'producteur': 'omr',
        'produit': 'FARISA',
        'qualite': '2CH',
        'emballage': 'CP 0.3',
        'nb_colis': 61,
        'poids_brut': 210.00,
    },
]

receptions = []
for data in receptions_data:
    # Forcer le numéro de réception
    env.company.reception_counter = int(data['num']) - 1
    
    reception = env['gecafle.reception'].create({
        'producteur_id': producteurs[data['producteur']].id,
        'reception_date': datetime(2025, 1, 10, 8, 0, 0),
        'details_reception_ids': [(0, 0, {
            'designation_id': produits[data['produit']].id,
            'qualite_id': qualites[data['qualite']].id,
            'type_colis_id': emballages[data['emballage']].id,
            'qte_colis_recue': data['nb_colis'],
            'poids_brut': data['poids_brut'],
            'poids_colis': emballages[data['emballage']].weight * data['nb_colis'],
            'poids_net': data['poids_brut'] - (emballages[data['emballage']].weight * data['nb_colis']),
        })]
    })
    reception.action_confirmer()
    receptions.append(reception)

# 7. Créer la vente avec toutes les lignes
env.company.vente_counter = 166653  # Pour avoir le numéro 0166654

vente = env['gecafle.vente'].create({
    'client_id': client.id,
    'date_vente': datetime(2025, 1, 10, 12, 51, 0),
    'utilisateur': 'Admin',
    'observation': '',
    'notes': "Après 08 Jours, Les Colis ne seront pas remboursable",
})

# 8. Ajouter les lignes de vente avec les prix spécifiques
lignes_vente_data = [
    (receptions[0], 470.00),  # ch - FARISA
    (receptions[1], 520.00),  # OR - FARISA
    (receptions[2], 80.00),   # mo - climantine
    (receptions[3], 570.00),  # omr - FARISA
]

for reception, prix in lignes_vente_data:
    detail_reception = reception.details_reception_ids[0]
    env['gecafle.details_ventes'].create({
        'vente_id': vente.id,
        'reception_id': reception.id,
        'detail_reception_id': detail_reception.id,
        'nombre_colis': detail_reception.qte_colis_recue,
        'poids_brut': detail_reception.poids_brut,
        'prix_unitaire': prix,
    })

# 9. Ajouter les emballages (pour le montant consigne)
# 357 colis CP 0.3 (100+126+61) + 70 colis CP
vente.detail_emballage_vente_ids = [
    (0, 0, {
        'emballage_id': emballages['CP 0.3'].id,
        'qte_sortantes': 287,  # 100 + 126 + 61
        'qte_entrantes': 0,
    }),
    (0, 0, {
        'emballage_id': emballages['CP'].id,
        'qte_sortantes': 70,
        'qte_entrantes': 0,
    }),
]

# 10. Valider la vente
vente.action_valider()

# 11. Afficher le résultat
print(f"Vente créée : {vente.name}")
print(f"Client : {vente.client_id.name}")
print(f"Montant Net : {vente.montant_total_net}")
print(f"Montant Consigne : {vente.montant_total_emballages}")
print(f"Montant Total : {vente.montant_total_a_payer}")
