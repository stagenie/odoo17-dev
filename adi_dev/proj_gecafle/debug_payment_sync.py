#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de débogage approfondi pour la synchronisation des paiements
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

def check_python_fields():
    """Vérifier si les champs sont définis dans les modèles Python d'Odoo"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES CHAMPS DANS LES MODÈLES PYTHON")
    print("="*60)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Vérifier dans ir_model_fields (métadonnées Odoo)
    cursor.execute("""
        SELECT
            imf.name as field_name,
            imf.model,
            imf.ttype as field_type,
            imf.readonly,
            imf.store,
            imf.compute,
            imf.state
        FROM ir_model_fields imf
        WHERE imf.model IN ('gecafle.reception', 'account.payment')
        AND imf.name IN (
            'avance_producteur', 'transport', 'paiement_emballage',
            'reception_id', 'is_advance_producer', 'is_advance_transport', 'is_payment_emballage'
        )
        ORDER BY imf.model, imf.name
    """)

    fields = cursor.fetchall()
    if fields:
        print("\n📋 Champs trouvés dans les métadonnées Odoo:")
        for field in fields:
            print(f"\n  {field['model']}.{field['field_name']}:")
            print(f"    - Type: {field['field_type']}")
            print(f"    - ReadOnly: {field['readonly']}")
            print(f"    - Store: {field['store']}")
            print(f"    - Compute: {field['compute']}")
            print(f"    - State: {field['state']}")
    else:
        print("\n⚠️ AUCUN champ trouvé dans les métadonnées Odoo!")
        print("    Les modules ne sont peut-être pas correctement installés/mis à jour")

    cursor.close()
    conn.close()

def check_database_structure():
    """Vérifier la structure complète de la base de données"""
    print("\n" + "="*60)
    print("STRUCTURE DE LA BASE DE DONNÉES")
    print("="*60)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Vérifier les colonnes de gecafle_reception
    print("\n📊 Table gecafle_reception:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'gecafle_reception'
        AND column_name IN ('avance_producteur', 'transport', 'paiement_emballage')
        ORDER BY column_name
    """)

    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']}, default: {col['column_default']})")

    # Vérifier les colonnes de account_payment
    print("\n📊 Table account_payment:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'account_payment'
        AND column_name IN ('reception_id', 'is_advance_producer', 'is_advance_transport', 'is_payment_emballage')
        ORDER BY column_name
    """)

    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']}, default: {col['column_default']})")

    cursor.close()
    conn.close()

def test_manual_update():
    """Tester une mise à jour manuelle pour vérifier les triggers/contraintes"""
    print("\n" + "="*60)
    print("TEST DE MISE À JOUR MANUELLE")
    print("="*60)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Trouver une réception de test
    cursor.execute("""
        SELECT id, name, avance_producteur, transport, paiement_emballage
        FROM gecafle_reception
        WHERE name LIKE '%TEST%' OR name LIKE '%test%'
        ORDER BY id DESC
        LIMIT 1
    """)

    reception = cursor.fetchone()
    if reception:
        print(f"\n🧪 Réception de test trouvée: {reception['name']} (ID: {reception['id']})")
        print(f"   Valeurs actuelles:")
        print(f"   - avance_producteur: {reception['avance_producteur']}")
        print(f"   - transport: {reception['transport']}")
        print(f"   - paiement_emballage: {reception['paiement_emballage']}")

        # Essayer une mise à jour directe
        try:
            test_value = 9999.99
            cursor.execute("""
                UPDATE gecafle_reception
                SET avance_producteur = %s,
                    transport = %s,
                    paiement_emballage = %s
                WHERE id = %s
            """, (test_value, test_value, test_value, reception['id']))

            conn.commit()

            # Vérifier si la mise à jour a fonctionné
            cursor.execute("""
                SELECT avance_producteur, transport, paiement_emballage
                FROM gecafle_reception
                WHERE id = %s
            """, (reception['id'],))

            updated = cursor.fetchone()
            print(f"\n   ✅ Mise à jour SQL directe réussie:")
            print(f"   - avance_producteur: {updated['avance_producteur']}")
            print(f"   - transport: {updated['transport']}")
            print(f"   - paiement_emballage: {updated['paiement_emballage']}")

            # Remettre à zéro
            cursor.execute("""
                UPDATE gecafle_reception
                SET avance_producteur = 0,
                    transport = 0,
                    paiement_emballage = 0
                WHERE id = %s
            """, (reception['id'],))
            conn.commit()
            print(f"\n   📝 Valeurs remises à zéro")

        except Exception as e:
            print(f"\n   ❌ Erreur lors de la mise à jour: {e}")
            conn.rollback()
    else:
        print("\n⚠️ Aucune réception de test trouvée")
        print("   Créez une réception avec 'TEST' dans le nom pour ce test")

    cursor.close()
    conn.close()

def check_payment_state():
    """Vérifier comment l'état des paiements est géré"""
    print("\n" + "="*60)
    print("ANALYSE DE L'ÉTAT DES PAIEMENTS")
    print("="*60)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Vérifier si la colonne state existe dans account_payment
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'account_payment'
        AND column_name = 'state'
    """)

    if cursor.fetchone():
        print("\n✅ La colonne 'state' existe dans account_payment")
    else:
        print("\n⚠️ La colonne 'state' N'EXISTE PAS dans account_payment")
        print("   Cela pourrait être le problème principal!")

        # Vérifier dans account_move à la place
        print("\n🔍 Vérification dans account_move (écriture comptable):")
        cursor.execute("""
            SELECT
                p.id as payment_id,
                p.amount,
                m.state as move_state,
                m.name as move_name,
                p.reception_id,
                p.is_advance_producer,
                p.is_advance_transport,
                p.is_payment_emballage
            FROM account_payment p
            INNER JOIN account_move m ON p.move_id = m.id
            WHERE p.reception_id IS NOT NULL
            ORDER BY p.id DESC
            LIMIT 5
        """)

        payments = cursor.fetchall()
        if payments:
            print(f"\n   {len(payments)} paiements récents avec leur état comptable:")
            for p in payments:
                print(f"\n   Payment #{p['payment_id']}:")
                print(f"     - Montant: {p['amount']}")
                print(f"     - État comptable: {p['move_state']}")
                print(f"     - Réception: {p['reception_id']}")
                print(f"     - Avance producteur: {p['is_advance_producer']}")
                print(f"     - Transport: {p['is_advance_transport']}")
                print(f"     - Emballage: {p['is_payment_emballage']}")

    cursor.close()
    conn.close()

def check_module_status():
    """Vérifier le statut des modules"""
    print("\n" + "="*60)
    print("STATUT DES MODULES ODOO")
    print("="*60)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT
            name,
            state,
            latest_version,
            published_version,
            installed_version
        FROM ir_module_module
        WHERE name LIKE '%gecafle%reception%'
        ORDER BY name
    """)

    modules = cursor.fetchall()
    if modules:
        print("\n📦 Modules trouvés:")
        for mod in modules:
            status = "✅" if mod['state'] == 'installed' else "❌"
            print(f"\n  {status} {mod['name']}:")
            print(f"     - État: {mod['state']}")
            print(f"     - Version installée: {mod['installed_version']}")
            print(f"     - Dernière version: {mod['latest_version']}")

            if mod['state'] != 'installed':
                print(f"     ⚠️ CE MODULE N'EST PAS INSTALLÉ!")
    else:
        print("\n⚠️ Aucun module gecafle reception trouvé!")

    cursor.close()
    conn.close()

def suggest_fixes():
    """Suggérer des corrections basées sur l'analyse"""
    print("\n" + "="*60)
    print("SUGGESTIONS DE CORRECTION")
    print("="*60)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    problems = []

    # Vérifier si les champs existent
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM information_schema.columns
        WHERE table_name = 'account_payment'
        AND column_name = 'state'
    """)

    if cursor.fetchone()['count'] == 0:
        problems.append({
            'issue': "La colonne 'state' n'existe pas dans account_payment",
            'fix': "Le code de synchronisation doit utiliser account_move.state au lieu de account_payment.state",
            'action': "Modifier le code pour joindre account_move et vérifier move.state"
        })

    # Vérifier les modules
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM ir_module_module
        WHERE name IN ('adi_gecafle_receptions', 'adi_gecafle_reception_extended')
        AND state != 'installed'
    """)

    if cursor.fetchone()['count'] > 0:
        problems.append({
            'issue': "Des modules ne sont pas installés/activés",
            'fix': "Installer et mettre à jour les modules",
            'action': "Dans Odoo: Applications > Rechercher les modules > Installer/Mettre à jour"
        })

    if problems:
        print("\n❌ PROBLÈMES DÉTECTÉS:")
        for i, p in enumerate(problems, 1):
            print(f"\n{i}. {p['issue']}")
            print(f"   Solution: {p['fix']}")
            print(f"   Action: {p['action']}")
    else:
        print("\n✅ Aucun problème structurel détecté")
        print("\n📝 Vérifiez que :")
        print("   1. Odoo a été redémarré après les modifications")
        print("   2. Les modules ont été mis à jour dans l'interface")
        print("   3. Les logs ne contiennent pas d'erreurs Python")

    cursor.close()
    conn.close()

def main():
    print("\n" + "="*60)
    print("🔍 DIAGNOSTIC APPROFONDI DE LA SYNCHRONISATION")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    try:
        # 1. Vérifier les champs Python
        check_python_fields()

        # 2. Vérifier la structure de la base
        check_database_structure()

        # 3. Vérifier l'état des paiements
        check_payment_state()

        # 4. Vérifier le statut des modules
        check_module_status()

        # 5. Test de mise à jour manuelle
        test_manual_update()

        # 6. Suggestions de correction
        suggest_fixes()

        print("\n" + "="*60)
        print("DIAGNOSTIC TERMINÉ")
        print("="*60)

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()