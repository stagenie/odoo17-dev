# models/vente_inherit.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GecafleVenteInherit(models.Model):
    _inherit = 'gecafle.vente'

    # IMPORTANT : Redéfinir le champ pour le rendre stocké
    consigne_appliquee = fields.Boolean(
        string="Consigne Appliquée",
        compute="_compute_consigne_appliquee",
        store=True,  # AJOUT IMPORTANT : Rendre le champ stocké
        help="Indique si la consigne est appliquée pour ce client"
    )

    @api.depends('client_id', 'client_id.est_fidel')
    def _compute_consigne_appliquee(self):
        for record in self:
            record.consigne_appliquee = not record.client_id.est_fidel if record.client_id else False

    # État de consigne
    etat_consigne = fields.Selection([
        ('non_rendu', 'Non rendu'),
        ('rendu', 'Rendu'),
        ('partiel', 'Partiellement rendu'),
    ], string="État consigne",
        compute='_compute_etat_consigne',
        store=True,
        help="État de retour des emballages consignés")

    # Retours de consigne liés
    consigne_retour_ids = fields.One2many(
        'gecafle.consigne.retour',
        'vente_id',
        string="Retours de consigne"
    )

    consigne_retour_count = fields.Integer(
        string="Retours consigne",
        compute='_compute_consigne_retour_count'
    )

    # Montant de consigne récupéré
    montant_consigne_recupere = fields.Monetary(
        string="Consigne récupérée",
        compute='_compute_montant_consigne_recupere',
        currency_field='currency_id',
        help="Montant total des consignes récupérées"
    )

    @api.depends('consigne_retour_ids.state', 'consigne_appliquee')
    def _compute_etat_consigne(self):
        for vente in self:
            if not vente.consigne_appliquee:
                vente.etat_consigne = False
            else:
                # Vérifier les retours validés
                retours_valides = vente.consigne_retour_ids.filtered(
                    lambda r: r.state in ['valide', 'avoir_cree']
                )

                if not retours_valides:
                    vente.etat_consigne = 'non_rendu'
                else:
                    # Calculer les quantités
                    qte_totale_consignee = sum(vente.detail_emballage_vente_ids.filtered(
                        lambda l: not l.emballage_id.non_returnable
                    ).mapped('qte_sortantes'))

                    qte_totale_retournee = sum(
                        retours_valides.mapped('retour_line_ids.qte_retournee')
                    )

                    if qte_totale_retournee >= qte_totale_consignee:
                        vente.etat_consigne = 'rendu'
                    elif qte_totale_retournee > 0:
                        vente.etat_consigne = 'partiel'
                    else:
                        vente.etat_consigne = 'non_rendu'

    @api.depends('consigne_retour_ids')
    def _compute_consigne_retour_count(self):
        for vente in self:
            vente.consigne_retour_count = len(vente.consigne_retour_ids)

    @api.depends('consigne_retour_ids.montant_a_rembourser', 'consigne_retour_ids.state')
    def _compute_montant_consigne_recupere(self):
        for vente in self:
            retours_valides = vente.consigne_retour_ids.filtered(
                lambda r: r.state in ['valide', 'avoir_cree']
            )
            vente.montant_consigne_recupere = sum(retours_valides.mapped('montant_a_rembourser'))

    def action_create_consigne_retour(self):
        """Crée un retour de consigne pour cette vente"""
        self.ensure_one()

        if self.state != 'valide':
            raise UserError(_("La vente doit être validée pour créer un retour de consigne."))

        if not self.consigne_appliquee:
            raise UserError(_("Cette vente n'a pas de consigne appliquée."))

        if self.etat_consigne == 'rendu':
            raise UserError(_("Tous les emballages ont déjà été retournés."))

        # Créer le retour
        retour = self.env['gecafle.consigne.retour'].create({
            'vente_id': self.id,
            'date': fields.Date.today(),
        })

        # Charger automatiquement les emballages
        retour._onchange_vente_id()

        # Ouvrir le formulaire
        return {
            'name': _('Retour de Consigne'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gecafle.consigne.retour',
            'res_id': retour.id,
            'target': 'current',
        }

    def action_view_consigne_retours(self):
        """Affiche les retours de consigne liés"""
        self.ensure_one()

        if self.consigne_retour_count == 0:
            raise UserError(_("Aucun retour de consigne pour cette vente."))

        if self.consigne_retour_count == 1:
            return {
                'name': _('Retour de Consigne'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'gecafle.consigne.retour',
                'res_id': self.consigne_retour_ids[0].id,
                'target': 'current',
            }
        else:
            return {
                'name': _('Retours de Consigne'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'gecafle.consigne.retour',
                'domain': [('id', 'in', self.consigne_retour_ids.ids)],
                'target': 'current',
            }
