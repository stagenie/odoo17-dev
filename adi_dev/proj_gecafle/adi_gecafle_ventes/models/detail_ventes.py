# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

#  On va modifier les modèle existants
class GecafleReceptionInherit(models.Model):
    _inherit = 'gecafle.reception'
    _rec_name = 'display_name'

    # Champ calculé pour l'affichage dans les listes déroulantes
    """
    
    """
    # Champ calculé simplifié
    display_name = fields.Char(
        string="Affichage",
        compute="_compute_display_name",
        store=True
    )

    @api.depends('name', 'producteur_id.name')
    def _compute_display_name(self):
        for record in self:
            # Accès prudent aux champs
            nom = record.name or ""
            producteur = record.producteur_id.name if record.producteur_id else ''

            # Accès au champ date avec gestion d'erreur
            date_str = ""
            for date_field in ['date_reception', 'reception_date', 'date']:
                if hasattr(record, date_field) and getattr(record, date_field):
                    try:
                        date_str = getattr(record, date_field).strftime('%d/%m/%Y %H:%M')
                        break
                    except:
                        pass

            record.display_name = f"[{nom}] {producteur} - {date_str}"

    def name_get(self):
        return [(record.id, record.display_name) for record in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search pour recherche multi-champs"""
        args = args or []
        domain = []

        if name:
            # Recherche dans plusieurs champs
            domain = ['|', '|',
                      ('name', operator, name),
                      ('producteur_id.name', operator, name),
                      ('display_name', operator, name)
                      ]

        # Combiner avec les args existants
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()


class GecafleDetailsReceptionInherit(models.Model):
    _inherit = 'gecafle.details_reception'
    _rec_name = 'display_name'

    # Ajouter les relations One2many explicites
    detail_vente_ids = fields.One2many(
        'gecafle.details_ventes',
        'detail_reception_id',
        string="Lignes de vente"
    )


    detail_destockage_ids = fields.One2many(
        'gecafle.destockage',
        'detail_reception_id',
        string="Lignes de destockage"
    )
    qte_colis_vendus = fields.Integer(
        string="Quantité Vendue",
        compute="_compute_quantities",
        store=True
    )
    qte_colis_destockes = fields.Integer(
        string="Quantité Destockée",
        compute="_compute_quantities",
        store=True
    )
    qte_colis_disponibles = fields.Integer(
        string="Quantité Disponible",
        compute="_compute_quantities",
        store=True
    )

    @api.depends('qte_colis_recue',
                 'detail_vente_ids.nombre_colis',
                 'detail_vente_ids.vente_id.state',
                 'detail_destockage_ids.qte_destockee')
    def _compute_quantities(self):
        for record in self:
            # Calcul des quantités vendues (uniquement les ventes validées)
            qte_vendus = sum(record.detail_vente_ids.filtered(
                lambda v: v.vente_id.state == 'valide'
            ).mapped('nombre_colis'))

            # Calcul des quantités destockées
            qte_destockes = sum(record.detail_destockage_ids.mapped('qte_destockee'))

            record.qte_colis_vendus = qte_vendus
            record.qte_colis_destockes = qte_destockes
            record.qte_colis_disponibles = max(0, record.qte_colis_recue - qte_vendus - qte_destockes)

    @api.constrains('qte_colis_recue',
                    'qte_colis_vendus',
                    'qte_colis_destockes')
    def _check_quantities(self):
        """
        Vérifie que la quantité reçue n'est pas inférieure à la somme des quantités vendues et destockées
        """
        for record in self:
            total_sorties = record.qte_colis_vendus + record.qte_colis_destockes
            if record.qte_colis_recue < total_sorties:
                raise ValidationError(_(
                    "La quantité reçue (%s) ne peut pas être inférieure à la somme des quantités "
                    "déjà vendues (%s) et destockées (%s)"
                ) % (record.qte_colis_recue, record.qte_colis_vendus, record.qte_colis_destockes))

    # Champ pour faciliter la recherche et l'affichage
    def name_get(self):
        # Implémentation plus directe pour Odoo 18
        result = []
        for record in self:
            product_name = record.designation_id.name if record.designation_id else 'Inconnu'
            quality = record.qualite_id.name if record.qualite_id else '-'
            package = record.type_colis_id.name if record.type_colis_id else '-'
            available = record.qte_colis_disponibles or 0

            name = "{} - {} / {} [{}]".format(
                product_name, quality, package, available
            )
            result.append((record.id, name))
        return result

    display_name = fields.Char(
        string="Affichage",
        compute="_compute_display_name",
        store=True
    )

    @api.depends('designation_id.name', 'qualite_id.name', 'type_colis_id.name', 'qte_colis_disponibles')
    def _compute_display_name(self):
        for record in self:
            product = record.designation_id.name if record.designation_id else 'Inconnu'
            quality = record.qualite_id.name if record.qualite_id else '-'
            package = record.type_colis_id.name if record.type_colis_id else '-'
            available = record.qte_colis_disponibles or 0

            record.display_name = f"{product} - {quality} / {package} [{available}]"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Recherche améliorée dans plusieurs champs"""
        args = args or []
        domain = []

        if name:
            # Recherche dans plusieurs champs liés
            domain = ['|', '|', '|',
                      ('designation_id.name', operator, name),
                      ('qualite_id.name', operator, name),
                      ('type_colis_id.name', operator, name),
                      ('display_name', operator, name)]

        # Combiner avec les arguments existants
        records = self.search(domain + args, limit=limit)
        return records.name_get()





class GecafleDetailsVentes(models.Model):
    _name = 'gecafle.details_ventes'
    _description = 'Détails des Ventes'

    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente",
        required=True,
        ondelete='cascade'
    )
    reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception",
        required=True,
        domain=lambda self: self._get_reception_domain()
    )

    @api.model
    def _get_reception_domain(self):
        """Retourne le domaine pour filtrer les réceptions avec stock disponible"""
        # Rechercher toutes les réceptions qui ont du stock disponible
        receptions_with_stock = self.env['gecafle.details_reception'].search([
            ('qte_colis_disponibles', '>', 0)
        ]).mapped('reception_id.id')


        # Créer le domaine
        return [
            ('state', 'in', ['brouillon', 'confirmee']),
            ('id', 'in', receptions_with_stock),
        ]
    """ 
     reception_id = fields.Many2one(
        'gecafle.reception',
        string="Réception",
        required=True,
        domain="[('state', 'in', ['brouillon', 'confirmee'])]",

    )

    """



    detail_reception_id = fields.Many2one(
        'gecafle.details_reception',
        string="Ligne Réception",
        required=True,
        domain="[('reception_id', '=', reception_id),"
               " ('qte_colis_disponibles', '>', 0)]"
    )

    @api.onchange('reception_id')
    def _onchange_reception_id(self):
        """Réinitialise la ligne de réception quand la réception change"""
        self.detail_reception_id = False

        if self.reception_id:
            # Vérifier s'il y a des lignes disponibles
            lines = self.env['gecafle.details_reception'].search([
                ('reception_id', '=', self.reception_id.id),
                ('qte_colis_disponibles', '>', 0)
            ])

            if not lines:
                return {
                    'warning': {
                        'title': 'Attention',
                        'message': 'Cette réception ne contient pas de lignes avec stock disponible.'
                    }
                }


    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        related="reception_id.producteur_id",
        store=True,
        readonly=True
    )
    produit_id = fields.Many2one(
        'gecafle.produit',
        string="Produit",
        related="detail_reception_id.designation_id",
        store=True,
        readonly=True
    )
    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type de Colis",
        required=True
    )
    type_produit = fields.Selection(
        string="Type",
        related="produit_id.type",
        store=True,
        readonly=True
    )
    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité",
        related="detail_reception_id.qualite_id",
        store=True,
        readonly=True
    )
    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type d'emballage",
        related="detail_reception_id.type_colis_id",
        store=True,
        readonly=True
    )
    nombre_colis = fields.Integer(
        string="Nb Colis",
        required=True,
        default=1
    )
    poids_brut = fields.Float(
        string="Poids brut",
        digits=(16, 2),
        required=True,
        default=1,
    )

    poids_brut_un_colis = fields.Float(
        string="Poids/U",
        compute="_compute_poids_colis",
        store=True,
        digits=(16, 2)
    )
    poids_colis = fields.Float(
        string="Poids colis",
        compute="_compute_poids_colis",
        store=True,
        digits=(16, 2)
    )
    prix_colis = fields.Float(
        string="Prix  Colis",
        compute="_compute_prix_colis",
        store=True,
        digits=(16, 2)
    )
    poids_net = fields.Float(
        string="Poids net",
        compute="_compute_poids_net",
        store=True,
        digits=(16, 2)
    )
    prix_unitaire = fields.Float(
        string="Prix unitaire",
        digits=(16, 2),
        required=True,
        default=1
    )
    montant_net = fields.Monetary(
        string="Montant Net",
        compute="_compute_montants",
        store=True,
        currency_field="currency_id"
    )
    taux_commission = fields.Float(
        string="% Commission",
        compute="_compute_commission",
        store=True,
        digits=(5, 2)
    )
    montant_commission = fields.Monetary(
        string="Montant Commission",
        compute="_compute_montants",
        store=True,
        currency_field="currency_id"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related="vente_id.currency_id",
        readonly=True
    )

    @api.depends('nombre_colis', 'poids_brut')
    def _compute_poids_unite(self):
        """Calcule le poids par unité"""
        for record in self:
            record.poids_unite = record.poids_brut / record.nombre_colis if record.nombre_colis else 0

    @api.depends('nombre_colis', 'type_colis_id')
    def _compute_poids_colis(self):
        """Calcule le poids total des emballages"""
        for record in self:
            poids_unite_emballage = record.type_colis_id.weight if record.type_colis_id else 0
            record.poids_colis = poids_unite_emballage * record.nombre_colis
            if record.nombre_colis > 0:
                record.poids_brut_un_colis = record.poids_brut / record.nombre_colis

    @api.depends('nombre_colis', 'type_colis_id')
    def _compute_prix_colis(self):
        """Calcule le poids total des emballages"""
        for record in self:
            prix_unite_emballage = record.type_colis_id.price_unit if record.type_colis_id else 0
            record.prix_colis = prix_unite_emballage * record.nombre_colis
            record.prix_colis = prix_unite_emballage * record.nombre_colis



    @api.depends('poids_brut', 'poids_colis')
    def _compute_poids_net(self):
        """Calcule le poids net (poids brut - poids emballages)"""
        for record in self:
            record.poids_net = record.poids_brut - record.poids_colis

    @api.depends('produit_id', 'type_produit', 'producteur_id')
    def _compute_commission(self):
        """Calcule le taux de commission en fonction du type de produit et du producteur"""
        for record in self:
            if record.producteur_id and record.producteur_id.use_custom_margin:
                if record.type_produit == 'fruit':
                    record.taux_commission = record.producteur_id.fruit_margin
                else:  # légume
                    record.taux_commission = record.producteur_id.vegetable_margin
            else:
                company =self.env.company
                if record.type_produit == 'fruit':
                    record.taux_commission = company.marge_fruits
                else:  # légume
                    record.taux_commission = company.marge_legumes

    @api.depends('poids_net', 'prix_unitaire', 'taux_commission')
    def _compute_montants(self):
        """Calcule les montants (HT, commission, net)"""
        for record in self:
            record.montant_net = record.poids_net * record.prix_unitaire
            record.montant_commission = record.montant_net * (record.taux_commission / 100)


    @api.constrains('nombre_colis', 'detail_reception_id')
    def _check_disponibilite(self):
        """Vérifie que la quantité demandée est disponible"""
        for record in self:
            if record.nombre_colis <= 0:
                raise ValidationError(_("Le nombre de colis doit être supérieur à zéro"))

            if record.nombre_colis > record.detail_reception_id.qte_colis_disponibles:
                raise ValidationError(_(
                    "Quantité insuffisante! Disponible: %s, Demandé: %s"
                ) % (record.detail_reception_id.qte_colis_disponibles, record.nombre_colis))

    def name_get(self):
        """Affichage plus convivial pour les lignes de vente"""
        result = []
        for record in self:
            # Format : "Produit - Qualité - Type colis (X colis)"
            product_name = record.produit_id.name if record.produit_id else 'Sans produit'
            quality = record.qualite_id.name if record.qualite_id else ''
            package = record.type_colis_id.name if record.type_colis_id else ''
            quantity = record.nombre_colis or 0

            # Construction du nom
            parts = [product_name]
            if quality:
                parts.append(quality)
            if package:
                parts.append(package)

            name = " - ".join(parts)
            name += f" ({quantity} colis)"

            result.append((record.id, name))
        return result

    # Ajouter aussi un champ display_name calculé
    display_name = fields.Char(
        string="Description",
        compute="_compute_display_name",
        store=True
    )

    @api.depends('produit_id', 'qualite_id', 'type_colis_id', 'nombre_colis')
    def _compute_display_name(self):
        for record in self:
            name_data = dict(record.name_get())
            record.display_name = name_data.get(record.id, '')




