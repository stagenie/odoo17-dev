    def action_create_vendor_invoice(self):
        """Crée une facture fournisseur détaillée à partir du récapitulatif"""
        self.ensure_one()

        # Vérifier que le récapitulatif est validé
        if self.state != 'valide':
            raise UserError(_("Le récapitulatif doit être validé avant de créer une facture."))

        # Vérifier qu'il n'existe pas déjà une facture
        if self.invoice_count > 0:
            raise UserError(_("Une facture existe déjà pour ce récapitulatif."))

        # Rechercher le compte fournisseur pour ce producteur
        vendor = self.env['res.partner'].search([
            ('name', '=', self.producteur_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        # Si le fournisseur n'existe pas, le créer
        if not vendor:
            vendor = self.env['res.partner'].create({
                'name': self.producteur_id.name,
                'phone': self.producteur_id.phone,
                'supplier_rank': 1,
                'is_company': False,
            })

        # Récupérer le montant de l'avance depuis la réception
        montant_avance = self.reception_id.avance_producteur if hasattr(self.reception_id, 'avance_producteur') else 0.0

        # Calculer le net à payer après déduction de l'avance
        net_a_payer_final = self.net_a_payer - montant_avance

        # Préparer la description de la facture avec mention de l'avance
        narration_text = _("Facture créée depuis le récapitulatif %s\n"
                           "Total ventes: %s\n"
                           "Commission: %s\n"
                           "Net avant avance: %s") % (
                             self.name,
                             self.total_ventes,
                             self.total_commission,
                             self.net_a_payer
                         )

        if montant_avance > 0:
            narration_text += _("\nAvance déduite: %s\n"
                                "Net à payer final: %s") % (
                                  montant_avance,
                                  net_a_payer_final
                              )

        # Créer la facture fournisseur avec la référence au récap
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': _("Bordereau N° %s - Folio %s") % (self.name, self.reception_id.name),
            'ref': _("Bordereau N° %s") % self.name,
            'recap_id': self.id,  # Lien vers le récapitulatif
            'narration': narration_text,
            'invoice_line_ids': [],
        }

        # Ligne 1 : Montant total des ventes
        invoice_line_vals = {
            'name': _("Vente de produits agricoles - Bordereau N° %s") % self.name,
            'quantity': 1,
            'price_unit': self.total_ventes,
        }
        invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        # Ligne 2 : Déduction pour la commission
        commission_line_vals = {
            'name': _("Commission sur ventes - Bordereau N° %s") % self.name,
            'quantity': 1,
            'price_unit': -self.total_commission,  # Négatif pour déduire
        }
        invoice_vals['invoice_line_ids'].append((0, 0, commission_line_vals))

        # Ligne 3 : Déduction pour l'avance (si elle existe)
        if montant_avance > 0:
            avance_line_vals = {
                'name': _("Avance versée lors de la réception - Folio N° %s") % self.reception_id.name,
                'quantity': 1,
                'price_unit': -montant_avance,  # Négatif pour déduire
            }
            invoice_vals['invoice_line_ids'].append((0, 0, avance_line_vals))

        # Créer la facture
        invoice = self.env['account.move'].create(invoice_vals)

        # Lier la facture au récapitulatif
        self.invoice_id = invoice.id
        self.state = 'facture'

        # Message de confirmation avec détails
        message_body = _("Facture fournisseur créée avec succès.\n\n"
                         "Détails:\n"
                         "- Total ventes: %s\n"
                         "- Commission: %s\n") % (
                           self.total_ventes,
                           self.total_commission
                       )

        if montant_avance > 0:
            message_body += _("- Avance déduite: %s\n") % montant_avance

        message_body += _("- Net à payer: %s") % net_a_payer_final

        self.message_post(body=message_body)

        # Ouvrir la facture créée
        return {
            'name': _('Facture Fournisseur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'target': 'current',
        }



    def ex_action_create_vendor_invoice(self):
        """Crée une facture fournisseur détaillée à partir du récapitulatif"""
        self.ensure_one()

        # Vérifier que le récapitulatif est validé
        if self.state != 'valide':
            raise UserError(_("Le récapitulatif doit être validé avant de créer une facture."))

        # Vérifier qu'il n'existe pas déjà une facture
        if self.invoice_count > 0:
            raise UserError(_("Une facture existe déjà pour ce récapitulatif."))

        # Rechercher le compte fournisseur pour ce producteur
        vendor = self.env['res.partner'].search([
            ('name', '=', self.producteur_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        # Si le fournisseur n'existe pas, le créer
        if not vendor:
            vendor = self.env['res.partner'].create({
                'name': self.producteur_id.name,
                'phone': self.producteur_id.phone,
                'supplier_rank': 1,
                'is_company': False,
            })

        # Créer la facture fournisseur avec la référence au récap
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': _("Bordereau N° %s - Folio %s") % (self.name, self.reception_id.name),
            'ref': _("Bordereau N° %s") % self.name,
            'recap_id': self.id,  # Lien vers le récapitulatif
            'narration': _("Facture créée depuis le récapitulatif %s\nTotal ventes: %s\nCommission: %s\nNet à payer: %s") % (
                self.name,
                self.total_ventes,
                self.total_commission,
                self.net_a_payer
            ),
            'invoice_line_ids': [],
        }

        # Option 1: Une seule ligne pour le montant total des ventes
        invoice_line_vals = {
            'name': _("Vente de produits agricoles - Bordereau N° %s") % self.name,
            'quantity': 1,
            'price_unit': self.total_ventes,
        }
        invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        # Ligne de déduction pour la commission
        commission_line_vals = {
            'name': _("Commission sur ventes - Bordereau N° %s") % self.name,
            'quantity': 1,
            'price_unit': -self.total_commission,  # Négatif pour déduire
        }
        invoice_vals['invoice_line_ids'].append((0, 0, commission_line_vals))

        # Créer la facture
        invoice = self.env['account.move'].create(invoice_vals)

        # Lier la facture au récapitulatif
        self.invoice_id = invoice.id
        self.state = 'facture'

        # Ouvrir la facture créée
        return {
            'name': _('Facture Fournisseur'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'target': 'current',
        }
