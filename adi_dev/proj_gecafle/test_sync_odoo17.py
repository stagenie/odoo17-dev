#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour la synchronisation des paiements - Version Odoo 17
Prend en compte que l'état est dans account_move.state et non payment.state
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

def test_payment_validation():
    """Test de la synchronisation lors de la validation d'un paiement"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("TEST DE SYNCHRONISATION - ODOO 17")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    # 1. Trouver ou créer une réception de test
    cursor.execute("""
        SELECT id, name, avance_producteur, transport, paiement_emballage
        FROM gecafle_reception
        WHERE name LIKE '%TEST%'
        ORDER BY id DESC
        LIMIT 1
    """)

    reception = cursor.fetchone()
    if not reception:
        print("\n⚠️ Aucune réception de test trouvée. Créez une réception avec 'TEST' dans le nom.")
        cursor.close()
        conn.close()
        return

    print(f"\n📋 Réception de test: {reception['name']} (ID: {reception['id']})")
    print(f"   Valeurs initiales:")
    print(f"   - avance_producteur: {reception['avance_producteur']}")
    print(f"   - transport: {reception['transport']}")
    print(f"   - paiement_emballage: {reception['paiement_emballage']}")

    # 2. Créer un paiement de test
    print("\n🔄 Création d'un paiement de test...")

    # Obtenir une devise
    cursor.execute("SELECT id FROM res_currency WHERE name = 'DZD' LIMIT 1")
    currency = cursor.fetchone()
    currency_id = currency['id'] if currency else 1

    # Créer un journal de paiement s'il n'existe pas
    cursor.execute("""
        SELECT id FROM account_journal
        WHERE type = 'cash'
        LIMIT 1
    """)
    journal = cursor.fetchone()
    if not journal:
        print("❌ Aucun journal de type 'cash' trouvé")
        return
    journal_id = journal['id']

    # Créer une écriture comptable (account.move)
    cursor.execute("""
        INSERT INTO account_move
        (name, move_type, state, journal_id, currency_id,
         create_uid, write_uid, create_date, write_date, date)
        VALUES
        ('PAYMENT/TEST/001', 'entry', 'draft', %s, %s,
         2, 2, NOW(), NOW(), NOW()::DATE)
        RETURNING id
    """, (journal_id, currency_id))

    move_id = cursor.fetchone()['id']
    conn.commit()

    print(f"   ✅ Écriture comptable créée (ID: {move_id})")

    # Créer le paiement lié
    cursor.execute("""
        INSERT INTO account_payment
        (payment_type, partner_type, amount, move_id,
         reception_id, is_advance_producer, is_advance_transport, is_payment_emballage,
         currency_id, create_uid, write_uid, create_date, write_date)
        VALUES
        ('outbound', 'supplier', 7777.00, %s,
         %s, TRUE, FALSE, FALSE,
         %s, 2, 2, NOW(), NOW())
        RETURNING id
    """, (move_id, reception['id'], currency_id))

    payment_id = cursor.fetchone()['id']
    conn.commit()

    print(f"   ✅ Paiement créé (ID: {payment_id}) - Type: Avance Producteur - Montant: 7777.00")

    # 3. Valider l'écriture comptable (ce qui devrait déclencher la synchronisation)
    print("\n📝 Validation de l'écriture comptable...")

    cursor.execute("""
        UPDATE account_move
        SET state = 'posted'
        WHERE id = %s
    """, (move_id,))
    conn.commit()

    print("   ✅ Écriture comptable validée (state = 'posted')")

    # 4. Vérifier la synchronisation
    print("\n🔍 Vérification de la synchronisation...")

    cursor.execute("""
        SELECT avance_producteur, transport, paiement_emballage
        FROM gecafle_reception
        WHERE id = %s
    """, (reception['id'],))

    result = cursor.fetchone()

    print(f"\n📊 Résultat après validation:")
    print(f"   - avance_producteur: {result['avance_producteur']} {'✅ SYNCHRONISÉ' if result['avance_producteur'] == 7777.00 else '❌ NON SYNCHRONISÉ'}")
    print(f"   - transport: {result['transport']}")
    print(f"   - paiement_emballage: {result['paiement_emballage']}")

    # 5. Test de remise en brouillon
    print("\n🔄 Test de remise en brouillon...")

    cursor.execute("""
        UPDATE account_move
        SET state = 'draft'
        WHERE id = %s
    """, (move_id,))
    conn.commit()

    cursor.execute("""
        SELECT avance_producteur
        FROM gecafle_reception
        WHERE id = %s
    """, (reception['id'],))

    result = cursor.fetchone()
    print(f"   - avance_producteur après draft: {result['avance_producteur']} {'✅ RÉINITIALISÉ' if result['avance_producteur'] == 0 else '❌ NON RÉINITIALISÉ'}")

    # 6. Test avec Transport
    print("\n🚛 Test avec paiement Transport...")

    # Créer une nouvelle écriture pour le transport
    cursor.execute("""
        INSERT INTO account_move
        (name, move_type, state, journal_id, currency_id,
         create_uid, write_uid, create_date, write_date, date)
        VALUES
        ('PAYMENT/TRANSPORT/001', 'entry', 'draft', %s, %s,
         2, 2, NOW(), NOW(), NOW()::DATE)
        RETURNING id
    """, (journal_id, currency_id))

    move_transport_id = cursor.fetchone()['id']

    cursor.execute("""
        INSERT INTO account_payment
        (payment_type, partner_type, amount, move_id,
         reception_id, is_advance_producer, is_advance_transport, is_payment_emballage,
         currency_id, create_uid, write_uid, create_date, write_date)
        VALUES
        ('outbound', 'supplier', 3333.00, %s,
         %s, FALSE, TRUE, FALSE,
         %s, 2, 2, NOW(), NOW())
        RETURNING id
    """, (move_transport_id, reception['id'], currency_id))

    payment_transport_id = cursor.fetchone()['id']

    # Valider
    cursor.execute("""
        UPDATE account_move
        SET state = 'posted'
        WHERE id = %s
    """, (move_transport_id,))
    conn.commit()

    cursor.execute("""
        SELECT transport
        FROM gecafle_reception
        WHERE id = %s
    """, (reception['id'],))

    result = cursor.fetchone()
    print(f"   - transport après validation: {result['transport']} {'✅ SYNCHRONISÉ' if result['transport'] == 3333.00 else '❌ NON SYNCHRONISÉ'}")

    # 7. Test avec Emballage
    print("\n📦 Test avec paiement Emballage...")

    cursor.execute("""
        INSERT INTO account_move
        (name, move_type, state, journal_id, currency_id,
         create_uid, write_uid, create_date, write_date, date)
        VALUES
        ('PAYMENT/EMBALLAGE/001', 'entry', 'posted', %s, %s,
         2, 2, NOW(), NOW(), NOW()::DATE)
        RETURNING id
    """, (journal_id, currency_id))

    move_emballage_id = cursor.fetchone()['id']

    cursor.execute("""
        INSERT INTO account_payment
        (payment_type, partner_type, amount, move_id,
         reception_id, is_advance_producer, is_advance_transport, is_payment_emballage,
         currency_id, create_uid, write_uid, create_date, write_date)
        VALUES
        ('outbound', 'supplier', 5555.00, %s,
         %s, FALSE, FALSE, TRUE,
         %s, 2, 2, NOW(), NOW())
        RETURNING id
    """, (move_emballage_id, reception['id'], currency_id))

    conn.commit()

    cursor.execute("""
        SELECT paiement_emballage
        FROM gecafle_reception
        WHERE id = %s
    """, (reception['id'],))

    result = cursor.fetchone()
    print(f"   - paiement_emballage après création: {result['paiement_emballage']} {'✅ SYNCHRONISÉ' if result['paiement_emballage'] == 5555.00 else '❌ NON SYNCHRONISÉ'}")

    # Nettoyer
    print("\n🧹 Nettoyage des données de test...")
    cursor.execute("DELETE FROM account_payment WHERE id IN (%s, %s, %s)",
                   (payment_id, payment_transport_id, cursor.lastrowid))
    cursor.execute("DELETE FROM account_move WHERE id IN (%s, %s, %s)",
                   (move_id, move_transport_id, move_emballage_id))
    cursor.execute("""
        UPDATE gecafle_reception
        SET avance_producteur = 0, transport = 0, paiement_emballage = 0
        WHERE id = %s
    """, (reception['id'],))
    conn.commit()

    cursor.close()
    conn.close()

    print("\n" + "="*60)
    print("RÉSUMÉ DU TEST")
    print("="*60)
    print("\n⚠️ IMPORTANT:")
    print("   Si la synchronisation ne fonctionne pas:")
    print("   1. Redémarrez Odoo pour charger les modifications")
    print("   2. Mettez à jour le module adi_gecafle_receptions")
    print("   3. Vérifiez les logs Odoo pour les messages [PAYMENT SYNC]")

def main():
    try:
        test_payment_validation()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()