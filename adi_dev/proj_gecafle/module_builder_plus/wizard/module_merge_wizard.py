# -*- coding: utf-8 -*-
import base64
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import html2text


class ModuleMergeWizard(models.TransientModel):
    _name = 'module.merge.wizard'
    _description = 'Assistant de fusion de modules'

    # Sélection des modules à fusionner
    module_ids = fields.Many2many(
        'module.content.plus',
        string='Modules à fusionner',
        required=True,
        help="Sélectionnez les modules à fusionner en un seul fichier"
    )

    # Options de fusion
    merge_name = fields.Char(
        'Nom du fichier fusionné',
        compute='_compute_merge_name',
        store=True,
        help="Nom du fichier résultant de la fusion"
    )

    include_separator = fields.Boolean(
        'Inclure des séparateurs',
        default=True,
        help="Ajouter des séparateurs entre chaque module"
    )

    separator_style = fields.Selection([
        ('simple', '═══════════════'),
        ('detailed', '╔═══ MODULE: {name} ═══╗'),
        ('markdown', '# MODULE: {name}\n---'),
    ], string='Style de séparateur', default='detailed')

    # Prévisualisation et résultat
    preview_content = fields.Text(
        'Aperçu du contenu',
        readonly=True,
        help="Aperçu du contenu fusionné"
    )

    merged_content = fields.Text(
        'Contenu fusionné',
        readonly=True
    )

    state = fields.Selection([
        ('select', 'Sélection'),
        ('preview', 'Aperçu'),
        ('done', 'Terminé')
    ], default='select', string='État')

    @api.depends('module_ids')
    def _compute_merge_name(self):
        """Génère automatiquement un nom pour le fichier fusionné"""
        for record in self:
            if record.module_ids:
                # Créer un nom basé sur les modules sélectionnés
                module_names = record.module_ids.mapped('name')
                if len(module_names) <= 3:
                    base_name = '_'.join(module_names)
                else:
                    base_name = f"{module_names[0]}_{module_names[1]}_et_{len(module_names) - 2}_autres"

                # Ajouter timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                record.merge_name = f"merged_{base_name}_{timestamp}.txt"
            else:
                record.merge_name = f"merged_modules_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"

    def action_preview(self):
        """Génère un aperçu du contenu fusionné"""
        self.ensure_one()

        if not self.module_ids:
            raise UserError(_("Veuillez sélectionner au moins un module à fusionner."))

        # Générer le contenu fusionné
        merged_content = self._generate_merged_content()

        # Limiter l'aperçu à 5000 caractères
        preview = merged_content[:5000]
        if len(merged_content) > 5000:
            preview += "\n\n... [Contenu tronqué pour l'aperçu] ..."

        self.write({
            'preview_content': preview,
            'merged_content': merged_content,
            'state': 'preview'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _generate_merged_content(self):
        """Génère le contenu fusionné de tous les modules sélectionnés"""
        content_parts = []
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0  # Pas de limite de largeur

        # En-tête du fichier
        content_parts.append(self._generate_header())

        # Traiter chaque module
        for index, module in enumerate(self.module_ids, 1):
            # Ajouter le séparateur si demandé
            if self.include_separator:
                separator = self._generate_separator(module.name, index)
                content_parts.append(separator)

            # Convertir le contenu HTML en texte
            if module.processed_content:
                text_content = h.handle(module.processed_content)
                content_parts.append(text_content)
            else:
                # Si pas de contenu traité, essayer d'importer d'abord
                content_parts.append(
                    f"\n[Module {module.name}: Aucun contenu traité disponible. Veuillez traiter le fichier d'abord.]\n")

            # Ajouter un espace entre les modules
            content_parts.append("\n\n")

        # Ajouter le pied de page
        content_parts.append(self._generate_footer())

        return '\n'.join(content_parts)

    def _generate_header(self):
        """Génère l'en-tête du fichier fusionné"""
        header = []
        header.append("=" * 80)
        header.append("FUSION DE MODULES ODOO")
        header.append("=" * 80)
        header.append(f"Date de génération: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        header.append(f"Nombre de modules: {len(self.module_ids)}")
        header.append(f"Modules inclus: {', '.join(self.module_ids.mapped('name'))}")
        header.append("=" * 80)
        header.append("\n")
        return '\n'.join(header)

    def _generate_separator(self, module_name, index):
        """Génère un séparateur selon le style choisi"""
        if self.separator_style == 'simple':
            return f"\n{'═' * 80}\n"
        elif self.separator_style == 'detailed':
            separator_length = 80
            title = f" MODULE {index}: {module_name} "
            padding_length = (separator_length - len(title)) // 2
            return f"\n{'╔' + '═' * padding_length}{title}{'═' * padding_length + '╗'}\n"
        elif self.separator_style == 'markdown':
            return f"\n# MODULE {index}: {module_name}\n{'---' * 20}\n"
        return "\n"

    def _generate_footer(self):
        """Génère le pied de page du fichier fusionné"""
        footer = []
        footer.append("\n")
        footer.append("=" * 80)
        footer.append("FIN DE LA FUSION")
        footer.append("=" * 80)
        footer.append(f"Généré par Module Builder Plus - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return '\n'.join(footer)

    def action_merge_and_download(self):
        """Fusionne les modules et propose le téléchargement"""
        self.ensure_one()

        # S'assurer qu'on a le contenu fusionné
        if not self.merged_content:
            self.action_preview()

        # Créer l'attachement
        attachment = self.env['ir.attachment'].create({
            'name': self.merge_name,
            'datas': base64.b64encode(self.merged_content.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'text/plain',
        })

        self.state = 'done'

        # Retourner l'action de téléchargement
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_merge_specific_types(self):
        """Action pour fusionner seulement certains types de fichiers"""
        self.ensure_one()

        # Créer un wizard pour choisir les types
        return {
            'name': 'Choisir les types de fichiers',
            'type': 'ir.actions.act_window',
            'res_model': 'module.merge.type.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_merge_wizard_id': self.id,
                'default_module_ids': [(6, 0, self.module_ids.ids)]
            }
        }
