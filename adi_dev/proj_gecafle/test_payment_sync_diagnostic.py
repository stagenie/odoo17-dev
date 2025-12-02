#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour la synchronisation des paiements avec les réceptions
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

# Configuration de la base de données
DB_CONFIG = {
    'host': None,  # Utiliser socket Unix
    'database': 'o17_gecafle_final_base',
    'user': 'stadev',
    'password': 'St@dev',
    'port': 5432
}

def check_table_columns():
    """Vérifier l'existence des colonnes dans la table gecafle_reception"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("VÉRIFICATION DES COLONNES DANS LA TABLE gecafle_reception")
    print("="*60)

    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'gecafle_reception'
        AND column_name IN ('avance_producteur', 'transport', 'paiement_emballage')
        ORDER BY column_name
    """)

    columns = cursor.fetchall()
    if columns:
        print("\nColonnes trouvées :")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
    else:
        print("\n⚠️  AUCUNE des colonnes de synchronisation n'existe dans la table!")

    cursor.close()
    conn.close()
    return {col['column_name'] for col in columns}

def check_recent_payments():
    """Vérifier les paiements récents et leur statut de synchronisation"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("PAIEMENTS RÉCENTS (derniers 20)")
    print("="*60)

    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.state,
            p.amount,
            p.reception_id,
            r.name as reception_name,
            p.is_advance_producer,
            p.is_advance_transport,
            CASE
                WHEN p.is_advance_producer THEN 'Avance Producteur'
                WHEN p.is_advance_transport THEN 'Transport'
                ELSE 'Standard/Emballage'
            END as type_paiement,
            p.create_date,
            p.write_date
        FROM account_payment p
        LEFT JOIN gecafle_reception r ON p.reception_id = r.id
        WHERE p.reception_id IS NOT NULL
        ORDER BY p.create_date DESC
        LIMIT 20
    """)

    payments = cursor.fetchall()

    if payments:
        print(f"\n{len(payments)} paiements trouvés avec une réception liée:")
        for payment in payments:
            print(f"\n  Paiement #{payment['id']} - {payment['name']}:")
            print(f"    - Réception: {payment['reception_name']} (ID: {payment['reception_id']})")
            print(f"    - Type: {payment['type_paiement']}")
            print(f"    - État: {payment['state']}")
            print(f"    - Montant: {payment['amount']}")
            print(f"    - Créé le: {payment['create_date']}")
            print(f"    - Modifié le: {payment['write_date']}")
    else:
        print("\n⚠️  Aucun paiement lié à une réception trouvé")

    cursor.close()
    conn.close()
    return payments

def check_reception_values(existing_columns):
    """Vérifier les valeurs actuelles dans les réceptions"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("VALEURS ACTUELLES DANS LES RÉCEPTIONS")
    print("="*60)

    # Construire la requête dynamique basée sur les colonnes existantes
    select_fields = ['r.id', 'r.name', 'r.state']

    if 'avance_producteur' in existing_columns:
        select_fields.append('r.avance_producteur')
    else:
        select_fields.append("0 as avance_producteur")

    if 'transport' in existing_columns:
        select_fields.append('r.transport')
    else:
        select_fields.append("0 as transport")

    if 'paiement_emballage' in existing_columns:
        select_fields.append('r.paiement_emballage')
    else:
        select_fields.append("0 as paiement_emballage")

    query = f"""
        SELECT
            {', '.join(select_fields)},
            (SELECT COUNT(*) FROM account_payment WHERE reception_id = r.id) as nb_paiements,
            (SELECT SUM(amount) FROM account_payment WHERE reception_id = r.id AND state = 'posted' AND is_advance_producer = true) as total_avance_posted,
            (SELECT SUM(amount) FROM account_payment WHERE reception_id = r.id AND state = 'posted' AND is_advance_transport = true) as total_transport_posted
        FROM gecafle_reception r
        WHERE EXISTS (SELECT 1 FROM account_payment WHERE reception_id = r.id)
        ORDER BY r.create_date DESC
        LIMIT 10
    """

    cursor.execute(query)
    receptions = cursor.fetchall()

    if receptions:
        print(f"\n{len(receptions)} réceptions avec des paiements:")
        for rec in receptions:
            print(f"\n  Réception {rec['name']} (ID: {rec['id']}):")
            print(f"    - État: {rec['state']}")
            print(f"    - Avance producteur (champ): {rec['avance_producteur']}")
            print(f"    - Transport (champ): {rec['transport']}")
            print(f"    - Paiement emballage (champ): {rec['paiement_emballage']}")
            print(f"    - Nombre de paiements: {rec['nb_paiements']}")
            print(f"    - Total avances posted: {rec['total_avance_posted'] or 0}")
            print(f"    - Total transport posted: {rec['total_transport_posted'] or 0}")

            # Vérifier la cohérence
            if rec['total_avance_posted'] and rec['avance_producteur'] != rec['total_avance_posted']:
                print(f"    ⚠️  INCOHÉRENCE: Avance producteur devrait être {rec['total_avance_posted']}")
            if rec['total_transport_posted'] and rec['transport'] != rec['total_transport_posted']:
                print(f"    ⚠️  INCOHÉRENCE: Transport devrait être {rec['total_transport_posted']}")

    cursor.close()
    conn.close()

def check_emballage_field():
    """Vérifier spécifiquement le champ is_payment_emballage"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("VÉRIFICATION DU CHAMP is_payment_emballage")
    print("="*60)

    # Vérifier si la colonne existe
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'account_payment'
        AND column_name = 'is_payment_emballage'
    """)

    if cursor.fetchone():
        print("\n✅ Le champ is_payment_emballage existe dans account_payment")

        # Compter les paiements emballage
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM account_payment
            WHERE is_payment_emballage = true
        """)
        count = cursor.fetchone()['count']
        print(f"   - Nombre de paiements emballage: {count}")
    else:
        print("\n⚠️  Le champ is_payment_emballage N'EXISTE PAS dans account_payment")

    cursor.close()
    conn.close()

def main():
    print("\n" + "="*60)
    print("DIAGNOSTIC DE LA SYNCHRONISATION DES PAIEMENTS")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    try:
        # 1. Vérifier les colonnes
        existing_columns = check_table_columns()

        # 2. Vérifier le champ emballage
        check_emballage_field()

        # 3. Vérifier les paiements récents
        check_recent_payments()

        # 4. Vérifier les valeurs dans les réceptions
        check_reception_values(existing_columns)

        print("\n" + "="*60)
        print("DIAGNOSTIC TERMINÉ")
        print("="*60)

        if not existing_columns:
            print("\n⚠️  PROBLÈME CRITIQUE: Les colonnes de synchronisation n'existent pas dans la table!")
            print("    Les modules étendus ne semblent pas avoir créé leurs champs correctement.")
            print("    Vérifiez que les modules sont bien installés et à jour.")

    except Exception as e:
        print(f"\n❌ ERREUR lors du diagnostic: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()