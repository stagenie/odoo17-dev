from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuration séquence Vente
    vente_prefix = fields.Char(
        related='company_id.vente_prefix',
        readonly=False,
        string='Préfixe Vente'
    )
    vente_separator = fields.Selection(
        related='company_id.vente_separator',
        readonly=False,
        string='Séparateur Vente'
    )
    vente_year_position = fields.Selection(
        related='company_id.vente_year_position',
        readonly=False,
        string='Position année (Vente)'
    )
    vente_yearly_reset = fields.Boolean(
        related='company_id.vente_yearly_reset',
        readonly=False,
        string='Reset annuel (Vente)'
    )

    # Configuration séquence Réception
    reception_prefix = fields.Char(
        related='company_id.reception_prefix',
        readonly=False,
        string='Préfixe Réception'
    )
    reception_separator = fields.Selection(
        related='company_id.reception_separator',
        readonly=False,
        string='Séparateur Réception'
    )
    reception_year_position = fields.Selection(
        related='company_id.reception_year_position',
        readonly=False,
        string='Position année (Réception)'
    )
    reception_yearly_reset = fields.Boolean(
        related='company_id.reception_yearly_reset',
        readonly=False,
        string='Reset annuel (Réception)'
    )

    # Champs de prévisualisation
    vente_preview = fields.Char(
        string='Aperçu N° Vente',
        compute='_compute_vente_preview'
    )
    reception_preview = fields.Char(
        string='Aperçu N° Réception',
        compute='_compute_reception_preview'
    )

    @api.depends('vente_prefix', 'vente_separator', 'vente_year_position')
    def _compute_vente_preview(self):
        for record in self:
            if record.company_id:
                record.vente_preview = record.company_id.preview_vente_format()
            else:
                record.vente_preview = ''

    @api.depends('reception_prefix', 'reception_separator', 'reception_year_position')
    def _compute_reception_preview(self):
        for record in self:
            if record.company_id:
                record.reception_preview = record.company_id.preview_reception_format()
            else:
                record.reception_preview = ''
