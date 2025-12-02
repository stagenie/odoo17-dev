#!/usr/bin/env python3
"""
Script de test pour vérifier la synchronisation des paiements avec les réceptions.
À exécuter via: odoo-bin shell -c /path/to/odoo.conf -d database_name < test_payment_sync.py
"""

import logging
_logger = logging.getLogger(__name__)

print("=" * 80)
print("TEST DE SYNCHRONISATION DES PAIEMENTS")
print("=" * 80)

# 1. Trouver une réception existante
reception = env['gecafle.reception'].search([('state', '=', 'confirmee')], limit=1)

if not reception:
    print("\n❌ Aucune réception confirmée trouvée. Créez une réception d'abord.")
    exit()

print(f"\n✓ Réception trouvée: {reception.name} (ID: {reception.id})")
print(f"  - avance_producteur actuel: {reception.avance_producteur}")
print(f"  - transport actuel: {reception.transport if hasattr(reception, 'transport') else 'N/A'}")
print(f"  - paiement_emballage actuel: {reception.paiement_emballage if hasattr(reception, 'paiement_emballage') else 'N/A'}")

# 2. Chercher un partenaire ou en créer un
partner = env['res.partner'].search([('supplier_rank', '>', 0)], limit=1)
if not partner:
    partner = env['res.partner'].create({
        'name': 'Test Producteur',
        'supplier_rank': 1,
    })
    print(f"\n✓ Partenaire créé: {partner.name} (ID: {partner.id})")
else:
    print(f"\n✓ Partenaire trouvé: {partner.name} (ID: {partner.id})")

# 3. Test 1: Créer un paiement avance producteur en brouillon
print("\n" + "=" * 80)
print("TEST 1: Création paiement avance producteur en brouillon")
print("=" * 80)

payment_avance = env['account.payment'].create({
    'payment_type': 'outbound',
    'partner_type': 'supplier',
    'partner_id': partner.id,
    'amount': 5000.0,
    'ref': 'Test Avance Producteur',
    'reception_id': reception.id,
    'is_advance_producer': True,
})

print(f"✓ Paiement avance créé (ID: {payment_avance.id}), État: {payment_avance.state}")
reception.refresh()
print(f"  Réception avance_producteur après création (brouillon): {reception.avance_producteur}")
print(f"  -> Devrait être: 0.0 (car le paiement est en brouillon)")

# 4. Test 2: Valider le paiement
print("\n" + "=" * 80)
print("TEST 2: Validation du paiement avance")
print("=" * 80)

payment_avance.action_post()
print(f"✓ Paiement validé, État: {payment_avance.state}")
reception.refresh()
print(f"  Réception avance_producteur après validation: {reception.avance_producteur}")
print(f"  -> Devrait être: 5000.0")

if reception.avance_producteur == 5000.0:
    print("  ✅ SUCCÈS: La synchronisation fonctionne!")
else:
    print(f"  ❌ ÉCHEC: Attendu 5000.0, obtenu {reception.avance_producteur}")

# 5. Test 3: Remettre en brouillon
print("\n" + "=" * 80)
print("TEST 3: Remise en brouillon du paiement")
print("=" * 80)

payment_avance.action_draft()
print(f"✓ Paiement remis en brouillon, État: {payment_avance.state}")
reception.refresh()
print(f"  Réception avance_producteur après remise en brouillon: {reception.avance_producteur}")
print(f"  -> Devrait être: 0.0")

if reception.avance_producteur == 0.0:
    print("  ✅ SUCCÈS: La réinitialisation fonctionne!")
else:
    print(f"  ❌ ÉCHEC: Attendu 0.0, obtenu {reception.avance_producteur}")

# 6. Test 4: Transport
print("\n" + "=" * 80)
print("TEST 4: Paiement Transport")
print("=" * 80)

if hasattr(reception, 'transport'):
    payment_transport = env['account.payment'].create({
        'payment_type': 'outbound',
        'partner_type': 'supplier',
        'partner_id': partner.id,
        'amount': 3000.0,
        'ref': 'Test Transport',
        'reception_id': reception.id,
        'is_advance_transport': True,
    })

    print(f"✓ Paiement transport créé (ID: {payment_transport.id})")
    payment_transport.action_post()
    print(f"✓ Paiement transport validé")
    reception.refresh()
    print(f"  Réception transport après validation: {reception.transport}")
    print(f"  -> Devrait être: 3000.0")

    if reception.transport == 3000.0:
        print("  ✅ SUCCÈS: Synchronisation transport OK!")
    else:
        print(f"  ❌ ÉCHEC: Attendu 3000.0, obtenu {reception.transport}")

    # Nettoyage
    payment_transport.action_draft()
    payment_transport.unlink()
else:
    print("  ⚠️  Champ 'transport' non disponible sur cette réception")

# 7. Test 5: Paiement Emballage
print("\n" + "=" * 80)
print("TEST 5: Paiement Emballage")
print("=" * 80)

if hasattr(reception, 'paiement_emballage'):
    payment_emballage = env['account.payment'].create({
        'payment_type': 'outbound',
        'partner_type': 'supplier',
        'partner_id': partner.id,
        'amount': 2000.0,
        'ref': 'Test Emballage',
        'reception_id': reception.id,
        'is_payment_emballage': True,
    })

    print(f"✓ Paiement emballage créé (ID: {payment_emballage.id})")
    payment_emballage.action_post()
    print(f"✓ Paiement emballage validé")
    reception.refresh()
    print(f"  Réception paiement_emballage après validation: {reception.paiement_emballage}")
    print(f"  -> Devrait être: 2000.0")

    if reception.paiement_emballage == 2000.0:
        print("  ✅ SUCCÈS: Synchronisation emballage OK!")
    else:
        print(f"  ❌ ÉCHEC: Attendu 2000.0, obtenu {reception.paiement_emballage}")

    # Nettoyage
    payment_emballage.action_draft()
    payment_emballage.unlink()
else:
    print("  ⚠️  Champ 'paiement_emballage' non disponible sur cette réception")

# Nettoyage final
print("\n" + "=" * 80)
print("NETTOYAGE")
print("=" * 80)
payment_avance.unlink()
print("✓ Paiement test supprimé")

print("\n" + "=" * 80)
print("TESTS TERMINÉS")
print("=" * 80)
print("\nVérifiez les logs Odoo pour les messages [PAYMENT SYNC]")
print("Commande: tail -f /var/log/odoo/odoo.log | grep 'PAYMENT SYNC'")
