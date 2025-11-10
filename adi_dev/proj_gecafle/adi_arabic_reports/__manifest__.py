# -*- coding: utf-8 -*-
{
    'name': 'ADI Rapports en Arabe',
    'version': '17.0.1.0.0',
    'category': 'Localization',
    'summary': 'Traduction en arabe des rapports GECAFLE',
    'description': """
        Module de traduction en arabe des rapports GECAFLE
        ===================================================

        Rapports traduits :
        - وصل البيع (Bon de Vente)
        - وصل الاستلام (Bon de Réception)
        - كشف إجمالي المبيعات (Bordereau Récapitulatif)
        - تفاصيل المبيعات (Détails des Ventes)
        - فاتورة المورد (Facture Fournisseur)
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'email': 'info@adicops.com',
    'depends': [
        'adi_gecafle_ventes',
        'adi_gecafle_receptions',
        'adi_gecafle_vente_invoices',  # Si ce module existe
        'account',
    ],
    'data': [
         'reports/report_bon_vente_ar.xml',
        'reports/report_bon_reception_ar.xml',
        'reports/report_recap_ventes_ar.xml',
        'reports/report_recap_ventes_commission_ar.xml',
        'reports/report_ventes_details_ar.xml',
        'reports/report_ventes_details_commission_ar.xml',
        'reports/report_invoice_supplier_ar.xml',
        'reports/report_bon_pese_ar.xml',
        'reports/report_avoir_client_ar.xml',
        'reports/report_avoir_producteur_ar.xml',
        'views/vente_smartbuttons.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
