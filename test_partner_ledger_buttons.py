#!/usr/bin/env python3
"""
Script de validation des boutons Partner Ledger ajoutés au module adi_gecafle_sync_partners
Ce script vérifie la structure des méthodes sans avoir besoin d'une installation Odoo complète
"""

import re
import sys
from pathlib import Path

def check_method_exists(file_path, method_name):
    """Vérifie qu'une méthode existe dans un fichier Python"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = rf'def {method_name}\(self.*?\):'
    if re.search(pattern, content):
        return True
    return False

def check_method_structure(file_path, method_name, expected_model):
    """Vérifie la structure de la méthode action_view_partner_ledger"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        'method_exists': False,
        'has_ensure_one': False,
        'returns_dict': False,
        'has_correct_model': False,
        'has_wizard_view': False,
        'has_context': False,
        'has_partner_ids': False,
    }

    # Extraire la méthode
    pattern = rf'def {method_name}\(self.*?\):.*?(?=\n    def |\nclass |\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        method_content = match.group(0)
        checks['method_exists'] = True

        # Vérifications
        if 'self.ensure_one()' in method_content:
            checks['has_ensure_one'] = True

        if 'return {' in method_content:
            checks['returns_dict'] = True

        if f"'res_model': '{expected_model}'" in method_content:
            checks['has_correct_model'] = True

        if 'accounting_pdf_reports.account_report_partner_ledger_view' in method_content:
            checks['has_wizard_view'] = True

        if "'context':" in method_content:
            checks['has_context'] = True

        if 'default_partner_ids' in method_content:
            checks['has_partner_ids'] = True

    return checks

def check_xml_button(file_path, button_name):
    """Vérifie qu'un bouton existe dans un fichier XML"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        'button_exists': False,
        'has_correct_action': False,
        'has_icon': False,
        'has_groups': False,
        'has_stat_info': False,
    }

    # Chercher le bouton
    pattern = rf'<button[^>]*name="{button_name}".*?</button>'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        button_content = match.group(0)
        checks['button_exists'] = True

        if 'type="object"' in button_content:
            checks['has_correct_action'] = True

        if 'icon="fa-book"' in button_content:
            checks['has_icon'] = True

        if 'groups="account.group_account_invoice"' in button_content:
            checks['has_groups'] = True

        if 'o_stat_info' in button_content:
            checks['has_stat_info'] = True

    return checks

def print_results(title, checks):
    """Affiche les résultats des vérifications"""
    print(f"\n{title}")
    print("=" * len(title))
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check.replace('_', ' ').title()}")
        if not passed:
            all_passed = False
    return all_passed

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print(" VALIDATION DES BOUTONS PARTNER LEDGER")
    print("="*70)

    base_path = Path('/home/user/odoo17-dev/adi_dev/proj_gecafle/adi_gecafle_sync_partners')
    all_tests_passed = True

    # Test 1: res.partner
    print("\n[1/6] Vérification de res.partner (res_partner.py)")
    res_partner_file = base_path / 'models' / 'res_partner.py'
    if res_partner_file.exists():
        checks = check_method_structure(
            res_partner_file,
            'action_view_partner_ledger',
            'account.report.partner.ledger'
        )
        if not print_results("Méthode action_view_partner_ledger dans res.partner", checks):
            all_tests_passed = False
    else:
        print("  ✗ Fichier non trouvé")
        all_tests_passed = False

    # Test 2: gecafle.client
    print("\n[2/6] Vérification de gecafle.client (gecafle_client.py)")
    client_file = base_path / 'models' / 'gecafle_client.py'
    if client_file.exists():
        checks = check_method_structure(
            client_file,
            'action_view_partner_ledger',
            'account.report.partner.ledger'
        )
        if not print_results("Méthode action_view_partner_ledger dans gecafle.client", checks):
            all_tests_passed = False
    else:
        print("  ✗ Fichier non trouvé")
        all_tests_passed = False

    # Test 3: gecafle.producteur
    print("\n[3/6] Vérification de gecafle.producteur (gecafle_producteur.py)")
    producteur_file = base_path / 'models' / 'gecafle_producteur.py'
    if producteur_file.exists():
        checks = check_method_structure(
            producteur_file,
            'action_view_partner_ledger',
            'account.report.partner.ledger'
        )
        if not print_results("Méthode action_view_partner_ledger dans gecafle.producteur", checks):
            all_tests_passed = False
    else:
        print("  ✗ Fichier non trouvé")
        all_tests_passed = False

    # Test 4: Vue res.partner
    print("\n[4/6] Vérification du bouton dans res_partner_views.xml")
    res_partner_view = base_path / 'views' / 'res_partner_views.xml'
    if res_partner_view.exists():
        checks = check_xml_button(res_partner_view, 'action_view_partner_ledger')
        if not print_results("Bouton Partner Ledger dans res.partner", checks):
            all_tests_passed = False
    else:
        print("  ✗ Fichier non trouvé")
        all_tests_passed = False

    # Test 5: Vue gecafle.client
    print("\n[5/6] Vérification du bouton dans gecafle_client_views.xml")
    client_view = base_path / 'views' / 'gecafle_client_views.xml'
    if client_view.exists():
        checks = check_xml_button(client_view, 'action_view_partner_ledger')
        if not print_results("Bouton Partner Ledger dans gecafle.client", checks):
            all_tests_passed = False
    else:
        print("  ✗ Fichier non trouvé")
        all_tests_passed = False

    # Test 6: Vue gecafle.producteur
    print("\n[6/6] Vérification du bouton dans gecafle_producteur_views.xml")
    producteur_view = base_path / 'views' / 'gecafle_producteur_views.xml'
    if producteur_view.exists():
        checks = check_xml_button(producteur_view, 'action_view_partner_ledger')
        if not print_results("Bouton Partner Ledger dans gecafle.producteur", checks):
            all_tests_passed = False
    else:
        print("  ✗ Fichier non trouvé")
        all_tests_passed = False

    # Résultat final
    print("\n" + "="*70)
    if all_tests_passed:
        print("✓ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS")
        print("="*70)
        print("\nLe module est prêt pour le déploiement!")
        print("\nProchaines étapes:")
        print("  1. Mettre à jour le module dans Odoo:")
        print("     - Aller dans Apps > adi_gecafle_sync_partners")
        print("     - Cliquer sur 'Upgrade'")
        print("  2. Tester manuellement:")
        print("     - Ouvrir un contact (res.partner)")
        print("     - Vérifier la présence du bouton 'Partner Ledger'")
        print("     - Cliquer et vérifier que le wizard s'ouvre")
        print("     - Répéter pour gecafle.client et gecafle.producteur")
        return 0
    else:
        print("✗ CERTAINS TESTS ONT ÉCHOUÉ")
        print("="*70)
        print("\nVeuillez vérifier les erreurs ci-dessus.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
