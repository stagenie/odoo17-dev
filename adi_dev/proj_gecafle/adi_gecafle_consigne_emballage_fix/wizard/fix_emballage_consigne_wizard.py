# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FixEmballageConsigneWizard(models.TransientModel):
    """
    Wizard pour détecter et corriger les enregistrements existants
    où le champ est_consigne n'est pas correctement défini sur les
    lignes d'emballage de vente.

    Fonctionnement:
    1. Analyse: Détecte les ventes avec des incohérences
    2. Prévisualisation: Affiche ce qui sera corrigé
    3. Correction: Régénère les lignes d'emballage avec le bon statut
    """
    _name = 'fix.emballage.consigne.wizard'
    _description = 'Assistant de correction des emballages consignés'

    # État du wizard
    state = fields.Selection([
        ('init', 'Initialisation'),
        ('analysis', 'Analyse'),
        ('preview', 'Prévisualisation'),
        ('done', 'Terminé'),
    ], string="État", default='init')

    # Filtres
    date_from = fields.Date(
        string="Date de début",
        help="Filtrer les ventes à partir de cette date"
    )
    date_to = fields.Date(
        string="Date de fin",
        help="Filtrer les ventes jusqu'à cette date"
    )
    vente_ids = fields.Many2many(
        'gecafle.vente',
        string="Ventes spécifiques",
        help="Sélectionner des ventes spécifiques à analyser (optionnel)"
    )

    # Résultats de l'analyse
    total_ventes_analyzed = fields.Integer(
        string="Ventes analysées",
        readonly=True
    )
    total_ventes_to_fix = fields.Integer(
        string="Ventes à corriger",
        readonly=True
    )
    total_lines_to_fix = fields.Integer(
        string="Lignes à corriger",
        readonly=True
    )

    # Lignes de prévisualisation
    preview_line_ids = fields.One2many(
        'fix.emballage.consigne.wizard.line',
        'wizard_id',
        string="Corrections à effectuer"
    )

    # Résumé
    analysis_summary = fields.Text(
        string="Résumé de l'analyse",
        readonly=True
    )

    # Résultats finaux
    fix_result = fields.Text(
        string="Résultat de la correction",
        readonly=True
    )

    def action_analyze(self):
        """
        Analyse les ventes pour détecter les incohérences entre:
        - Le comportement forcé sur les lignes de vente (force_comportement_emballage)
        - Le champ est_consigne sur les lignes d'emballage
        """
        self.ensure_one()

        # Réinitialiser
        self.preview_line_ids.unlink()

        # Construire le domaine de recherche
        domain = [('state', '=', 'valide')]

        if self.vente_ids:
            domain.append(('id', 'in', self.vente_ids.ids))
        else:
            if self.date_from:
                domain.append(('date_vente', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_vente', '<=', self.date_to))

        # Rechercher les ventes
        ventes = self.env['gecafle.vente'].search(domain)
        self.total_ventes_analyzed = len(ventes)

        ventes_to_fix = []
        lines_to_create = []
        issues_found = []

        for vente in ventes:
            vente_issues = self._analyze_vente(vente)
            if vente_issues:
                ventes_to_fix.append(vente)
                for issue in vente_issues:
                    lines_to_create.append({
                        'wizard_id': self.id,
                        'vente_id': vente.id,
                        'emballage_id': issue['emballage_id'],
                        'current_est_consigne': issue['current'],
                        'expected_est_consigne': issue['expected'],
                        'qte_sortantes': issue['qte'],
                        'issue_type': issue['type'],
                        'issue_description': issue['description'],
                    })
                issues_found.extend(vente_issues)

        # Créer les lignes de prévisualisation
        for line_vals in lines_to_create:
            self.env['fix.emballage.consigne.wizard.line'].create(line_vals)

        self.total_ventes_to_fix = len(ventes_to_fix)
        self.total_lines_to_fix = len(lines_to_create)

        # Générer le résumé
        summary_lines = [
            f"Analyse terminée",
            f"=" * 40,
            f"Ventes analysées: {self.total_ventes_analyzed}",
            f"Ventes avec problèmes: {self.total_ventes_to_fix}",
            f"Lignes à corriger: {self.total_lines_to_fix}",
            "",
        ]

        if self.total_ventes_to_fix > 0:
            summary_lines.append("Types de problèmes détectés:")
            issue_types = {}
            for issue in issues_found:
                issue_type = issue['type']
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            for itype, count in issue_types.items():
                summary_lines.append(f"  - {itype}: {count}")
        else:
            summary_lines.append("Aucun problème détecté. Toutes les ventes sont cohérentes.")

        self.analysis_summary = "\n".join(summary_lines)
        self.state = 'preview'

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _analyze_vente(self, vente):
        """
        Analyse une vente et retourne la liste des problèmes détectés.

        Vérifie:
        1. Les lignes d'emballage ont-elles le bon est_consigne?
        2. Y a-t-il des lignes de vente R et NR pour le même emballage
           qui devraient être séparées?
        """
        issues = []

        # Construire un dictionnaire des attentes depuis les lignes de vente
        # Clé: (emballage_id, est_consigne), Valeur: qté
        expected = {}
        for line in vente.detail_vente_ids:
            if line.type_colis_id and line.nombre_colis > 0:
                est_consigne = line.est_consigne if hasattr(line, 'est_consigne') else False
                key = (line.type_colis_id.id, est_consigne)
                expected[key] = expected.get(key, 0) + line.nombre_colis

        # Construire un dictionnaire de l'existant depuis les lignes d'emballage
        # Clé: (emballage_id, est_consigne), Valeur: qté
        actual = {}
        for emb_line in vente.detail_emballage_vente_ids:
            key = (emb_line.emballage_id.id, emb_line.est_consigne)
            actual[key] = actual.get(key, 0) + emb_line.qte_sortantes

        # Comparer et détecter les différences
        all_keys = set(expected.keys()) | set(actual.keys())

        for key in all_keys:
            emballage_id, est_consigne = key
            expected_qty = expected.get(key, 0)
            actual_qty = actual.get(key, 0)

            emballage = self.env['gecafle.emballage'].browse(emballage_id)
            type_str = "R (Consigné)" if est_consigne else "NR (Non Rendu)"

            if expected_qty > 0 and actual_qty == 0:
                # Ligne attendue mais inexistante
                issues.append({
                    'emballage_id': emballage_id,
                    'current': None,
                    'expected': est_consigne,
                    'qte': expected_qty,
                    'type': 'missing_line',
                    'description': f"Ligne manquante: {emballage.name} {type_str} ({expected_qty} colis)",
                })
            elif expected_qty == 0 and actual_qty > 0:
                # Ligne existante mais non attendue
                issues.append({
                    'emballage_id': emballage_id,
                    'current': est_consigne,
                    'expected': None,
                    'qte': actual_qty,
                    'type': 'extra_line',
                    'description': f"Ligne en trop: {emballage.name} {type_str} ({actual_qty} colis)",
                })
            elif expected_qty != actual_qty:
                # Quantité incorrecte
                issues.append({
                    'emballage_id': emballage_id,
                    'current': est_consigne,
                    'expected': est_consigne,
                    'qte': expected_qty,
                    'type': 'wrong_qty',
                    'description': f"Qté incorrecte: {emballage.name} {type_str} (actuel: {actual_qty}, attendu: {expected_qty})",
                })

        # Cas spécial: vérifier si est_consigne n'est pas défini (ancien format)
        for emb_line in vente.detail_emballage_vente_ids:
            # Vérifier si la valeur par défaut (False) correspond bien à l'attente
            if not emb_line.est_consigne:
                # Vérifier s'il devrait être True
                for line in vente.detail_vente_ids:
                    if (line.type_colis_id.id == emb_line.emballage_id.id and
                            hasattr(line, 'est_consigne') and line.est_consigne):
                        # Il y a au moins une ligne de vente avec cet emballage qui est consignée
                        # mais la ligne d'emballage n'a pas est_consigne = True
                        if (emb_line.emballage_id.id, True) not in actual:
                            issues.append({
                                'emballage_id': emb_line.emballage_id.id,
                                'current': False,
                                'expected': True,
                                'qte': emb_line.qte_sortantes,
                                'type': 'wrong_consigne_status',
                                'description': f"Statut incorrect: {emb_line.emballage_id.name} devrait être R mais est NR",
                            })
                        break

        return issues

    def action_fix(self):
        """
        Applique les corrections en régénérant les lignes d'emballage
        pour les ventes concernées.
        """
        self.ensure_one()

        if self.state != 'preview':
            raise UserError(_("Veuillez d'abord lancer l'analyse."))

        if self.total_ventes_to_fix == 0:
            raise UserError(_("Aucune vente à corriger."))

        # Récupérer les ventes uniques à corriger
        vente_ids = self.preview_line_ids.mapped('vente_id').ids
        ventes = self.env['gecafle.vente'].browse(vente_ids)

        fixed_count = 0
        errors = []

        for vente in ventes:
            try:
                # Régénérer les lignes d'emballage avec la nouvelle logique
                vente.generate_emballage_lines()
                fixed_count += 1
            except Exception as e:
                errors.append(f"Vente {vente.name}: {str(e)}")

        # Générer le rapport
        result_lines = [
            "Correction terminée",
            "=" * 40,
            f"Ventes corrigées avec succès: {fixed_count}",
            f"Erreurs: {len(errors)}",
        ]

        if errors:
            result_lines.append("")
            result_lines.append("Détail des erreurs:")
            for error in errors:
                result_lines.append(f"  - {error}")

        self.fix_result = "\n".join(result_lines)
        self.state = 'done'

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_back_to_init(self):
        """Retour à l'état initial pour relancer une analyse"""
        self.state = 'init'
        self.preview_line_ids.unlink()
        self.analysis_summary = False
        self.fix_result = False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class FixEmballageConsigneWizardLine(models.TransientModel):
    """Ligne de prévisualisation des corrections"""
    _name = 'fix.emballage.consigne.wizard.line'
    _description = 'Ligne de correction emballage consigne'

    wizard_id = fields.Many2one(
        'fix.emballage.consigne.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade'
    )
    vente_id = fields.Many2one(
        'gecafle.vente',
        string="Vente",
        required=True
    )
    vente_name = fields.Char(
        string="N° Vente",
        related='vente_id.name'
    )
    vente_date = fields.Datetime(
        string="Date",
        related='vente_id.date_vente'
    )
    emballage_id = fields.Many2one(
        'gecafle.emballage',
        string="Emballage"
    )
    current_est_consigne = fields.Boolean(
        string="Actuel"
    )
    expected_est_consigne = fields.Boolean(
        string="Attendu"
    )
    qte_sortantes = fields.Integer(
        string="Quantité"
    )
    issue_type = fields.Selection([
        ('missing_line', 'Ligne manquante'),
        ('extra_line', 'Ligne en trop'),
        ('wrong_qty', 'Quantité incorrecte'),
        ('wrong_consigne_status', 'Statut R/NR incorrect'),
    ], string="Type de problème")
    issue_description = fields.Char(
        string="Description"
    )
