from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GecafleDestockageWizard(models.TransientModel):
    _name = 'gecafle.destockage.wizard'
    _description = 'Wizard Destockage'

    stock_id = fields.Many2one(
        'gecafle.stock',
        string="Ligne de Stock",
        required=True
    )
    reception_date = fields.Datetime(
        string="Date de réception",
        related='stock_id.reception_date',
        readonly=True
    )
    reception_id = fields.Many2one(
        string="N° de réception",
        related='stock_id.reception_id',
        readonly=True
    )
    producteur_id = fields.Many2one(
        string="Producteur",
        related='stock_id.producteur_id',
        readonly=True
    )
    designation_id = fields.Many2one(
        string="Produit",
        related='stock_id.designation_id',
        readonly=True
    )
    emballage_id = fields.Many2one(
        string="Emballage",
        related='stock_id.emballage_id',
        readonly=True
    )
    qualite_id = fields.Many2one(
        string="Qualité",
        related='stock_id.qualite_id',
        readonly=True
    )

    destockage_date = fields.Datetime(
        string="Date de Destockage",
        default=fields.Datetime.now,
        required=True
    )
    qte_disponible = fields.Integer(
        string="Quantité Disponible",
        related='stock_id.qte_disponible',
        readonly=True
    )
    qte_destockee = fields.Integer(
        string="Quantité Destockée",
        required=True,
        default=1
    )
    observation = fields.Text(string="Observation", required=True)

    # Champ calculé pour trouver la ligne de réception correspondante
    detail_reception_id = fields.Many2one(
        'gecafle.details_reception',
        string="Ligne de Réception",
        compute="_compute_detail_reception"
    )

    @api.depends('stock_id')
    def _compute_detail_reception(self):
        """Récupère la ligne de réception associée à cette ligne de stock"""
        for wizard in self:
            # Recherche des lignes de réception correspondant aux critères
            domain = [
                ('reception_id', '=', wizard.reception_id.id),
                ('designation_id', '=', wizard.designation_id.id),
            ]

            if wizard.qualite_id:
                domain.append(('qualite_id', '=', wizard.qualite_id.id))

            if wizard.emballage_id:
                domain.append(('type_colis_id', '=', wizard.emballage_id.id))

            matching_lines = self.env['gecafle.details_reception'].search(domain)

            # Si plusieurs lignes correspondent, prendre celle avec le plus de quantité disponible
            if matching_lines:
                wizard.detail_reception_id = matching_lines.sorted(
                    key=lambda r: r.qte_colis_disponibles, reverse=True
                )[0].id
            else:
                wizard.detail_reception_id = False

    def action_destock(self):
        # Vérifier que la quantité à destocker ne dépasse pas la quantité disponible
        if self.qte_destockee <= 0:
            raise ValidationError(_("La quantité destockée doit être supérieure à 0"))

        # Vérifier que la quantité à destocker ne dépasse pas la quantité disponible
        if self.qte_destockee > self.stock_id.qte_disponible:
            raise ValidationError(_("La quantité destockée ne peut être supérieure à la quantité disponible!"))

        # Vérifier que la ligne de réception a été trouvée
        if not self.detail_reception_id:
            raise ValidationError(_("Impossible de trouver la ligne de réception correspondante pour ce destockage."))

        # Vérifier que la ligne de réception a suffisamment de quantité disponible
        if self.detail_reception_id.qte_colis_disponibles < self.qte_destockee:
            raise ValidationError(_(
                "La quantité disponible dans la ligne de réception (%s) est insuffisante pour ce destockage (%s)."
            ) % (self.detail_reception_id.qte_colis_disponibles, self.qte_destockee))

        # Créer un enregistrement de destockage
        self.env['gecafle.destockage'].with_context(force_stock=True).create({
            'stock_id': self.stock_id.id,
            'detail_reception_id': self.detail_reception_id.id,
            'qte_disponible': self.qte_disponible,
            'qte_destockee': self.qte_destockee,
            'destockage_date': self.destockage_date,
            'observation': self.observation,
        })

        # Mettre à jour la quantité disponible du stock
        self.stock_id.with_context(force_stock=True).write({
            'qte_disponible': self.stock_id.qte_disponible - self.qte_destockee
        })

        # SUPPRIMÉ: Ne plus mettre à jour manuellement la quantité destockée
        # self.detail_reception_id.qte_colis_destockes += self.qte_destockee

        return {'type': 'ir.actions.act_window_close'}

    def action_destock_back(self):
        # Vérifier que la quantité à destocker ne dépasse pas la quantité disponible
        if self.qte_destockee <= 0:
            raise ValidationError(_("La quantité destockée doit être supérieure à 0"))

        # Vérifier que la quantité à destocker ne dépasse pas la quantité disponible
        if self.qte_destockee > self.stock_id.qte_disponible:
            raise ValidationError(_("La quantité destockée ne peut être supérieure à la quantité disponible!"))

        # Vérifier que la ligne de réception a été trouvée
        if not self.detail_reception_id:
            raise ValidationError(_("Impossible de trouver la ligne de réception correspondante pour ce destockage."))

        # Vérifier que la ligne de réception a suffisamment de quantité disponible
        if self.detail_reception_id.qte_colis_disponibles < self.qte_destockee:
            raise ValidationError(_(
                "La quantité disponible dans la ligne de réception (%s) est insuffisante pour ce destockage (%s)."
            ) % (self.detail_reception_id.qte_colis_disponibles, self.qte_destockee))

        # Créer un enregistrement de destockage
        self.env['gecafle.destockage'].with_context(force_stock=True).create({
            'stock_id': self.stock_id.id,
            'detail_reception_id': self.detail_reception_id.id,  # Ajouter la référence à la ligne de réception
            'qte_disponible': self.qte_disponible,
            'qte_destockee': self.qte_destockee,
            'destockage_date': self.destockage_date,
            'observation': self.observation,
        })

        # Mettre à jour la quantité disponible du stock
        self.stock_id.with_context(force_stock=True).write({
            'qte_disponible': self.stock_id.qte_disponible - self.qte_destockee
        })

        # Mettre à jour la quantité destockée dans la ligne de réception
        self.detail_reception_id.qte_colis_destockes += self.qte_destockee

        return {'type': 'ir.actions.act_window_close'}
