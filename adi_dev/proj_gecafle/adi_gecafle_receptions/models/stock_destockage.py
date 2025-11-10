from odoo import models, fields, api,_
from odoo.exceptions import ValidationError

class GecafleStock(models.Model):
    _name = 'gecafle.stock'
    _description = 'Journal de Stock'


    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception",
        required=True,
        ondelete='cascade'
    )




    producteur_id = fields.Many2one(
        string="Producteur",
        related='reception_id.producteur_id',
        store=True
    )
    reception_date = fields.Datetime(
        string="Date de Réception",
        related='reception_id.reception_date',
        store=True
    )
    designation_id = fields.Many2one(
        'gecafle.produit',
        string="Produit",
        required=True
    )
    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité"
    )
    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string="Emballage",
        required=True
    )
    qte_disponible = fields.Integer(
        string="Quantité Disponible",
        required=True,
        default=0
    )
    qte_destockee = fields.Integer(
        string="Quantité Destockée",
        required=True,
        default=0
    )

    destockage_date = fields.Datetime(
        string="Date de Destockage",
        default=fields.Datetime.now,
        required=True
    )
    observation = fields.Text(string="Observation")

    destockage_ids = fields.One2many(
        'gecafle.destockage',
        'stock_id',
        string="Opérations de Destockage"
    )


    @api.depends('destockage_ids', 'destockage_ids.qte_destockee')
    def _compute_qte_destockee(self):
        for stock in self:
            stock.qte_destockee = sum(stock.destockage_ids.mapped('qte_destockee'))

    @api.model
    def create(self, vals):
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La création manuelle du stock est interdite, il est généré automatiquement."))
        return super(GecafleStock, self).create(vals)

    def write(self, vals):
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La modification du stock est interdite, il est généré automatiquement."))
        return super(GecafleStock, self).write(vals)

    def unlink(self):
        # On autorise la suppression uniquement si le contexte contient 'force_stock'
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La suppression des entrées de stock est interdite."))
        return super().unlink()
    def copy(self):
        # On autorise la copie uniquement si le contexte contient 'force_stock'
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La Copie des entrées de stock est interdite."))
        return super().copy()


class GecafleDestockage(models.Model):
    _name = 'gecafle.destockage'
    _description = 'Historique de Destockage'


    stock_id = fields.Many2one(
        'gecafle.stock',
        string="Ligne de Stock",
        required=True,
        ondelete='cascade'
    )
    reception_id = fields.Many2one(
        related='stock_id.reception_id',
        string="Réception",
        store=True,
        readonly=True
    )
    detail_reception_id = fields.Many2one(
        'gecafle.details_reception',
        string="Ligne de Réception"
    )
    producteur_id = fields.Many2one(
        string="Producteur",
        related='reception_id.producteur_id',
        store=True
    )
    reception_date = fields.Datetime(
        related='stock_id.reception_date',
        string="Date de Réception",
        store=True,
        readonly=True
    )
    designation_id = fields.Many2one(
        related='stock_id.designation_id',
        string="Produit",
        store=True,
        readonly=True
    )
    emballage_id = fields.Many2one(
        related='stock_id.emballage_id',
        string="Emballage",
        store=True,
        readonly=True
    )
    qualite_id = fields.Many2one(
        related='stock_id.qualite_id',
        string="Qualité",
        store=True,
        readonly=True
    )
    qte_destockee = fields.Integer(
        string="Quantité Destockée",
        required=True
    )
    qte_disponible = fields.Integer(
        string="Quantité Disponible",
        related='stock_id.qte_disponible',
        readonly=True
    )
    destockage_date = fields.Datetime(
        string="Date de Destockage",
        default=fields.Datetime.now,
        required=True
    )
    observation = fields.Text(string="Observation")

    @api.model
    def create(self, vals):
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La création manuelle du stock est interdite, il est généré automatiquement."))
        return super(GecafleDestockage, self).create(vals)

    def write(self, vals):
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La modification du stock est interdite, il est généré automatiquement."))
        return super(GecafleDestockage, self).write(vals)

    def unlink(self):
        # On autorise la suppression uniquement si le contexte contient 'force_stock'
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La suppression des entrées de stock est interdite."))
        return super().unlink()

    def copy(self):
        # On autorise la copie uniquement si le contexte contient 'force_stock'
        if not self.env.context.get('force_stock'):
            raise ValidationError(_("La Copie des entrées de stock est interdite."))
        return super().copy()

