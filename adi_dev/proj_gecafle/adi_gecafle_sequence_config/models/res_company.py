from odoo import models, fields, api
from datetime import datetime


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Configuration séquence Vente
    vente_prefix = fields.Char(
        string='Préfixe Vente',
        default='',
        help="Préfixe pour le numéro de vente (ex: VTE, VENTE, etc.)"
    )
    vente_separator = fields.Selection([
        ('-', 'Tiret (-)'),
        ('/', 'Slash (/)'),
        ('', 'Aucun'),
    ], string='Séparateur Vente', default='/',
       help="Séparateur entre les éléments du numéro")
    vente_year_position = fields.Selection([
        ('none', 'Sans année'),
        ('prefix', 'Année en préfixe (avant numéro)'),
        ('suffix', 'Année en suffixe (après numéro)'),
    ], string='Position année (Vente)', default='prefix',
       help="Position de l'année dans le numéro de vente")
    vente_yearly_reset = fields.Boolean(
        string='Reset annuel (Vente)',
        default=True,
        help="Réinitialiser le compteur de vente à 1 chaque nouvelle année"
    )
    vente_last_reset_year = fields.Integer(
        string='Dernière année reset (Vente)',
        default=lambda self: datetime.now().year,
        help="Année du dernier reset du compteur de vente"
    )

    # Configuration séquence Réception
    reception_prefix = fields.Char(
        string='Préfixe Réception',
        default='',
        help="Préfixe pour le numéro de réception (ex: REC, BR, etc.)"
    )
    reception_separator = fields.Selection([
        ('-', 'Tiret (-)'),
        ('/', 'Slash (/)'),
        ('', 'Aucun'),
    ], string='Séparateur Réception', default='/',
       help="Séparateur entre les éléments du numéro")
    reception_year_position = fields.Selection([
        ('none', 'Sans année'),
        ('prefix', 'Année en préfixe (avant numéro)'),
        ('suffix', 'Année en suffixe (après numéro)'),
    ], string='Position année (Réception)', default='prefix',
       help="Position de l'année dans le numéro de réception")
    reception_yearly_reset = fields.Boolean(
        string='Reset annuel (Réception)',
        default=True,
        help="Réinitialiser le compteur de réception à 1 chaque nouvelle année"
    )
    reception_last_reset_year = fields.Integer(
        string='Dernière année reset (Réception)',
        default=lambda self: datetime.now().year,
        help="Année du dernier reset du compteur de réception"
    )

    def _format_sequence_number(self, counter_value, prefix, separator, year_position):
        """
        Formate un numéro de séquence selon la configuration.

        Args:
            counter_value: La valeur du compteur (ex: '00000001')
            prefix: Le préfixe (ex: 'VTE')
            separator: Le séparateur ('-' ou '/')
            year_position: Position de l'année ('none', 'prefix', 'suffix')

        Returns:
            Le numéro formaté (ex: 'VTE/2026/00000001' ou '00000001/2026')
        """
        parts = []
        year = str(datetime.now().year)
        sep = separator if separator else ''

        # Ajouter le préfixe s'il existe
        if prefix:
            parts.append(prefix)

        # Ajouter l'année en préfixe si demandé
        if year_position == 'prefix':
            parts.append(year)

        # Ajouter le compteur
        parts.append(counter_value)

        # Ajouter l'année en suffixe si demandé
        if year_position == 'suffix':
            parts.append(year)

        return sep.join(parts)

    def _check_yearly_reset(self, counter_field, last_reset_year_field, yearly_reset_field):
        """
        Vérifie si le compteur doit être réinitialisé pour la nouvelle année.

        Args:
            counter_field: Nom du champ compteur (ex: 'vente_counter')
            last_reset_year_field: Nom du champ de dernière année (ex: 'vente_last_reset_year')
            yearly_reset_field: Nom du champ booléen reset annuel (ex: 'vente_yearly_reset')
        """
        self.ensure_one()
        current_year = datetime.now().year
        last_reset_year = getattr(self, last_reset_year_field) or 0
        yearly_reset = getattr(self, yearly_reset_field)

        if yearly_reset and current_year > last_reset_year:
            # Réinitialiser le compteur
            setattr(self, counter_field, '00000001')
            setattr(self, last_reset_year_field, current_year)

    def get_next_vente_number(self):
        """Génère le prochain numéro de vente formaté."""
        self.ensure_one()
        company = self.sudo()

        # Vérifier si reset annuel nécessaire
        company._check_yearly_reset(
            'vente_counter',
            'vente_last_reset_year',
            'vente_yearly_reset'
        )

        # Incrémenter le compteur
        next_counter = company.increment_counter('vente_counter')

        # Formater avec la configuration
        return self._format_sequence_number(
            next_counter,
            self.vente_prefix or '',
            self.vente_separator or '',
            self.vente_year_position or 'none'
        )

    def get_next_reception_number(self):
        """Génère le prochain numéro de réception formaté."""
        self.ensure_one()
        company = self.sudo()

        # Vérifier si reset annuel nécessaire
        company._check_yearly_reset(
            'reception_counter',
            'reception_last_reset_year',
            'reception_yearly_reset'
        )

        # Incrémenter le compteur
        next_counter = company.increment_counter('reception_counter')

        # Formater avec la configuration
        return self._format_sequence_number(
            next_counter,
            self.reception_prefix or '',
            self.reception_separator or '',
            self.reception_year_position or 'none'
        )

    def preview_vente_format(self):
        """Retourne un aperçu du format de vente sans incrémenter."""
        self.ensure_one()
        current_counter = self.vente_counter or '00000001'
        return self._format_sequence_number(
            current_counter,
            self.vente_prefix or '',
            self.vente_separator or '',
            self.vente_year_position or 'none'
        )

    def preview_reception_format(self):
        """Retourne un aperçu du format de réception sans incrémenter."""
        self.ensure_one()
        current_counter = self.reception_counter or '00000001'
        return self._format_sequence_number(
            current_counter,
            self.reception_prefix or '',
            self.reception_separator or '',
            self.reception_year_position or 'none'
        )
