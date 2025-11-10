# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class GecafleTracabiliteProduits(models.Model):
    _name = 'gecafle.tracabilite.produits'
    _description = 'Traçabilité des Produits - Mouvements de Stock'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc, id desc'

    name = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default='Nouveau'
    )

    date_debut = fields.Date(
        string="Date de début",
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    date_fin = fields.Date(
        string="Date de fin",
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        help="Laisser vide pour tous les producteurs"
    )

    produit_id = fields.Many2one(
        'gecafle.produit',
        string="Produit",
        help="Laisser vide pour tous les produits"
    )

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('calcule', 'Calculé'),
    ], string="État", default='brouillon', tracking=True)

    # Lignes de traçabilité (2 types : réceptions et ventes)
    reception_line_ids = fields.One2many(
        'gecafle.tracabilite.reception.line',
        'tracabilite_id',
        string="Lignes de réception"
    )

    vente_line_ids = fields.One2many(
        'gecafle.tracabilite.vente.line',
        'tracabilite_id',
        string="Lignes de vente"
    )

    # Ligne sélectionnée pour afficher les détails
    selected_reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception sélectionnée"
    )

    # Totaux
    total_entrant = fields.Integer(
        string="Total Entrant",
        compute='_compute_totals',
        store=True
    )

    total_sortant = fields.Integer(
        string="Total Sortant",
        compute='_compute_totals',
        store=True
    )

    total_restant = fields.Integer(
        string="Total Restant",
        compute='_compute_totals',
        store=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('gecafle.tracabilite.produits') or 'TRAC/'
        return super().create(vals)

    @api.depends('reception_line_ids.qte_entrante', 'vente_line_ids.qte_sortante')
    def _compute_totals(self):
        for record in self:
            record.total_entrant = sum(record.reception_line_ids.mapped('qte_entrante'))
            record.total_sortant = sum(record.vente_line_ids.mapped('qte_sortante'))
            record.total_restant = record.total_entrant - record.total_sortant

    def action_calculer(self):
        """Calcule les mouvements de stock pour la période"""
        self.ensure_one()

        # Supprimer les lignes existantes
        self.reception_line_ids.unlink()
        self.vente_line_ids.unlink()

        # Domaine pour les réceptions
        domain_reception = [
            ('state', '=', 'confirmee'),
            ('reception_date', '>=', fields.Datetime.to_datetime(self.date_debut)),
            ('reception_date', '<=', fields.Datetime.to_datetime(self.date_fin).replace(hour=23, minute=59))
        ]

        if self.producteur_id:
            domain_reception.append(('producteur_id', '=', self.producteur_id.id))

        # Récupérer les réceptions
        receptions = self.env['gecafle.reception'].search(domain_reception, order='reception_date')

        # Traiter les réceptions
        for reception in receptions:
            for line in reception.details_reception_ids:
                # Filtrer par produit si spécifié
                if self.produit_id and line.designation_id != self.produit_id:
                    continue

                # Créer la ligne de réception
                self.env['gecafle.tracabilite.reception.line'].create({
                    'tracabilite_id': self.id,
                    'date': reception.reception_date,
                    'numero_reception': reception.name,
                    'reception_id': reception.id,
                    'producteur_id': reception.producteur_id.id,
                    'produit_id': line.designation_id.id,
                    'qualite_id': line.qualite_id.id,
                    'type_colis_id': line.type_colis_id.id,
                    'qte_entrante': line.qte_colis_recue,
                })

        # Domaine pour les ventes
        domain_vente = [
            ('state', '=', 'valide'),
            ('date_vente', '>=', fields.Datetime.to_datetime(self.date_debut)),
            ('date_vente', '<=', fields.Datetime.to_datetime(self.date_fin).replace(hour=23, minute=59))
        ]

        # Récupérer les ventes
        ventes = self.env['gecafle.vente'].search(domain_vente, order='date_vente')

        # Traiter les ventes
        for vente in ventes:
            for line in vente.detail_vente_ids:
                # Filtrer par producteur et produit si spécifiés
                if self.producteur_id and line.producteur_id != self.producteur_id:
                    continue
                if self.produit_id and line.produit_id != self.produit_id:
                    continue

                # Créer la ligne de vente
                self.env['gecafle.tracabilite.vente.line'].create({
                    'tracabilite_id': self.id,
                    'date': vente.date_vente,
                    'numero_vente': vente.name,
                    'client_id': vente.client_id.id,
                    'producteur_id': line.producteur_id.id,
                    'produit_id': line.produit_id.id,
                    'qualite_id': line.qualite_id.id,
                    'type_colis_id': line.type_colis_id.id,
                    'qte_sortante': line.nombre_colis,
                })

        self.state = 'calcule'

        # Message de confirmation
        message = _("Traçabilité calculée avec succès !\n")
        message += _("- %d réceptions trouvées\n") % len(self.reception_line_ids)
        message += _("- %d ventes trouvées\n") % len(self.vente_line_ids)
        message += _("- Total entrant: %d\n") % self.total_entrant
        message += _("- Total sortant: %d\n") % self.total_sortant
        message += _("- Restant: %d") % self.total_restant

        self.message_post(body=message)

        return True

    def action_reset(self):
        """Remet la traçabilité en brouillon"""
        self.state = 'brouillon'
        return True

    def action_select_reception(self):
        """Sélectionne une réception pour voir les détails"""
        self.ensure_one()
        action = self.env.ref('adi_gecafle_receptions.action_gecafle_reception_list').read()[0]
        action['domain'] = [('id', 'in', self.reception_line_ids.mapped('reception_id').ids)]
        return action


class GecafleTracabiliteReceptionLine(models.Model):
    _name = 'gecafle.tracabilite.reception.line'
    _description = 'Ligne de Traçabilité - Réception'
    _order = 'date, id'

    tracabilite_id = fields.Many2one(
        'gecafle.tracabilite.produits',
        string="Traçabilité",
        required=True,
        ondelete='cascade'
    )

    date = fields.Datetime(
        string="Date/Heure",
        required=True
    )

    numero_reception = fields.Char(
        string="N° Réception",
        required=True
    )

    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception"
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur"
    )

    produit_id = fields.Many2one(
        'gecafle.produit',
        string="Désignation"
    )

    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité"
    )

    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type Colis"
    )

    qte_entrante = fields.Integer(
        string="Nbre colis",
        default=0
    )


class GecafleTracabiliteVenteLine(models.Model):
    _name = 'gecafle.tracabilite.vente.line'
    _description = 'Ligne de Traçabilité - Vente'
    _order = 'date, id'

    tracabilite_id = fields.Many2one(
        'gecafle.tracabilite.produits',
        string="Traçabilité",
        required=True,
        ondelete='cascade'
    )

    date = fields.Datetime(
        string="Date/Heure",
        required=True
    )

    numero_vente = fields.Char(
        string="N° Souche",
        required=True
    )

    client_id = fields.Many2one(
        'gecafle.client',
        string="Client"
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur"
    )

    produit_id = fields.Many2one(
        'gecafle.produit',
        string="Désignation"
    )

    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité"
    )

    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type Colis"
    )

    qte_sortante = fields.Integer(
        string="Nbre colis",
        default=0
    )
