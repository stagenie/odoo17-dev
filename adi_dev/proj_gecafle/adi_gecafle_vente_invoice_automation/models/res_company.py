# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Paramètre principal pour l'automatisation
    auto_post_sales_invoices = fields.Boolean(
        string="Comptabiliser automatiquement les factures de vente",
        default=False,
        help="Si activé, les factures créées depuis les ventes seront automatiquement "
             "comptabilisées. En cas d'erreur, elles seront créées en brouillon."
    )

    # Paramètres additionnels pour la gestion
    invoice_auto_validation_retry = fields.Boolean(
        string="Réessayer en mode brouillon si erreur",
        default=True,
        help="Si la comptabilisation automatique échoue, créer la facture en brouillon"
    )

    invoice_auto_send_email = fields.Boolean(
        string="Envoyer la facture par email après validation",
        default=False,
        help="Envoie automatiquement la facture par email au client après validation"
    )

    invoice_auto_log_errors = fields.Boolean(
        string="Logger les erreurs de comptabilisation",
        default=True,
        help="Enregistre les erreurs de comptabilisation dans le chatter de la vente"
    )
