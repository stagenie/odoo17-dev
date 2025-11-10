from odoo import api, fields, models, _
from odoo.exceptions import UserError

class GecafleReception(models.Model):
    _inherit = 'gecafle.reception'

    # Champ pour vérifier si le stock est épuisé
    # NOUVEAU : Champ pour indiquer si la réception a un récap
    has_recap = fields.Boolean(
        string="A un récapitulatif",
        compute="_compute_recap_count",
        store=True,
        help="Indique si cette réception a au moins un récapitulatif"
    )

    def _compute_recap_count(self):
        for record in self:
            count = self.env['gecafle.reception.recap'].search_count([
                ('reception_id', '=', record.id)
            ])
            record.recap_count = count
            record.has_recap = count > 0
    stock_epuise = fields.Boolean(
        string="Stock épuisé",
        compute="_compute_stock_epuise",
        store=True,
        help="Indique si tout le stock de cette réception a été vendu ou destocké"
    )

    # Champ pour vérifier si un récapitulatif existe déjà
    recap_count = fields.Integer(
        string="Récapitulatifs",
        compute="_compute_recap_count"
    )

    recap_ids = fields.One2many(
        'gecafle.reception.recap',
        'reception_id',
        string="Récapitulatifs"
    )

    @api.depends('details_reception_ids.qte_colis_recue',
                 'details_reception_ids.qte_colis_vendus',
                 'details_reception_ids.qte_colis_destockes')
    def _compute_stock_epuise(self):
        for record in self:
            # Vérifier si le stock est épuisé pour toutes les lignes
            stock_epuise = True
            for line in record.details_reception_ids:
                if line.qte_colis_recue != (line.qte_colis_vendus + line.qte_colis_destockes):
                    stock_epuise = False
                    break

            record.stock_epuise = stock_epuise



    def action_create_recap(self):
        """Crée un nouveau récapitulatif de ventes"""
        self.ensure_one()

        # Vérifier si le stock est bien épuisé
        if not self.stock_epuise:
            raise UserError(_("Le stock de cette réception n'est pas entièrement épuisé. "
                              "Vous ne pouvez pas créer de récapitulatif pour le moment."))

        # Créer le récapitulatif
        recap = self.env['gecafle.reception.recap'].create({
            'reception_id': self.id,
        })

        # Générer les lignes
        recap.generate_recap_lines()
        recap.generate_original_lines()
        recap.generate_sale_lines()

        # Ouvrir le formulaire du récapitulatif
        return {
            'name': _('Récapitulatif des ventes'),
            'view_mode': 'form',
            'res_model': 'gecafle.reception.recap',
            'res_id': recap.id,
            'type': 'ir.actions.act_window',
        }

    def action_view_recaps(self):
        """Affiche les récapitulatifs existants"""
        self.ensure_one()

        action = {
            'name': _('Récapitulatifs des ventes'),
            'view_mode': 'form',
            'res_model': 'gecafle.reception.recap',
            'domain': [('reception_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_reception_id': self.id},
        }

        if self.recap_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.recap_ids[0].id,
            })

        return action
