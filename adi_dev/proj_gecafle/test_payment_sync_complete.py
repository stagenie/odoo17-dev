#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test complet pour la synchronisation des paiements
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Configuration de la base de données
DB_CONFIG = {
    'host': None,  # Utiliser socket Unix
    'database': 'o17_gecafle_final_base',
    'user': 'stadev',
    'password': 'St@dev',
    'port': 5432
}

def create_test_reception():
    """Crée une réception de test si elle n'existe pas"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n=== CRÉATION D'UNE RÉCEPTION DE TEST ===")

    # Chercher un producteur existant
    cursor.execute("SELECT id, name FROM gecafle_producteur LIMIT 1")
    producteur = cursor.fetchone()

    if not producteur:
        print("⚠️  Aucun producteur trouvé. Création d'un producteur de test...")

        # Créer le producteur avec la structure correcte
        cursor.execute("""
            INSERT INTO gecafle_producteur
            (name, address, phone, language,
             create_uid, write_uid, create_date, write_date)
            VALUES
            ('"PRODUCTEUR TEST SYNC"'::jsonb, '"Adresse Test"'::jsonb, '0123456789', 'fr_FR',
             2, 2, NOW(), NOW())
            ON CONFLICT (name) DO UPDATE
            SET write_date = NOW()
            RETURNING id, name
        """)

        producteur = cursor.fetchone()
        # La colonne name est de type jsonb, donc on extrait le texte
        producteur['name'] = producteur['name'].strip('"') if isinstance(producteur['name'], str) else producteur['name']
        conn.commit()
        print(f"✅ Producteur de test créé : {producteur['name']} (ID: {producteur['id']})")

    # Vérifier si une réception de test existe déjà
    cursor.execute("""
        SELECT id, name FROM gecafle_reception
        WHERE name = 'REC/TEST/SYNC'
        LIMIT 1
    """)
    existing_reception = cursor.fetchone()

    if existing_reception:
        reception = existing_reception
        print(f"   Utilisation de la réception existante : {reception['name']} (ID: {reception['id']})")
        # Réinitialiser les montants
        cursor.execute("""
            UPDATE gecafle_reception
            SET avance_producteur = 0, transport = 0, paiement_emballage = 0
            WHERE id = %s
        """, (reception['id'],))
    else:
        # Obtenir la devise par défaut
        cursor.execute("SELECT id FROM res_currency WHERE name = 'DZD' LIMIT 1")
        currency = cursor.fetchone()
        if not currency:
            cursor.execute("SELECT id FROM res_currency LIMIT 1")
            currency = cursor.fetchone()
        currency_id = currency['id'] if currency else 1

        # Créer une nouvelle réception de test
        cursor.execute("""
            INSERT INTO gecafle_reception
            (name, reception_date, user_id, state, producteur_id,
             avance_producteur, transport, paiement_emballage, currency_id,
             create_uid, write_uid, create_date, write_date)
            VALUES
            ('REC/TEST/SYNC', NOW(), 2, 'brouillon', %s,
             0, 0, 0, %s,
             2, 2, NOW(), NOW())
            RETURNING id, name
        """, (producteur['id'], currency_id))
        reception = cursor.fetchone()

    conn.commit()

    print(f"✅ Réception créée/mise à jour : {reception['name']} (ID: {reception['id']})")
    print(f"   Producteur : {producteur['name']}")

    cursor.close()
    conn.close()
    return reception['id']

def create_test_payments(reception_id):
    """Crée des paiements de test pour chaque type"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n=== CRÉATION DES PAIEMENTS DE TEST ===")

    # Créer ou obtenir un partner pour les paiements
    cursor.execute("""
        SELECT id FROM res_partner
        WHERE name = 'PRODUCTEUR TEST SYNC'
        LIMIT 1
    """)

    result = cursor.fetchone()
    if result:
        partner_id = result['id']
    else:
        # Créer un partner de test
        cursor.execute("""
            INSERT INTO res_partner
            (name, is_company, customer_rank, supplier_rank,
             create_uid, write_uid, create_date, write_date)
            VALUES
            ('PRODUCTEUR TEST SYNC', FALSE, 0, 1,
             2, 2, NOW(), NOW())
            RETURNING id
        """)
        partner_id = cursor.fetchone()['id']
        conn.commit()

    # Créer les paiements de test
    test_payments = [
        {
            'name': 'PAYMENT/AVANCE/TEST',
            'amount': 5000.00,
            'is_advance_producer': True,
            'is_advance_transport': False,
            'is_payment_emballage': False,
            'type_desc': 'Avance Producteur'
        },
        {
            'name': 'PAYMENT/TRANSPORT/TEST',
            'amount': 1500.00,
            'is_advance_producer': False,
            'is_advance_transport': True,
            'is_payment_emballage': False,
            'type_desc': 'Transport'
        },
        {
            'name': 'PAYMENT/EMBALLAGE/TEST',
            'amount': 2000.00,
            'is_advance_producer': False,
            'is_advance_transport': False,
            'is_payment_emballage': True,
            'type_desc': 'Emballage'
        }
    ]

    created_payments = []

    for payment_data in test_payments:
        # Vérifier si le paiement existe déjà
        cursor.execute("""
            SELECT id, state, amount FROM account_payment
            WHERE reception_id = %s
            AND is_advance_producer = %s
            AND is_advance_transport = %s
            AND is_payment_emballage = %s
            LIMIT 1
        """, (reception_id,
              payment_data['is_advance_producer'],
              payment_data['is_advance_transport'],
              payment_data['is_payment_emballage']))

        existing = cursor.fetchone()

        if existing:
            print(f"   Paiement {payment_data['type_desc']} existe déjà (ID: {existing['id']})")
            created_payments.append(existing['id'])
        else:
            # Créer un nouveau paiement
            cursor.execute("""
                INSERT INTO account_payment
                (payment_type, partner_type, partner_id, amount,
                 date, ref, state, reception_id,
                 is_advance_producer, is_advance_transport, is_payment_emballage,
                 create_uid, write_uid, create_date, write_date)
                VALUES
                ('outbound', 'supplier', %s, %s,
                 NOW()::DATE, %s, 'draft', %s,
                 %s, %s, %s,
                 2, 2, NOW(), NOW())
                RETURNING id
            """, (partner_id,
                  payment_data['amount'],
                  payment_data['type_desc'],
                  reception_id,
                  payment_data['is_advance_producer'],
                  payment_data['is_advance_transport'],
                  payment_data['is_payment_emballage']))

            new_payment = cursor.fetchone()
            created_payments.append(new_payment['id'])
            print(f"✅ Paiement {payment_data['type_desc']} créé (ID: {new_payment['id']}) - Montant: {payment_data['amount']}")

    conn.commit()
    cursor.close()
    conn.close()
    return created_payments

def test_payment_sync(reception_id, payment_ids):
    """Teste la synchronisation en validant les paiements"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n=== TEST DE SYNCHRONISATION ===")

    # État initial de la réception
    cursor.execute("""
        SELECT avance_producteur, transport, paiement_emballage
        FROM gecafle_reception
        WHERE id = %s
    """, (reception_id,))

    initial_state = cursor.fetchone()
    print(f"\n📊 État initial de la réception :")
    print(f"   - Avance producteur : {initial_state['avance_producteur']}")
    print(f"   - Transport : {initial_state['transport']}")
    print(f"   - Paiement emballage : {initial_state['paiement_emballage']}")

    # Valider chaque paiement et vérifier la synchronisation
    for payment_id in payment_ids:
        cursor.execute("""
            SELECT
                p.id,
                p.amount,
                p.state,
                p.is_advance_producer,
                p.is_advance_transport,
                p.is_payment_emballage,
                CASE
                    WHEN p.is_advance_producer THEN 'Avance Producteur'
                    WHEN p.is_advance_transport THEN 'Transport'
                    WHEN p.is_payment_emballage THEN 'Emballage'
                    ELSE 'Standard'
                END as type_desc
            FROM account_payment p
            WHERE p.id = %s
        """, (payment_id,))

        payment = cursor.fetchone()

        print(f"\n🔄 Validation du paiement {payment['type_desc']} (ID: {payment_id})")
        print(f"   Montant : {payment['amount']}")

        # Simuler la validation (passer à 'posted')
        cursor.execute("""
            UPDATE account_payment
            SET state = 'posted', write_date = NOW()
            WHERE id = %s
        """, (payment_id,))

        conn.commit()

        # Attendre un peu pour que la synchronisation ait lieu
        import time
        time.sleep(0.5)

        # Vérifier l'état de la réception après validation
        cursor.execute("""
            SELECT avance_producteur, transport, paiement_emballage
            FROM gecafle_reception
            WHERE id = %s
        """, (reception_id,))

        new_state = cursor.fetchone()

        # Déterminer quel champ devrait avoir changé
        if payment['is_advance_producer']:
            if new_state['avance_producteur'] == payment['amount']:
                print(f"   ✅ Synchronisation OK : avance_producteur = {new_state['avance_producteur']}")
            else:
                print(f"   ❌ ERREUR : avance_producteur = {new_state['avance_producteur']} (attendu : {payment['amount']})")

        elif payment['is_advance_transport']:
            if new_state['transport'] == payment['amount']:
                print(f"   ✅ Synchronisation OK : transport = {new_state['transport']}")
            else:
                print(f"   ❌ ERREUR : transport = {new_state['transport']} (attendu : {payment['amount']})")

        elif payment['is_payment_emballage']:
            if new_state['paiement_emballage'] == payment['amount']:
                print(f"   ✅ Synchronisation OK : paiement_emballage = {new_state['paiement_emballage']}")
            else:
                print(f"   ❌ ERREUR : paiement_emballage = {new_state['paiement_emballage']} (attendu : {payment['amount']})")

    # État final
    cursor.execute("""
        SELECT avance_producteur, transport, paiement_emballage
        FROM gecafle_reception
        WHERE id = %s
    """, (reception_id,))

    final_state = cursor.fetchone()
    print(f"\n📊 État final de la réception :")
    print(f"   - Avance producteur : {final_state['avance_producteur']}")
    print(f"   - Transport : {final_state['transport']}")
    print(f"   - Paiement emballage : {final_state['paiement_emballage']}")

    cursor.close()
    conn.close()

def test_payment_cancellation(reception_id, payment_ids):
    """Teste la synchronisation lors de l'annulation des paiements"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n=== TEST D'ANNULATION DES PAIEMENTS ===")

    # Annuler le premier paiement
    if payment_ids:
        payment_id = payment_ids[0]

        cursor.execute("""
            UPDATE account_payment
            SET state = 'cancel', write_date = NOW()
            WHERE id = %s
            RETURNING is_advance_producer, is_advance_transport, is_payment_emballage, amount
        """, (payment_id,))

        payment = cursor.fetchone()
        conn.commit()

        print(f"🔄 Annulation du paiement ID {payment_id}")

        # Vérifier la synchronisation
        cursor.execute("""
            SELECT avance_producteur, transport, paiement_emballage
            FROM gecafle_reception
            WHERE id = %s
        """, (reception_id,))

        state = cursor.fetchone()

        if payment['is_advance_producer']:
            if state['avance_producteur'] == 0:
                print(f"   ✅ Synchronisation OK : avance_producteur remis à 0")
            else:
                print(f"   ❌ ERREUR : avance_producteur = {state['avance_producteur']} (attendu : 0)")

    cursor.close()
    conn.close()

def main():
    print("\n" + "="*60)
    print("TEST COMPLET DE LA SYNCHRONISATION DES PAIEMENTS")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    try:
        # 1. Créer une réception de test
        reception_id = create_test_reception()
        if not reception_id:
            return

        # 2. Créer des paiements de test
        payment_ids = create_test_payments(reception_id)

        # 3. Tester la synchronisation lors de la validation
        test_payment_sync(reception_id, payment_ids)

        # 4. Tester la synchronisation lors de l'annulation
        test_payment_cancellation(reception_id, payment_ids)

        print("\n" + "="*60)
        print("TEST TERMINÉ AVEC SUCCÈS")
        print("="*60)

        print("\n📝 NOTES :")
        print("   - Si la synchronisation ne fonctionne pas automatiquement,")
        print("     vérifiez que les modules Odoo sont bien redémarrés")
        print("   - Les logs Odoo contiendront des messages [PAYMENT SYNC]")
        print("     pour déboguer les problèmes")

    except Exception as e:
        print(f"\n❌ ERREUR lors du test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()