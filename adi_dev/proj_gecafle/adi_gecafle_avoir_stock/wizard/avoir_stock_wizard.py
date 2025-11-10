# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class GecafleAvoirExpressWizard(models.TransientModel):
    _inherit = 'gecafle.avoir.client.wizard'

    # Toggle pour activer la sélection détaillée
    mode_stock_detail = fields.Boolean(
        string="Avoir sur stock (sélection détaillée)",
        default=False,
        help="Permet de sélectionner individuellement les produits et quantités à retourner"
    )

    # Lignes de détail pour la sélection
    line_ids = fields.One2many(
        'gecafle.avoir.stock.wizard.line',
        'wizard_id',
        string="Produits à retourner"
    )

    # Montant calculé automatiquement
    montant_calcule = fields.Monetary(
        string="Montant calculé",
        compute='_compute_montant_calcule',
        store=True,
        currency_field='currency_id'
    )

    # SIMPLIFICATION : Un seul champ pour gérer le retour physique
    gerer_retour_stock = fields.Boolean(
        string="Gérer le retour physique du stock",
        default=False,  # Changé à False par défaut
        help="Si activé, créera une réception de retour et ajoutera les produits au stock. "
             "Si désactivé, créera uniquement un avoir comptable sans mouvement de stock."
    )

    type_retour = fields.Selection([
        ('revente', 'Pour revente'),
        ('destockage', 'Pour destockage'),
    ], string="Type de retour (informatif)", default='revente')

    @api.depends('line_ids.montant_total', 'line_ids.inclure')
    def _compute_montant_calcule(self):
        """Calcule le montant total basé sur les lignes sélectionnées"""
        for record in self:
            montant = sum(line.montant_total for line in record.line_ids if line.inclure)
            record.montant_calcule = montant

    @api.onchange('mode_stock_detail')
    def _onchange_mode_stock_detail(self):
        """Gère l'activation/désactivation du mode détaillé"""
        if not self.mode_stock_detail:
            for line in self.line_ids:
                line.inclure = False
                line.qte_retour = 0
                line.nombre_colis_retour = 0
            if self.vente_id:
                self.montant_avoir = self.montant_vente * 0.1
            # Désactiver le retour stock par défaut
            self.gerer_retour_stock = False

    def action_create_avoir_express(self):
        """Override pour gérer le mode stock détaillé avec ou sans retour physique"""
        self.ensure_one()

        if self.mode_stock_detail:
            # Vérifications
            lignes_incluses = self.line_ids.filtered(lambda l: l.inclure)

            if not lignes_incluses:
                raise ValidationError(_("Veuillez sélectionner au moins un produit à retourner."))

            montant_total = sum(lignes_incluses.mapped('montant_total'))

            if montant_total <= 0:
                raise ValidationError(_("Le montant calculé doit être supérieur à zéro."))

            # Construction de la description
            description_complete = self._build_description(lignes_incluses)

            # Créer l'avoir (toujours créé, que ce soit avec ou sans retour physique)
            avoir = self.env['gecafle.avoir.client'].with_context(
                force_automation=True,
                skip_confirmation=True,
                avoir_stock_detail=True
            ).create({
                'vente_id': self.vente_id.id,
                'date': fields.Date.today(),
                'type_avoir': self.type_avoir,
                'montant_avoir': montant_total,
                'description': description_complete,
                'generer_avoirs_producteurs': self.generer_avoirs_producteurs,
            })

            # GESTION CONDITIONNELLE DU RETOUR PHYSIQUE
            if self.gerer_retour_stock:
                # Créer les réceptions de retour SEULEMENT si demandé
                self._creer_receptions_retour(avoir, lignes_incluses)

                # Message dans le chatter
                avoir.message_post(
                    body=_("✅ Avoir créé AVEC retour physique de stock.\n"
                           "Type de retour : %s\n"
                           "Réceptions de retour créées.") % (
                             dict(self._fields['type_retour'].selection).get(self.type_retour)
                         )
                )
            else:
                # PAS de création de réception, juste l'avoir comptable
                avoir.message_post(
                    body=_("📄 Avoir créé SANS retour physique de stock.\n"
                           "Type informatif : %s\n"
                           "Uniquement un avoir comptable a été généré.") % (
                             dict(self._fields['type_retour'].selection).get(self.type_retour)
                         )
                )

            # Retourner la vue de l'avoir créé
            return {
                'name': _('Avoir Client'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'gecafle.avoir.client',
                'res_id': avoir.id,
                'target': 'current',
            }
        else:
            return super().action_create_avoir_express()

    def _build_description(self, lignes):
        """Construit la description détaillée de l'avoir"""
        details = []
        for line in lignes:
            # Ajouter une indication si le prix a été modifié
            prix_info = ""
            if hasattr(line, 'prix_unitaire_original') and line.prix_unitaire != line.prix_unitaire_original:
                prix_info = f" (prix modifié de {line.prix_unitaire_original:.2f})"

            if line.nombre_colis_retour > 0:
                details.append(
                    f"- {line.produit_id.name} ({line.producteur_id.name}): "
                    f"{line.nombre_colis_retour} colis ({line.qte_retour:.2f} kg) à {line.prix_unitaire:.2f} DA/kg{prix_info}"
                )
            else:
                details.append(
                    f"- {line.produit_id.name} ({line.producteur_id.name}): "
                    f"{line.qte_retour:.2f} kg à {line.prix_unitaire:.2f} DA/kg{prix_info}"
                )

        # Ajouter l'information sur le type de retour
        type_info = ""
        if self.gerer_retour_stock:
            type_info = f"\n📦 Retour physique : {dict(self._fields['type_retour'].selection).get(self.type_retour)}"
        else:
            type_info = f"\n💳 Avoir comptable uniquement (pas de retour physique)"

        description = f"{self.description}{type_info}\n\n📋 Détail des produits retournés:\n" + "\n".join(details)
        return description

    def _creer_receptions_retour(self, avoir, lignes):
        """
        Crée des réceptions de type retour SEULEMENT si gerer_retour_stock est True
        """
        Reception = self.env['gecafle.reception']
        DetailReception = self.env['gecafle.details_reception']

        # Dictionnaire pour regrouper par producteur
        receptions_groupees = defaultdict(list)

        for line in lignes:
            key = (line.producteur_id.id, line.reception_num)
            receptions_groupees[key].append(line)

        # Créer une réception de retour pour chaque groupe
        receptions_creees = []

        for (producteur_id, reception_num), grouped_lines in receptions_groupees.items():
            producteur = self.env['gecafle.producteur'].browse(producteur_id)

            # Générer le nom de la réception de retour
            company = self.env.company
            new_name = company.sudo().increment_counter('reception_counter')

            # Préparer les valeurs de la réception
            reception_vals = {
                'name': new_name,
                'producteur_id': producteur_id,
                'reception_date': fields.Datetime.now(),
                'is_return': True,
                'avoir_client_id': avoir.id,
                'user_id': self.env.user.id,
                'state': 'brouillon',
                'avance_producteur': 0,
                'observations': f"Retour suite à avoir {avoir.name} - Type: {self.type_retour} (informatif)",
            }

            # Créer la réception
            nouvelle_reception = Reception.create(reception_vals)

            # Ajouter les lignes de détail
            for line in grouped_lines:
                DetailReception.create({
                    'reception_id': nouvelle_reception.id,
                    'designation_id': line.produit_id.id,
                    'qualite_id': line.qualite_id.id if line.qualite_id else False,
                    'type_colis_id': line.type_colis_id.id,
                    'qte_colis_recue': line.nombre_colis_retour,
                    'observation': f"Retour depuis vente {self.vente_id.name} - {self.type_retour}",
                })

            receptions_creees.append(nouvelle_reception)

            # Message dans le chatter de l'avoir
            avoir.message_post(
                body=_("✅ Réception de retour créée: %s pour le producteur %s\n"
                       "Type de retour: %s") % (
                         nouvelle_reception.name,
                         producteur.name,
                         self.type_retour
                     )
            )

            _logger.info("Réception de retour créée: %s", nouvelle_reception.name)

        # Confirmer automatiquement si configuré
        if hasattr(self.env.company,
                   'auto_confirmer_receptions_retour') and self.env.company.auto_confirmer_receptions_retour:
            for reception in receptions_creees:
                try:
                    reception.action_confirm()
                except Exception as e:
                    _logger.warning("Impossible de confirmer la réception %s: %s", reception.name, str(e))

        return receptions_creees

    # Méthodes d'actions rapides (restent identiques)
    def select_all_lines(self):
        """Sélectionne toutes les lignes"""
        for line in self.line_ids:
            line.inclure = True
            if line.nombre_colis_vendu > 0:
                line.nombre_colis_retour = line.nombre_colis_vendu
                line.qte_retour = line.qte_vendue
        return {'type': 'ir.actions.do_nothing'}

    def unselect_all_lines(self):
        """Désélectionne toutes les lignes"""
        for line in self.line_ids:
            line.inclure = False
            line.nombre_colis_retour = 0
            line.qte_retour = 0
        return {'type': 'ir.actions.do_nothing'}

    def reset_quantities(self):
        """Réinitialise les quantités aux valeurs vendues"""
        for line in self.line_ids:
            if line.inclure:
                line.nombre_colis_retour = line.nombre_colis_vendu
                line.qte_retour = line.qte_vendue
        return {'type': 'ir.actions.do_nothing'}


class GecafleAvoirStockWizardLine(models.TransientModel):
    _name = 'gecafle.avoir.stock.wizard.line'
    _description = 'Ligne de sélection pour avoir stock'
    _rec_name = 'produit_id'

    wizard_id = fields.Many2one(
        'gecafle.avoir.client.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade'
    )

    detail_vente_id = fields.Many2one(
        'gecafle.details_ventes',
        string="Ligne de vente source",
        readonly=True
    )

    reception_num = fields.Char(
        string="N° Réception",
        compute='_compute_reception_num',
        store=True,
        readonly=True
    )

    @api.depends('detail_vente_id')
    def _compute_reception_num(self):
        """Récupère le numéro de réception depuis la ligne de vente"""
        for record in self:
            if record.detail_vente_id and record.detail_vente_id.reception_id:
                record.reception_num = record.detail_vente_id.reception_id.name
            else:
                record.reception_num = ''

    produit_id = fields.Many2one(
        'gecafle.produit',
        string="Produit",
        required=True,
        readonly=True
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string="Producteur",
        readonly=True
    )

    qualite_id = fields.Many2one(
        'gecafle.qualite',
        string="Qualité",
        readonly=True
    )

    type_colis_id = fields.Many2one(
        'gecafle.emballage',
        string="Type colis",
        readonly=True
    )

    # MODIFICATION : Champ prix unitaire éditable
    prix_unitaire = fields.Float(
        string="Prix unitaire",
        digits='Product Price'
        # SUPPRIMÉ : readonly=True
    )

    # AJOUT : Champ pour stocker le prix original
    prix_unitaire_original = fields.Float(
        string="Prix unitaire original",
        readonly=True,
        digits='Product Price',
        help="Prix unitaire de la vente originale"
    )

    # Champs pour les quantités vendues
    nombre_colis_vendu = fields.Integer(
        string="Nb colis vendus",
        readonly=True,
        help="Nombre de colis initialement vendus"
    )

    qte_vendue = fields.Float(
        string="Qté vendue (kg)",
        readonly=True,
        help="Quantité en kg initialement vendue"
    )

    # Toggle pour inclure dans l'avoir
    inclure = fields.Boolean(
        string="Inclure",
        default=False,
        help="Cocher pour inclure ce produit dans l'avoir"
    )

    # Champs pour les quantités à retourner
    nombre_colis_retour = fields.Integer(
        string="Nb colis retour",
        default=0,
        help="Nombre de colis à retourner"
    )

    qte_retour = fields.Float(
        string="Qté retour (kg)",
        default=0,
        digits='Product Unit of Measure',
        help="Quantité en kg à retourner/créditer"
    )

    montant_total = fields.Monetary(
        string="Montant",
        compute='_compute_montant_total',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='wizard_id.currency_id',
        readonly=True
    )

    @api.depends('inclure', 'qte_retour', 'prix_unitaire')
    def _compute_montant_total(self):
        """Calcule le montant total de la ligne"""
        for record in self:
            if record.inclure and record.qte_retour > 0:
                record.montant_total = record.qte_retour * record.prix_unitaire
            else:
                record.montant_total = 0.0

    @api.onchange('inclure')
    def _onchange_inclure(self):
        """Initialise la quantité et le prix quand on coche la ligne"""
        if self.inclure:
            if self.nombre_colis_vendu > 0 and self.nombre_colis_retour == 0:
                self.nombre_colis_retour = self.nombre_colis_vendu
            if self.qte_vendue > 0 and self.qte_retour == 0:
                self.qte_retour = self.qte_vendue
            # Initialiser le prix original si pas déjà fait
            if not self.prix_unitaire_original and self.prix_unitaire:
                self.prix_unitaire_original = self.prix_unitaire
        else:
            self.nombre_colis_retour = 0
            self.qte_retour = 0
            # Restaurer le prix original quand on décoche
            if self.prix_unitaire_original:
                self.prix_unitaire = self.prix_unitaire_original

    @api.onchange('nombre_colis_retour')
    def _onchange_nombre_colis_retour(self):
        """Ajuste la quantité en kg en fonction du nombre de colis"""
        if self.nombre_colis_retour > 0 and self.nombre_colis_vendu > 0 and self.qte_vendue > 0:
            ratio = self.nombre_colis_retour / self.nombre_colis_vendu
            self.qte_retour = self.qte_vendue * ratio
