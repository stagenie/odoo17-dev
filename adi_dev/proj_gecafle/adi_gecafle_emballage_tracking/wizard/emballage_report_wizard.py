# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GecafleEmballageReportWizard(models.TransientModel):
    _name = 'gecafle.emballage.report.wizard'
    _description = 'Assistant Rapport Emballages'

    report_type = fields.Selection([
        ('client', 'Récapitulatif Client'),
        ('producteur', 'Récapitulatif Producteur'),
        ('global', 'État Global'),
        ('detail', 'Détail par Emballage'),
    ], string='Type de rapport', required=True, default='client')

    date_debut = fields.Date(
        string='Date début',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )

    date_fin = fields.Date(
        string='Date fin',
        required=True,
        default=fields.Date.today
    )

    client_id = fields.Many2one(
        'gecafle.client',
        string='Client'
    )

    client_ids = fields.Many2many(
        'gecafle.client',
        string='Clients',
        help='Laissez vide pour inclure tous les clients'
    )

    producteur_id = fields.Many2one(
        'gecafle.producteur',
        string='Producteur'
    )

    producteur_ids = fields.Many2many(
        'gecafle.producteur',
        string='Producteurs',
        help='Laissez vide pour inclure tous les producteurs'
    )

    emballage_ids = fields.Many2many(
        'gecafle.emballage',
        string='Emballages',
        help='Laissez vide pour tous les emballages'
    )

    include_non_returned = fields.Boolean(
        string='Inclure emballages non rendus',
        default=False
    )

    # Options d'affichage
    group_by_date = fields.Boolean(
        string='Grouper par date',
        default=False
    )

    group_by_reference = fields.Boolean(
        string='Grouper par référence',
        default=False
    )

    show_details = fields.Boolean(
        string='Afficher les détails',
        default=True
    )

    show_summary_only = fields.Boolean(
        string='Résumé uniquement',
        default=False
    )

    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
    ], string='Format de sortie', default='pdf')

    def action_print_report(self):
        """Génère le rapport"""
        self.ensure_one()

        # Validation des dates
        if self.date_debut > self.date_fin:
            raise UserError(_("La date de début doit être antérieure à la date de fin"))

        # Vérifier qu'il y a des données
        if not self._has_data():
            raise UserError(_("Aucune donnée trouvée pour les critères sélectionnés"))

        # Sélection du rapport selon le type
        if self.report_type == 'client':
            return self._print_client_report()
        elif self.report_type == 'producteur':
            return self._print_producteur_report()
        elif self.report_type == 'global':
            return self._print_global_report()
        else:
            return self._print_detail_report()

    def _has_data(self):
        """Vérifie s'il y a des données pour le rapport"""
        domain = self._get_mouvement_domain()
        return self.env['gecafle.emballage.mouvement'].search_count(domain) > 0

    def _get_mouvement_domain(self):
        """Construit le domaine pour les mouvements"""
        domain = [
            ('date', '>=', datetime.combine(self.date_debut, datetime.min.time())),
            ('date', '<=', datetime.combine(self.date_fin, datetime.max.time())),
            ('is_cancelled', '=', False),  # Exclure les mouvements annulés
        ]

        # Filtrer par emballages
        if self.emballage_ids:
            domain.append(('emballage_id', 'in', self.emballage_ids.ids))

        # Filtrer selon le type de rapport
        if self.report_type == 'client':
            if self.client_id:
                domain.append(('client_id', '=', self.client_id.id))
            elif self.client_ids:
                domain.append(('client_id', 'in', self.client_ids.ids))
            else:
                domain.append(('client_id', '!=', False))

        elif self.report_type == 'producteur':
            if self.producteur_id:
                domain.append(('producteur_id', '=', self.producteur_id.id))
            elif self.producteur_ids:
                domain.append(('producteur_id', 'in', self.producteur_ids.ids))
            else:
                domain.append(('producteur_id', '!=', False))

        return domain

    def _print_client_report(self):
        """Imprime le rapport client"""
        # CORRECTION : Passer self directement, pas de data wrapper
        return self.env.ref('adi_gecafle_emballage_tracking.action_report_emballage_client').report_action(self)

    def _print_producteur_report(self):
        """Imprime le rapport producteur"""
        # CORRECTION : Passer self directement
        return self.env.ref('adi_gecafle_emballage_tracking.action_report_emballage_producteur').report_action(self)

    def _print_global_report(self):
        """Imprime le rapport global"""
        # CORRECTION : Passer self directement
        return self.env.ref('adi_gecafle_emballage_tracking.action_report_emballage_global').report_action(self)

    def _print_detail_report(self):
        """Imprime le rapport détaillé"""
        # CORRECTION : Passer self directement
        return self.env.ref('adi_gecafle_emballage_tracking.action_report_emballage_detail').report_action(self)

    def _prepare_report_data(self):
        """Prépare les données complètes pour tous les types de rapport"""
        self.ensure_one()

        # Récupérer les mouvements selon les critères
        domain = self._get_mouvement_domain()
        mouvements = self.env['gecafle.emballage.mouvement'].search(domain, order='date, id')

        data = {
            'wizard': self,
            'type_rapport': self.report_type,
            'date_debut': self.date_debut,
            'date_fin': self.date_fin,
            'show_details': self.show_details,
            'company': self.env.company,
        }

        # Traitement selon le type de rapport
        if self.report_type == 'client':
            data.update(self._prepare_client_data(mouvements))
        elif self.report_type == 'producteur':
            data.update(self._prepare_producteur_data(mouvements))
        elif self.report_type == 'global':
            data.update(self._prepare_global_data(mouvements))
        else:  # detail
            data.update(self._prepare_detail_data(mouvements))

        return data

    def _prepare_client_data(self, mouvements):
        """Prépare les données pour le rapport client"""
        data = {
            'client': self.client_id.name if self.client_id else 'Tous les clients',
            'sections': {}
        }

        # Grouper par client
        for mouv in mouvements:
            if not mouv.client_id:
                continue

            client_key = mouv.client_id.id
            if client_key not in data['sections']:
                data['sections'][client_key] = {
                    'client': mouv.client_id,
                    'ventes': [],
                    'autres': [],
                    'resume': {}
                }

            section = data['sections'][client_key]

            # CORRECTION : Formater la date en string AVANT de l'envoyer au template
            date_formatted = mouv.date.strftime('%d/%m/%Y') if mouv.date else ''

            # Séparer ventes et autres mouvements
            if mouv.type_mouvement in ['sortie_vente', 'retour_client', 'consigne']:
                section['ventes'].append({
                    'date': date_formatted,  # Date déjà formatée
                    'reference': mouv.reference or mouv.name,
                    'emballage': mouv.emballage_id.name if mouv.emballage_id else '',
                    'qte_sortante': mouv.quantite if mouv.type_mouvement == 'sortie_vente' else 0,
                    'qte_entrante': mouv.quantite if mouv.type_mouvement in ['retour_client', 'consigne'] else 0,
                })
            else:
                section['autres'].append({
                    'date': date_formatted,  # Date déjà formatée
                    'reference': mouv.name,
                    'emballage': mouv.emballage_id.name if mouv.emballage_id else '',
                    'qte_sortante': mouv.quantite if mouv.sens == 'sortie' else 0,
                    'qte_entrante': mouv.quantite if mouv.sens == 'entree' else 0,
                })

            # Calculer le résumé par emballage
            if mouv.emballage_id:
                emb_key = mouv.emballage_id.id
                if emb_key not in section['resume']:
                    section['resume'][emb_key] = {
                        'emballage': mouv.emballage_id.name,  # Nom de l'emballage
                        'qte_sortante': 0,
                        'qte_entrante': 0,
                        'difference': 0
                    }

                if mouv.sens == 'sortie':
                    section['resume'][emb_key]['qte_sortante'] += mouv.quantite
                else:
                    section['resume'][emb_key]['qte_entrante'] += mouv.quantite

                section['resume'][emb_key]['difference'] = (
                        section['resume'][emb_key]['qte_sortante'] -
                        section['resume'][emb_key]['qte_entrante']
                )

        # Convertir les résumés en listes
        for client_key in data['sections']:
            data['sections'][client_key]['resume'] = list(
                data['sections'][client_key]['resume'].values()
            )

        return data
    def _prepare_producteur_data(self, mouvements):
        """Prépare les données pour le rapport producteur"""
        data = {
            'producteur': self.producteur_id.name if self.producteur_id else 'Tous les producteurs',
            'sections': {}
        }

        # Grouper par producteur
        for mouv in mouvements:
            if not mouv.producteur_id:
                continue

            prod_key = mouv.producteur_id.id
            if prod_key not in data['sections']:
                data['sections'][prod_key] = {
                    'producteur': mouv.producteur_id,
                    'receptions': [],
                    'autres': [],
                    'resume': {}
                }

            section = data['sections'][prod_key]

            # CORRECTION : Formater la date en string
            date_formatted = mouv.date.strftime('%d/%m/%Y') if mouv.date else ''

            # Séparer réceptions et autres mouvements
            if mouv.type_mouvement in ['entree_reception', 'sortie_producteur']:
                section['receptions'].append({
                    'date': date_formatted,  # Date déjà formatée
                    'reference': mouv.reference or mouv.name,
                    'emballage': mouv.emballage_id.name if mouv.emballage_id else '',
                    'qte_entrante': mouv.quantite if mouv.type_mouvement == 'entree_reception' else 0,
                    'qte_sortante': mouv.quantite if mouv.type_mouvement == 'sortie_producteur' else 0,
                })
            else:
                section['autres'].append({
                    'date': date_formatted,  # Date déjà formatée
                    'reference': mouv.name,
                    'emballage': mouv.emballage_id.name if mouv.emballage_id else '',
                    'qte_entrante': mouv.quantite if mouv.sens == 'entree' else 0,
                    'qte_sortante': mouv.quantite if mouv.sens == 'sortie' else 0,
                })

            # Calculer le résumé avec noms au lieu d'objets
            if mouv.emballage_id:
                emb_key = mouv.emballage_id.id
                if emb_key not in section['resume']:
                    section['resume'][emb_key] = {
                        'emballage': mouv.emballage_id.name,  # Nom string
                        'qte_entrante': 0,
                        'qte_sortante': 0,
                        'difference': 0
                    }

                if mouv.sens == 'entree':
                    section['resume'][emb_key]['qte_entrante'] += mouv.quantite
                else:
                    section['resume'][emb_key]['qte_sortante'] += mouv.quantite

                section['resume'][emb_key]['difference'] = (
                    section['resume'][emb_key]['qte_sortante'] -
                    section['resume'][emb_key]['qte_entrante']
                )

        # Convertir les résumés en listes
        for prod_key in data['sections']:
            data['sections'][prod_key]['resume'] = list(
                data['sections'][prod_key]['resume'].values()
            )

        return data

    def _prepare_global_data(self, mouvements):
        """Prépare les données pour le rapport global"""
        data = {
            'stats': {
                'total_mouvements': len(mouvements),
                'total_entrees': 0,
                'total_sorties': 0,
            },
            'emballages': []
        }

        emballages_dict = {}

        # Calculer les statistiques
        for mouv in mouvements:
            if mouv.sens == 'entree':
                data['stats']['total_entrees'] += mouv.quantite
            else:
                data['stats']['total_sorties'] += mouv.quantite

            # Grouper par emballage
            if mouv.emballage_id:
                emb_key = mouv.emballage_id.id
                if emb_key not in emballages_dict:
                    tracking = self.env['gecafle.emballage.tracking'].search([
                        ('emballage_id', '=', emb_key)
                    ], limit=1)

                    emballages_dict[emb_key] = {
                        'emballage': mouv.emballage_id.name,  # Nom string
                        'stock_initial': tracking.stock_initial if tracking else 0,
                        'stock_disponible': tracking.stock_disponible if tracking else 0,
                        'stock_chez_clients': tracking.stock_chez_clients if tracking else 0,
                        'stock_chez_producteurs': tracking.stock_chez_producteurs if tracking else 0,
                        'entrees': 0,
                        'sorties': 0,
                    }

                if mouv.sens == 'entree':
                    emballages_dict[emb_key]['entrees'] += mouv.quantite
                else:
                    emballages_dict[emb_key]['sorties'] += mouv.quantite

        # Convertir en liste
        data['emballages'] = list(emballages_dict.values())

        return data

    def _prepare_detail_data(self, mouvements):
        """Prépare les données pour le rapport détaillé"""
        data = {
            'emballages_detail': []
        }

        # Grouper par emballage
        emballages_dict = {}
        for mouv in mouvements:
            # CORRECTION : Vérifier que l'emballage existe
            if not mouv.emballage_id:
                _logger.warning(f"Mouvement {mouv.id} sans emballage associé")
                continue

            emb_key = mouv.emballage_id.id
            if emb_key not in emballages_dict:
                tracking = self.env['gecafle.emballage.tracking'].search([
                    ('emballage_id', '=', emb_key)
                ], limit=1)

                emballages_dict[emb_key] = {
                    'emballage': mouv.emballage_id.name,  # Nom string au lieu de l'objet
                    'solde_initial': tracking.stock_initial if tracking else 0,
                    'total_entrees': 0,
                    'total_sorties': 0,
                    'solde_final': 0,
                    'mouvements': []
                }

            # CORRECTION : Formater toutes les données en strings/valeurs simples
            mouvement_data = {
                'date': mouv.date.strftime('%d/%m/%Y %H:%M') if mouv.date else '',
                'reference': mouv.reference or mouv.name or '',
                'type': dict(mouv._fields['type_mouvement'].selection).get(mouv.type_mouvement, ''),
                'client': mouv.client_id.name if mouv.client_id else '',
                'producteur': mouv.producteur_id.name if mouv.producteur_id else '',
                'quantite': mouv.quantite or 0,
                'sens': mouv.sens or '',
                'notes': mouv.notes or '',
            }

            emballages_dict[emb_key]['mouvements'].append(mouvement_data)

            # Calculer les totaux
            if mouv.sens == 'entree':
                emballages_dict[emb_key]['total_entrees'] += mouv.quantite
            else:
                emballages_dict[emb_key]['total_sorties'] += mouv.quantite

        # Calculer les soldes finaux et convertir en liste
        for emb_data in emballages_dict.values():
            emb_data['solde_final'] = (
                    emb_data['solde_initial'] +
                    emb_data['total_entrees'] -
                    emb_data['total_sorties']
            )
            data['emballages_detail'].append(emb_data)

        return data

    # AJOUT : Méthodes pour compatibilité avec les templates existants
    def _get_vente_movements(self):
        """Récupère les mouvements liés aux ventes"""
        domain = [
            ('date', '>=', datetime.combine(self.date_debut, datetime.min.time())),
            ('date', '<=', datetime.combine(self.date_fin, datetime.max.time())),
            ('type_mouvement', 'in', ['sortie_vente', 'retour_client', 'consigne']),
            ('is_cancelled', '=', False),
        ]

        if self.client_id:
            domain.append(('client_id', '=', self.client_id.id))
        elif self.client_ids:
            domain.append(('client_id', 'in', self.client_ids.ids))

        movements = self.env['gecafle.emballage.mouvement'].search(domain, order='date')

        result = []
        for mov in movements:
            result.append({
                'date': mov.date.strftime('%d/%m/%Y') if mov.date else '',
                'reference': mov.reference or mov.name or '',
                'emballage': mov.emballage_id.name if mov.emballage_id else '',
                'qte_sortante': mov.quantite if mov.type_mouvement == 'sortie_vente' else 0,
                'qte_entrante': mov.quantite if mov.type_mouvement in ['retour_client', 'consigne'] else 0,
            })

        return result

    def _get_autres_movements(self):
        """Récupère les autres mouvements"""
        domain = [
            ('date', '>=', datetime.combine(self.date_debut, datetime.min.time())),
            ('date', '<=', datetime.combine(self.date_fin, datetime.max.time())),
            ('type_mouvement', 'not in',
             ['sortie_vente', 'retour_client', 'consigne', 'entree_reception', 'sortie_producteur']),
            ('is_cancelled', '=', False),
        ]

        if self.client_id:
            domain.append(('client_id', '=', self.client_id.id))
        elif self.client_ids:
            domain.append(('client_id', 'in', self.client_ids.ids))

        movements = self.env['gecafle.emballage.mouvement'].search(domain, order='date')

        result = []
        for mov in movements:
            result.append({
                'date': mov.date.strftime('%d/%m/%Y') if mov.date else '',
                'reference': mov.name or '',
                'emballage': mov.emballage_id.name if mov.emballage_id else '',
                'qte_sortante': mov.quantite if mov.sens == 'sortie' else 0,
                'qte_entrante': mov.quantite if mov.sens == 'entree' else 0,
            })

        return result

    def _get_recap_data(self):
        """Récupère les données récapitulatives"""
        domain = self._get_mouvement_domain()
        movements = self.env['gecafle.emballage.mouvement'].search(domain)

        recap = {}
        for mov in movements:
            if not mov.emballage_id:
                continue

            emb_name = mov.emballage_id.name
            if emb_name not in recap:
                recap[emb_name] = {
                    'emballage': emb_name,
                    'sortante': 0,
                    'entrante': 0,
                    'difference': 0,
                }

            if mov.sens == 'sortie':
                recap[emb_name]['sortante'] += mov.quantite
            else:
                recap[emb_name]['entrante'] += mov.quantite

            recap[emb_name]['difference'] = recap[emb_name]['sortante'] - recap[emb_name]['entrante']

        return list(recap.values())
