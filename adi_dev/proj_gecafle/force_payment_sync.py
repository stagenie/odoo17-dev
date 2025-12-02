#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de synchronisation FORCÉE des paiements
Synchronise en se basant sur account_move.state (Odoo 17)
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

def force_sync_all_payments():
    """Force la synchronisation de TOUS les paiements avec leurs réceptions"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("SYNCHRONISATION FORCÉE DES PAIEMENTS")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    # 1. D'abord, réinitialiser TOUS les champs à 0
    print("\n🔄 Étape 1: Réinitialisation de tous les montants...")
    cursor.execute("""
        UPDATE gecafle_reception
        SET avance_producteur = 0,
            transport = 0,
            paiement_emballage = 0
        WHERE id IN (
            SELECT DISTINCT reception_id
            FROM account_payment
            WHERE reception_id IS NOT NULL
        )
    """)
    updated_count = cursor.rowcount
    conn.commit()
    print(f"   ✅ {updated_count} réceptions réinitialisées")

    # 2. Récupérer tous les paiements avec leur état depuis account_move
    print("\n🔍 Étape 2: Analyse des paiements...")
    cursor.execute("""
        SELECT
            p.id as payment_id,
            p.reception_id,
            p.amount,
            p.is_advance_producer,
            p.is_advance_transport,
            p.is_payment_emballage,
            m.state as move_state,
            m.name as move_name,
            r.name as reception_name
        FROM account_payment p
        INNER JOIN account_move m ON p.move_id = m.id
        INNER JOIN gecafle_reception r ON p.reception_id = r.id
        WHERE p.reception_id IS NOT NULL
        ORDER BY p.reception_id, p.id
    """)

    payments = cursor.fetchall()
    print(f"   📊 {len(payments)} paiements trouvés")

    # 3. Grouper les paiements par réception et type
    reception_totals = {}
    for payment in payments:
        reception_id = payment['reception_id']
        if reception_id not in reception_totals:
            reception_totals[reception_id] = {
                'name': payment['reception_name'],
                'avance_producteur': 0,
                'transport': 0,
                'paiement_emballage': 0,
                'details': []
            }

        # Si l'écriture comptable est validée (posted)
        if payment['move_state'] == 'posted':
            amount = payment['amount'] or 0

            # Déterminer le type et additionner
            if payment['is_advance_producer']:
                reception_totals[reception_id]['avance_producteur'] += amount
                payment_type = 'Avance Producteur'
            elif payment['is_advance_transport']:
                reception_totals[reception_id]['transport'] += amount
                payment_type = 'Transport'
            elif payment['is_payment_emballage']:
                reception_totals[reception_id]['paiement_emballage'] += amount
                payment_type = 'Emballage'
            else:
                payment_type = 'Non typé'

            reception_totals[reception_id]['details'].append({
                'id': payment['payment_id'],
                'amount': amount,
                'type': payment_type,
                'move': payment['move_name']
            })

    # 4. Mettre à jour chaque réception
    print("\n💾 Étape 3: Mise à jour des réceptions...")
    success_count = 0
    error_count = 0

    for reception_id, totals in reception_totals.items():
        try:
            print(f"\n   📋 Réception {totals['name']} (ID: {reception_id}):")

            # Afficher les détails
            for detail in totals['details']:
                print(f"      - Paiement #{detail['id']}: {detail['type']} = {detail['amount']:.2f} ({detail['move']})")

            # Faire l'UPDATE SQL
            cursor.execute("""
                UPDATE gecafle_reception
                SET avance_producteur = %s,
                    transport = %s,
                    paiement_emballage = %s,
                    write_date = NOW()
                WHERE id = %s
            """, (
                totals['avance_producteur'],
                totals['transport'],
                totals['paiement_emballage'],
                reception_id
            ))

            conn.commit()

            print(f"      ✅ Totaux synchronisés:")
            print(f"         - Avance Producteur: {totals['avance_producteur']:.2f}")
            print(f"         - Transport: {totals['transport']:.2f}")
            print(f"         - Paiement Emballage: {totals['paiement_emballage']:.2f}")

            success_count += 1

        except Exception as e:
            print(f"      ❌ Erreur: {e}")
            error_count += 1
            conn.rollback()

    # 5. Vérification finale
    print("\n✅ Étape 4: Vérification finale...")
    cursor.execute("""
        SELECT
            COUNT(*) as nb_receptions,
            SUM(avance_producteur) as total_avance,
            SUM(transport) as total_transport,
            SUM(paiement_emballage) as total_emballage
        FROM gecafle_reception
        WHERE avance_producteur > 0
           OR transport > 0
           OR paiement_emballage > 0
    """)

    stats = cursor.fetchone()

    print(f"\n📊 STATISTIQUES FINALES:")
    print(f"   - Réceptions avec paiements: {stats['nb_receptions'] or 0}")
    print(f"   - Total Avances Producteur: {stats['total_avance'] or 0:.2f}")
    print(f"   - Total Transport: {stats['total_transport'] or 0:.2f}")
    print(f"   - Total Emballages: {stats['total_emballage'] or 0:.2f}")

    cursor.close()
    conn.close()

    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    print(f"✅ Réceptions synchronisées avec succès: {success_count}")
    print(f"❌ Erreurs rencontrées: {error_count}")
    print(f"📊 Total de paiements traités: {len(payments)}")

def verify_sync():
    """Vérifie les incohérences après synchronisation"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("VÉRIFICATION DES INCOHÉRENCES")
    print("="*60)

    # Vérifier les incohérences
    cursor.execute("""
        SELECT
            r.id,
            r.name,
            r.avance_producteur as reception_avance,
            r.transport as reception_transport,
            r.paiement_emballage as reception_emballage,
            COALESCE(SUM(CASE WHEN p.is_advance_producer AND m.state = 'posted' THEN p.amount ELSE 0 END), 0) as calc_avance,
            COALESCE(SUM(CASE WHEN p.is_advance_transport AND m.state = 'posted' THEN p.amount ELSE 0 END), 0) as calc_transport,
            COALESCE(SUM(CASE WHEN p.is_payment_emballage AND m.state = 'posted' THEN p.amount ELSE 0 END), 0) as calc_emballage
        FROM gecafle_reception r
        LEFT JOIN account_payment p ON p.reception_id = r.id
        LEFT JOIN account_move m ON p.move_id = m.id
        WHERE r.id IN (
            SELECT DISTINCT reception_id
            FROM account_payment
            WHERE reception_id IS NOT NULL
        )
        GROUP BY r.id, r.name, r.avance_producteur, r.transport, r.paiement_emballage
        HAVING r.avance_producteur != COALESCE(SUM(CASE WHEN p.is_advance_producer AND m.state = 'posted' THEN p.amount ELSE 0 END), 0)
            OR r.transport != COALESCE(SUM(CASE WHEN p.is_advance_transport AND m.state = 'posted' THEN p.amount ELSE 0 END), 0)
            OR r.paiement_emballage != COALESCE(SUM(CASE WHEN p.is_payment_emballage AND m.state = 'posted' THEN p.amount ELSE 0 END), 0)
    """)

    inconsistencies = cursor.fetchall()

    if inconsistencies:
        print("\n⚠️ INCOHÉRENCES DÉTECTÉES:")
        for inc in inconsistencies:
            print(f"\n   Réception {inc['name']} (ID: {inc['id']}):")
            if inc['reception_avance'] != inc['calc_avance']:
                print(f"      - Avance: {inc['reception_avance']} (devrait être {inc['calc_avance']})")
            if inc['reception_transport'] != inc['calc_transport']:
                print(f"      - Transport: {inc['reception_transport']} (devrait être {inc['calc_transport']})")
            if inc['reception_emballage'] != inc['calc_emballage']:
                print(f"      - Emballage: {inc['reception_emballage']} (devrait être {inc['calc_emballage']})")
    else:
        print("\n✅ Aucune incohérence détectée - Toutes les réceptions sont synchronisées!")

    cursor.close()
    conn.close()

def main():
    try:
        # Forcer la synchronisation
        force_sync_all_payments()

        # Vérifier les incohérences
        verify_sync()

        print("\n" + "="*60)
        print("💡 PROCHAINES ÉTAPES")
        print("="*60)
        print("\n1. Les montants ont été synchronisés directement en base")
        print("2. Pour que les changements futurs soient automatiques :")
        print("   - Redémarrer Odoo avec mise à jour des modules :")
        print("     ./odoo-bin -c odoo17.conf -d o17_gecafle_final_base \\")
        print("       -u adi_gecafle_receptions,adi_gecafle_reception_extended")
        print("\n3. Vérifier les logs pour [PAYMENT SYNC] lors des prochains paiements")

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()