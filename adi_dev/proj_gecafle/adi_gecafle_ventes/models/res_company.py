from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Paramètre existant pour la remise maximale
    remise_max_autorisee = fields.Monetary(
        string="Remise Maximale Autorisée",
        default=5000,
        currency_field="currency_id",
        help="Montant maximal de remise autorisé sur une vente"
    )

    # Nouveau paramètre pour autoriser ou interdire la modification du montant total
    autoriser_modification_prix = fields.Boolean(
        string="Autoriser modification du prix total",
        default=True,
        help="Si coché, permet d'effectuer des remises globale"
    )

    # Paramètres pour les ajustements
    fideles_paient_emballages_non_rendus = fields.Boolean(
        string="Clients fidèles paient emballages non rendus",
        default=True,
        help="Si coché, les clients fidèles doivent payer les emballages non rendus (jetables). "
             "Si décoché, les clients fidèles ne paient aucun emballage."
    )
