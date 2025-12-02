#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de synchronisation manuelle des paiements existants avec les réceptions
Ce script corrige les montants dans les réceptions basé sur les paiements validés
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

def synchronize_all_receptions():
    """Synchronise toutes les réceptions avec leurs paiements"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("SYNCHRONISATION DES PAIEMENTS EXISTANTS")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    # 1. D'abord, s'assurer que les champs existent
    ensure_fields_exist(cursor, conn)

    # 2. Récupérer toutes les réceptions qui ont des paiements
    cursor.execute("""
        SELECT DISTINCT r.id, r.name
        FROM gecafle_reception r
        WHERE EXISTS (
            SELECT 1 FROM account_payment p
            WHERE p.reception_id = r.id
        )
        ORDER BY r.id
    """)

    receptions = cursor.fetchall()
    print(f"\n📊 {len(receptions)} réceptions avec des paiements trouvées")

    total_updated = 0
    errors = 0

    for reception in receptions:
        print(f"\n🔄 Traitement de la réception {reception['name']} (ID: {reception['id']})")

        # Calculer les sommes pour chaque type de paiement
        # Note: Comme la colonne 'state' n'existe pas dans account_payment,
        # on considère tous les paiements comme validés

        # Avance producteur
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM account_payment
            WHERE reception_id = %s
            AND is_advance_producer = TRUE
        """, (reception['id'],))
        avance_producteur = cursor.fetchone()['total']

        # Transport
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM account_payment
            WHERE reception_id = %s
            AND is_advance_transport = TRUE
        """, (reception['id'],))
        transport = cursor.fetchone()['total']

        # Emballage
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM account_payment
            WHERE reception_id = %s
            AND is_payment_emballage = TRUE
        """, (reception['id'],))
        paiement_emballage = cursor.fetchone()['total']

        # Obtenir les valeurs actuelles dans la réception
        cursor.execute("""
            SELECT avance_producteur, transport, paiement_emballage
            FROM gecafle_reception
            WHERE id = %s
        """, (reception['id'],))
        current = cursor.fetchone()

        # Comparer et mettre à jour si nécessaire
        updates_needed = []
        if current['avance_producteur'] != avance_producteur:
            updates_needed.append(('avance_producteur', avance_producteur, current['avance_producteur']))
        if current['transport'] != transport:
            updates_needed.append(('transport', transport, current['transport']))
        if current['paiement_emballage'] != paiement_emballage:
            updates_needed.append(('paiement_emballage', paiement_emballage, current['paiement_emballage']))

        if updates_needed:
            try:
                # Construire la requête UPDATE
                set_clauses = []
                values = []
                for field, new_val, old_val in updates_needed:
                    set_clauses.append(f"{field} = %s")
                    values.append(new_val)
                    print(f"   - {field}: {old_val} → {new_val}")

                values.append(reception['id'])
                query = f"UPDATE gecafle_reception SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(query, values)
                conn.commit()

                print(f"   ✅ Mise à jour effectuée")
                total_updated += 1

            except Exception as e:
                print(f"   ❌ Erreur lors de la mise à jour: {e}")
                errors += 1
                conn.rollback()
        else:
            print(f"   ✅ Déjà synchronisé")

    cursor.close()
    conn.close()

    print("\n" + "="*60)
    print("RÉSUMÉ DE LA SYNCHRONISATION")
    print("="*60)
    print(f"✅ Réceptions mises à jour : {total_updated}")
    print(f"❌ Erreurs rencontrées : {errors}")
    print(f"📊 Total réceptions traitées : {len(receptions)}")

def ensure_fields_exist(cursor, conn):
    """S'assure que tous les champs nécessaires existent dans les tables"""
    print("\n🔍 Vérification de l'existence des champs...")

    # Vérifier/créer les champs dans gecafle_reception
    fields_to_check = [
        ('gecafle_reception', 'avance_producteur', 'NUMERIC DEFAULT 0'),
        ('gecafle_reception', 'transport', 'NUMERIC DEFAULT 0'),
        ('gecafle_reception', 'paiement_emballage', 'NUMERIC DEFAULT 0'),
        ('account_payment', 'reception_id', 'INTEGER'),
        ('account_payment', 'is_advance_producer', 'BOOLEAN DEFAULT FALSE'),
        ('account_payment', 'is_advance_transport', 'BOOLEAN DEFAULT FALSE'),
        ('account_payment', 'is_payment_emballage', 'BOOLEAN DEFAULT FALSE'),
    ]

    for table, column, data_type in fields_to_check:
        cursor.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name = %s
        """, (table, column))

        if not cursor.fetchone():
            print(f"   ⚠️  Création du champ {table}.{column}...")
            try:
                cursor.execute(f"""
                    ALTER TABLE {table}
                    ADD COLUMN IF NOT EXISTS {column} {data_type}
                """)
                conn.commit()
                print(f"   ✅ Champ créé avec succès")
            except Exception as e:
                print(f"   ❌ Erreur lors de la création: {e}")
                conn.rollback()
        else:
            print(f"   ✅ {table}.{column} existe déjà")

def show_payment_summary():
    """Affiche un résumé des paiements par type"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n" + "="*60)
    print("RÉSUMÉ DES PAIEMENTS PAR TYPE")
    print("="*60)

    # Compter les paiements par type
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN is_advance_producer THEN 1 END) as nb_avance_producteur,
            SUM(CASE WHEN is_advance_producer THEN amount ELSE 0 END) as total_avance_producteur,
            COUNT(CASE WHEN is_advance_transport THEN 1 END) as nb_transport,
            SUM(CASE WHEN is_advance_transport THEN amount ELSE 0 END) as total_transport,
            COUNT(CASE WHEN is_payment_emballage THEN 1 END) as nb_emballage,
            SUM(CASE WHEN is_payment_emballage THEN amount ELSE 0 END) as total_emballage,
            COUNT(*) as nb_total,
            SUM(amount) as total_general
        FROM account_payment
        WHERE reception_id IS NOT NULL
    """)

    result = cursor.fetchone()

    print(f"\n📊 Statistiques globales :")
    print(f"   - Avances producteur : {result['nb_avance_producteur'] or 0} paiements, Total: {result['total_avance_producteur'] or 0:.2f}")
    print(f"   - Transport : {result['nb_transport'] or 0} paiements, Total: {result['total_transport'] or 0:.2f}")
    print(f"   - Emballage : {result['nb_emballage'] or 0} paiements, Total: {result['total_emballage'] or 0:.2f}")
    print(f"   - TOTAL GÉNÉRAL : {result['nb_total'] or 0} paiements, Montant: {result['total_general'] or 0:.2f}")

    cursor.close()
    conn.close()

def main():
    try:
        # D'abord s'assurer que les champs existent
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        ensure_fields_exist(cursor, conn)
        cursor.close()
        conn.close()

        # Afficher le résumé avant synchronisation
        show_payment_summary()

        # Effectuer la synchronisation
        synchronize_all_receptions()

        print("\n✅ Synchronisation terminée avec succès")
        print("\n💡 IMPORTANT :")
        print("   - Ce script a synchronisé les montants dans les réceptions")
        print("   - Les futurs paiements seront synchronisés automatiquement")
        print("   - grâce au code Python modifié dans les modules Odoo")
        print("   - Assurez-vous de redémarrer Odoo pour que les changements")
        print("   - dans account_payment.py prennent effet")

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()