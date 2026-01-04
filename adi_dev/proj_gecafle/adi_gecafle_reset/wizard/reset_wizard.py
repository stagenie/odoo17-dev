from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import logging

_logger = logging.getLogger(__name__)


class GecafleResetWizard(models.TransientModel):
    _name = 'gecafle.reset.wizard'
    _description = 'Assistant de réinitialisation des données GECAFLE'

    confirmation_text = fields.Char(
        string='Confirmation',
        help="Tapez 'RESET GECAFLE' pour confirmer la suppression"
    )

    reset_ventes = fields.Boolean(
        string='Réinitialiser les Ventes',
        default=True,
        help="Supprime toutes les ventes et documents associés"
    )
    reset_receptions = fields.Boolean(
        string='Réinitialiser les Réceptions',
        default=True,
        help="Supprime toutes les réceptions et documents associés"
    )
    reset_emballages = fields.Boolean(
        string='Réinitialiser les Emballages',
        default=True,
        help="Supprime tous les mouvements et suivis d'emballages"
    )
    reset_avoirs = fields.Boolean(
        string='Réinitialiser les Avoirs',
        default=True,
        help="Supprime tous les avoirs clients et producteurs"
    )
    reset_bordereaux = fields.Boolean(
        string='Réinitialiser les Bordereaux',
        default=True,
        help="Supprime tous les bordereaux récapitulatifs"
    )
    reset_statistiques = fields.Boolean(
        string='Réinitialiser les Statistiques',
        default=True,
        help="Supprime tous les relevés et traçabilités"
    )
    reset_comptabilite = fields.Boolean(
        string='Réinitialiser Comptabilité',
        default=True,
        help="Supprime toutes les factures, avoirs et paiements"
    )
    reset_tresorerie = fields.Boolean(
        string='Réinitialiser Trésorerie',
        default=True,
        help="Supprime toutes les opérations de caisse, coffre, transferts et clôtures"
    )
    reset_counters = fields.Boolean(
        string='Réinitialiser les Compteurs',
        default=True,
        help="Remet tous les compteurs de séquences à 00000001"
    )
    reset_rh = fields.Boolean(
        string='Réinitialiser RH/Paie',
        default=True,
        help="Supprime pointages, acomptes, prêts et fiches de paie"
    )

    # Champs informatifs
    info_ventes = fields.Integer(string='Ventes', compute='_compute_counts')
    info_receptions = fields.Integer(string='Réceptions', compute='_compute_counts')
    info_emballages = fields.Integer(string='Mouvements emballages', compute='_compute_counts')
    info_factures = fields.Integer(string='Factures/Avoirs', compute='_compute_counts')
    info_paiements = fields.Integer(string='Paiements', compute='_compute_counts')
    info_tresorerie = fields.Integer(string='Opérations trésorerie', compute='_compute_counts')
    info_rh = fields.Integer(string='Opérations RH/Paie', compute='_compute_counts')

    @api.depends('reset_ventes', 'reset_receptions', 'reset_comptabilite', 'reset_emballages', 'reset_tresorerie')
    def _compute_counts(self):
        for record in self:
            record.info_ventes = self._safe_count('gecafle.vente')
            record.info_receptions = self._safe_count('gecafle.reception')
            record.info_emballages = self._safe_count('gecafle.emballage.mouvement')
            record.info_factures = self._safe_count('account.move', [('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund'])])
            record.info_paiements = self._safe_count('account.payment')
            record.info_tresorerie = (
                self._safe_count('treasury.cash.operation') +
                self._safe_count('treasury.safe.operation') +
                self._safe_count('treasury.transfer') +
                self._safe_count('treasury.cash.closing')
            )
            record.info_rh = (
                self._safe_count('attendance.daily') +
                self._safe_count('employee.advance') +
                self._safe_count('employee.loan') +
                self._safe_count('payroll.slip')
            )

    def _safe_count(self, model_name, domain=None):
        """Compte les enregistrements d'un modèle de manière sécurisée."""
        try:
            model = self.env.get(model_name)
            if model is None:
                return 0
            return model.sudo().search_count(domain or [])
        except Exception:
            return 0

    def _check_admin_access(self):
        """Vérifie que l'utilisateur est administrateur système."""
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Seuls les administrateurs système peuvent effectuer cette opération."))

    def _get_tables_to_purge(self):
        """
        Retourne la liste des tables à purger dans l'ordre correct.
        IMPORTANT: Les tables enfants DOIVENT être avant les tables parents.
        """
        tables = []

        # COMPTABILITÉ - Ordre critique: réconciliations → lignes → paiements → écritures
        if self.reset_comptabilite:
            tables.extend([
                'account_partial_reconcile',
                'account_full_reconcile',
                'account_payment',
                'account_move_line',
                'account_move',
            ])

        # TRÉSORERIE - Ordre: transferts (référencent cash_operation) → lignes clôture → clôtures → opérations
        if self.reset_tresorerie:
            tables.extend([
                'treasury_transfer',  # Doit être supprimé EN PREMIER (référence cash_operation)
                'treasury_cash_closing_line',
                'treasury_cash_closing',
                'treasury_cash_operation',
                'treasury_safe_operation',
            ])

        # RH / PAIE - Ordre: lignes paie → fiches → batches → périodes | échéances → prêts | acomptes | lignes pointage → pointages
        if self.reset_rh:
            tables.extend([
                'payroll_line',
                'payroll_slip',
                'payroll_batch',
                'payroll_period',
                'loan_installment',
                'employee_loan',
                'employee_advance',
                'attendance_daily_line',
                'attendance_daily',
            ])

        # STATISTIQUES
        if self.reset_statistiques:
            tables.extend([
                'gecafle_tracabilite_vente_line',
                'gecafle_tracabilite_reception_line',
                'gecafle_tracabilite_produits',
                'gecafle_releve_vente_detail',
                'gecafle_releve_reception_detail',
                'gecafle_releve_reception_ventes_line',
                'gecafle_releve_reception_ventes',
                'gecafle_statistiques_ventes',
            ])

        # BORDEREAUX
        if self.reset_bordereaux:
            tables.extend([
                'gecafle_reception_recap_sale',
                'gecafle_reception_recap_original',
                'gecafle_reception_recap_line',
                'gecafle_reception_recap',
            ])

        # AVOIRS GECAFLE
        if self.reset_avoirs:
            tables.extend([
                'gecafle_avoir_producteur',
                'gecafle_avoir_client',
            ])

        # EMBALLAGES - Ordre: mouvements (réf tracking) → balances → tracking → consignes
        if self.reset_emballages:
            tables.extend([
                'gecafle_emballage_mouvement',  # Doit être EN PREMIER (référence tracking)
                'gecafle_emballage_balance_client',
                'gecafle_emballage_balance_producteur',
                'gecafle_emballage_tracking',
                'gecafle_consigne_retour_line',
                'gecafle_consigne_retour',
            ])

        # VENTES - Ordre: détails emballage client → emballage client → détails vente → ventes
        if self.reset_ventes:
            tables.extend([
                'gecafle_bon_achat_line',
                'gecafle_bon_achat',
                'gecafle_emballage_client_details_operations',
                'gecafle_emballage_client',
                'gecafle_details_emballage_vente',
                'gecafle_details_ventes',
                'gecafle_vente',
            ])

        # RÉCEPTIONS - Ordre: destockage → stock → détails emballage → emballage → détails → réceptions
        if self.reset_receptions:
            tables.extend([
                'gecafle_destockage',
                'gecafle_stock',
                'gecafle_emballage_producteur_details_operations',
                'gecafle_emballage_producteur',
                'gecafle_details_emballage_reception',
                'gecafle_details_reception',
                'gecafle_reception',
            ])

        return tables

    def _table_exists(self, table_name):
        """Vérifie si une table existe (pas une vue)."""
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
                AND table_type = 'BASE TABLE'
            )
        """, (table_name,))
        return self.env.cr.fetchone()[0]

    def _is_view(self, table_name):
        """Vérifie si c'est une vue SQL."""
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views
                WHERE table_schema = 'public' AND table_name = %s
            )
        """, (table_name,))
        return self.env.cr.fetchone()[0]

    def _reset_counters(self):
        """Réinitialise tous les compteurs."""
        company = self.env.company.sudo()

        # Compteurs dans res.company
        counter_fields = [
            'reception_counter', 'vente_counter',
            'reglement_client_counter', 'reglement_producteur_counter',
            'versement_producteur_counter', 'emballage_producteur_counter',
            'emballage_client_counter', 'versement_client_counter',
        ]
        for field in counter_fields:
            if hasattr(company, field):
                setattr(company, field, '00000001')

        # Années de reset
        from datetime import datetime
        current_year = datetime.now().year
        for field in ['vente_last_reset_year', 'reception_last_reset_year']:
            if hasattr(company, field):
                setattr(company, field, current_year)

        # Séquences ir.sequence
        sequences = self.env['ir.sequence'].sudo().search([
            '|', '|', '|',
            ('code', 'like', 'gecafle.%'),
            ('code', 'like', 'treasury.%'),
            ('code', 'like', 'payroll.%'),
            ('code', 'like', 'employee.%'),
        ])
        sequences.write({'number_next': 1})

        _logger.info("Tous les compteurs réinitialisés")

    def _reset_treasury_balances(self):
        """Réinitialise les soldes de caisse et coffre à zéro via SQL direct."""
        # Reset des caisses (last_closing_balance + current_balance)
        if self._table_exists('treasury_cash'):
            self.env.cr.execute("UPDATE treasury_cash SET last_closing_balance = 0, current_balance = 0")
            _logger.info("Soldes des caisses réinitialisés à zéro")

        # Reset des coffres (current_balance)
        if self._table_exists('treasury_safe'):
            self.env.cr.execute("UPDATE treasury_safe SET current_balance = 0")
            _logger.info("Soldes des coffres réinitialisés à zéro")

    def action_reset(self):
        """Action principale - TRANSACTION ATOMIQUE."""
        self.ensure_one()
        self._check_admin_access()

        if self.confirmation_text != 'RESET GECAFLE':
            raise UserError(_("Pour confirmer, tapez exactement : RESET GECAFLE"))

        if not any([
            self.reset_ventes, self.reset_receptions, self.reset_emballages,
            self.reset_avoirs, self.reset_bordereaux, self.reset_statistiques,
            self.reset_comptabilite, self.reset_tresorerie, self.reset_counters,
            self.reset_rh
        ]):
            raise UserError(_("Sélectionnez au moins une option."))

        _logger.info("=" * 60)
        _logger.info("RESET GECAFLE - DÉBUT")
        _logger.info(f"Utilisateur: {self.env.user.name}")
        _logger.info("=" * 60)

        tables_to_purge = self._get_tables_to_purge()
        total_deleted = 0
        tables_purged = []

        # TRANSACTION ATOMIQUE - Tout ou rien
        try:
            for table_name in tables_to_purge:
                # Ignorer les vues SQL (elles se vident automatiquement)
                if self._is_view(table_name):
                    _logger.info(f"Vue SQL {table_name} - ignorée (sera vide automatiquement)")
                    continue

                if not self._table_exists(table_name):
                    _logger.info(f"Table {table_name} n'existe pas - ignorée")
                    continue

                # Compter avant suppression
                self.env.cr.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = self.env.cr.fetchone()[0]

                if count > 0:
                    # Supprimer
                    self.env.cr.execute(f'DELETE FROM "{table_name}"')
                    total_deleted += count
                    tables_purged.append(f"{table_name}: {count}")
                    _logger.info(f"Purgé {count} de {table_name}")

            # Réinitialiser les compteurs
            if self.reset_counters:
                self._reset_counters()

            # Réinitialiser les soldes de trésorerie à zéro
            if self.reset_tresorerie:
                self._reset_treasury_balances()

            # Si on arrive ici, tout est OK - la transaction sera commitée automatiquement
            _logger.info("=" * 60)
            _logger.info(f"RESET GECAFLE - SUCCÈS - {total_deleted} enregistrements supprimés")
            _logger.info("=" * 60)

        except Exception as e:
            # En cas d'erreur, Odoo fera automatiquement un rollback
            _logger.error(f"RESET GECAFLE - ÉCHEC: {str(e)}")
            _logger.error("Rollback automatique - Aucune donnée n'a été supprimée")
            raise UserError(_(
                "Erreur lors de la réinitialisation.\n\n"
                "AUCUNE DONNÉE N'A ÉTÉ SUPPRIMÉE (rollback automatique).\n\n"
                "Détail: %s"
            ) % str(e))

        # Message de succès
        message = _("Réinitialisation réussie !\n\nTotal supprimé : %s enregistrements") % total_deleted

        if self.reset_counters:
            message += _("\n\nCompteurs réinitialisés à 00000001")

        if self.reset_tresorerie:
            message += _("\n\nSoldes caisse/coffre remis à zéro")

        if tables_purged:
            message += _("\n\nDétail:\n") + "\n".join(tables_purged[:10])
            if len(tables_purged) > 10:
                message += f"\n... et {len(tables_purged) - 10} autres tables"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reset GECAFLE - Succès'),
                'message': message,
                'type': 'success',
                'sticky': True,
            }
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
