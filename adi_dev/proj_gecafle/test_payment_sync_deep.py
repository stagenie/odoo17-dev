#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test approfondi pour la synchronisation des paiements
"""

import sys
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

# Chemin vers Odoo
odoo_path = '/opt/odoo/odoo17'
sys.path.insert(0, odoo_path)

# Configuration Odoo
import odoo
from odoo import api, SUPERUSER_ID

# Nom de la base de données
db_name = 'o17_gecafle_final_base'

def test_payment_sync():
    """Test de la synchronisation des paiements"""
    _logger.info("=" * 80)
    _logger.info("DÉBUT DU TEST DE SYNCHRONISATION DES PAIEMENTS")
    _logger.info("=" * 80)

    # Initialiser Odoo
    odoo.tools.config.parse_config([
        '--database', db_name,
        '--db_host', 'localhost',
        '--db_user', 'stadev',
        '--db_password', 'St@dev'
    ])

    with odoo.api.Environment.manage():
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # 1. Chercher une réception
            _logger.info("\n1. Recherche d'une réception...")
            reception = env['gecafle.reception'].search([('state', '=', 'brouillon')], limit=1)

            if not reception:
                _logger.info("   Création d'une réception de test...")
                # Chercher un producteur
                producteur = env['gecafle.producteur'].search([], limit=1)
                if not producteur:
                    _logger.error("   ❌ Aucun producteur trouvé! Impossible de créer une réception")
                    return

                reception = env['gecafle.reception'].create({
                    'producteur_id': producteur.id,
                    'reception_date': '2025-01-15',
                    'observations': 'Test synchronisation paiements',
                })
                _logger.info(f"   ✅ Réception créée: {reception.name} (ID: {reception.id})")
            else:
                _logger.info(f"   ✅ Réception trouvée: {reception.name} (ID: {reception.id})")

            # Afficher les valeurs actuelles
            _logger.info(f"\n   Valeurs actuelles de la réception:")
            _logger.info(f"   - avance_producteur: {reception.avance_producteur}")
            _logger.info(f"   - transport: {reception.transport}")
            _logger.info(f"   - paiement_emballage: {reception.paiement_emballage}")

            # 2. Créer un partenaire si nécessaire
            _logger.info("\n2. Vérification du partenaire...")
            partner = reception._get_or_create_partner()
            _logger.info(f"   ✅ Partenaire: {partner.name} (ID: {partner.id})")

            # 3. Créer un paiement avance producteur EN BROUILLON
            _logger.info("\n3. Création d'un paiement avance producteur EN BROUILLON...")
            payment = env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id,
                'amount': 5000.0,
                'date': '2025-01-15',
                'ref': f'Test Avance {reception.name}',
                'reception_id': reception.id,
                'is_advance_producer': True,
            })
            _logger.info(f"   ✅ Paiement créé: ID {payment.id}")
            _logger.info(f"   - État du paiement: {payment.move_id.state if payment.move_id else 'Pas de move_id'}")
            _logger.info(f"   - Montant: {payment.amount}")

            # Vérifier la valeur de la réception (devrait être 0 car le paiement n'est pas posté)
            reception.refresh()
            _logger.info(f"\n   Après création du paiement EN BROUILLON:")
            _logger.info(f"   - avance_producteur: {reception.avance_producteur} (devrait être 0)")

            # 4. Valider le paiement (action_post)
            _logger.info("\n4. Validation du paiement (transition vers 'posted')...")
            try:
                payment.action_post()
                _logger.info(f"   ✅ Paiement validé")
                _logger.info(f"   - Nouvel état: {payment.move_id.state if payment.move_id else 'Pas de move_id'}")
            except Exception as e:
                _logger.error(f"   ❌ Erreur lors de la validation: {e}")
                import traceback
                _logger.error(traceback.format_exc())
                return

            # Vérifier la synchronisation
            reception.refresh()
            _logger.info(f"\n   Après validation du paiement:")
            _logger.info(f"   - avance_producteur: {reception.avance_producteur} (devrait être 5000.0)")

            if reception.avance_producteur == 5000.0:
                _logger.info("   ✅ ✅ ✅ SYNCHRONISATION RÉUSSIE!")
            else:
                _logger.error("   ❌ ❌ ❌ SYNCHRONISATION ÉCHOUÉE!")
                _logger.error(f"   Valeur attendue: 5000.0")
                _logger.error(f"   Valeur obtenue: {reception.avance_producteur}")

                # Vérifier directement en base
                _logger.info("\n   Vérification directe en base de données...")
                cr.execute("""
                    SELECT avance_producteur, transport, paiement_emballage
                    FROM gecafle_reception
                    WHERE id = %s
                """, (reception.id,))
                result = cr.fetchone()
                if result:
                    _logger.info(f"   Valeurs en base: avance={result[0]}, transport={result[1]}, emballage={result[2]}")

            # 5. Test avec paiement transport
            _logger.info("\n5. Test avec paiement TRANSPORT...")
            payment_transport = env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id,
                'amount': 1500.0,
                'date': '2025-01-15',
                'ref': f'Test Transport {reception.name}',
                'reception_id': reception.id,
                'is_advance_transport': True,
            })
            _logger.info(f"   ✅ Paiement transport créé: ID {payment_transport.id}")

            # Valider
            payment_transport.action_post()
            _logger.info(f"   ✅ Paiement transport validé")

            # Vérifier
            reception.refresh()
            _logger.info(f"\n   Après validation du paiement transport:")
            _logger.info(f"   - transport: {reception.transport} (devrait être 1500.0)")

            if reception.transport == 1500.0:
                _logger.info("   ✅ ✅ ✅ SYNCHRONISATION TRANSPORT RÉUSSIE!")
            else:
                _logger.error("   ❌ ❌ ❌ SYNCHRONISATION TRANSPORT ÉCHOUÉE!")

            # 6. Test avec paiement emballage
            _logger.info("\n6. Test avec paiement EMBALLAGE...")
            payment_emballage = env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id,
                'amount': 800.0,
                'date': '2025-01-15',
                'ref': f'Test Emballage {reception.name}',
                'reception_id': reception.id,
                'is_payment_emballage': True,
            })
            _logger.info(f"   ✅ Paiement emballage créé: ID {payment_emballage.id}")

            # Valider
            payment_emballage.action_post()
            _logger.info(f"   ✅ Paiement emballage validé")

            # Vérifier
            reception.refresh()
            _logger.info(f"\n   Après validation du paiement emballage:")
            _logger.info(f"   - paiement_emballage: {reception.paiement_emballage} (devrait être 800.0)")

            if reception.paiement_emballage == 800.0:
                _logger.info("   ✅ ✅ ✅ SYNCHRONISATION EMBALLAGE RÉUSSIE!")
            else:
                _logger.error("   ❌ ❌ ❌ SYNCHRONISATION EMBALLAGE ÉCHOUÉE!")

            # Résumé final
            _logger.info("\n" + "=" * 80)
            _logger.info("RÉSUMÉ FINAL")
            _logger.info("=" * 80)
            _logger.info(f"Réception: {reception.name}")
            _logger.info(f"  - Avance producteur: {reception.avance_producteur} (attendu: 5000.0)")
            _logger.info(f"  - Transport: {reception.transport} (attendu: 1500.0)")
            _logger.info(f"  - Emballage: {reception.paiement_emballage} (attendu: 800.0)")

            # Ne pas commit pour éviter de polluer la base
            _logger.info("\n⚠️  ROLLBACK de la transaction de test...")
            cr.rollback()
            _logger.info("✅ Test terminé (aucune modification permanente)")

if __name__ == '__main__':
    try:
        test_payment_sync()
    except Exception as e:
        _logger.error(f"Erreur fatale: {e}")
        import traceback
        _logger.error(traceback.format_exc())
        sys.exit(1)
