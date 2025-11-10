# -*- coding: utf-8 -*-
from odoo import models, fields, api


class GecafleAvoirProducteurAutomation(models.Model):
    _inherit = 'gecafle.avoir.producteur'

    # NE PAS OVERRIDE create() ici, car c'est déjà fait dans avoir_producteur_inherit.py
    # On peut ajouter d'autres méthodes spécifiques à l'automatisation si nécessaire

    def action_validate(self):
        """Override pour automatiser si l'avoir client est automatisé"""
        res = super().action_validate()

        # Si créé depuis un avoir client automatisé
        if self.avoir_client_id and hasattr(self.avoir_client_id, 'is_automated') and self.avoir_client_id.is_automated:
            config = self.env.company

            if hasattr(config, 'avoir_auto_validate_producteur') and config.avoir_auto_validate_producteur:
                # Logique d'automatisation supplémentaire si nécessaire
                pass

        return res
