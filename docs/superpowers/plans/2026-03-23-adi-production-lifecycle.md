# ADI Production Lifecycle - Module d'annulation et contrôle du cycle de vie

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nouveau module `adi_production_lifecycle` qui hérite de `adi_simple_production_cost` pour gérer proprement l'annulation, la remise en brouillon, le verrouillage des champs selon l'état, et l'annulation en cascade de tous les documents générés (pickings, achats, factures).

**Architecture:** Module Odoo 17 héritage (`_inherit = 'ron.daily.production'`) qui surcharge `action_reset_draft`, ajoute un état `cancelled`, un wizard d'annulation avec motif obligatoire, et des méthodes d'annulation en cascade pour les pickings (retours), achats et factures. Verrouillage des champs via `readonly` conditionnel sur les états non-draft.

**Tech Stack:** Odoo 17, Python 3.10+, XML (vues héritées), module stock (retours via `stock.return.picking`), module purchase, module account.

---

## Analyse des cas d'annulation

### Cas 1 : Remise en brouillon depuis `confirmed`
- Aucun document n'a encore été généré
- Simple reset d'état, motif optionnel
- Les données restent éditables

### Cas 2 : Remise en brouillon depuis `validated` (documents NON auto-validés)
- Les documents existent mais sont en brouillon/draft
- **Pickings (BL)** : état `draft` ou `confirmed` → annuler (`action_cancel`)
- **Achats (PO)** : état `draft` ou `sent` → annuler (`button_cancel`)
- Supprimer les liens (remettre les Many2one à False)

### Cas 3 : Remise en brouillon depuis `validated` (documents auto-validés = `done`)
- **Pickings (BL consommation)** : état `done` → créer un retour (`stock.return.picking`) pour inverser le mouvement de stock
- **Achats (PO)** : état `purchase` → annuler les pickings de réception d'abord, puis annuler le PO
- **Réceptions (pickings des PO)** : état `done` → créer des retours
- **Factures fournisseur** : état `draft` → annuler ; état `posted` → créer un avoir (credit note)
- **Impact AVCO** : les retours de stock inversent automatiquement la valorisation AVCO dans Odoo

### Cas 4 : Annulation depuis `done`
- Même que cas 3 mais depuis état terminé
- Doit passer en état `cancelled` (pas en `draft`)
- Motif obligatoire

### Cas 5 : Modification en état non-draft
- **Problème actuel** : les lignes de consommation, rebuts, produits finis sont éditables même en état `validated` ou `done`
- **Solution** : verrouillage des One2many via `readonly` conditionnel dans les vues héritées

### Cas 6 : Documents partiellement validés
- Certains pickings `done`, d'autres `confirmed`
- Traitement différentiel selon l'état de chaque document

### Cas 7 : Factures déjà réconciliées/payées
- Bloquer l'annulation si une facture est payée (état `in_payment` ou `paid`)
- Proposer de créer un avoir à la place

---

## Structure des fichiers

```
adi_dev/adi_dev2/adi_production_lifecycle/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── ron_daily_production.py      # _inherit avec surcharges
├── wizard/
│   ├── __init__.py
│   └── cancel_production_wizard.py  # Wizard d'annulation avec motif
├── views/
│   ├── ron_daily_production_views.xml  # Héritage vues (boutons, readonly)
│   └── cancel_production_wizard_views.xml
└── security/
    └── ir.model.access.csv
```

---

## Task 1 : Squelette du module

**Files:**
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/__init__.py`
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/__manifest__.py`
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/models/__init__.py`
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/models/ron_daily_production.py`
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/wizard/__init__.py`
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/wizard/cancel_production_wizard.py`

- [ ] **Step 1: Créer `__manifest__.py`**

```python
# -*- coding: utf-8 -*-
{
    'name': 'ADI - Cycle de Vie Production',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': "Annulation, remise en brouillon et verrouillage des productions",
    'description': """
Gestion du cycle de vie des productions journalières :
- Annulation propre avec motif obligatoire
- Annulation en cascade des documents générés (BL, achats, factures)
- Retours de stock automatiques pour les documents validés
- Verrouillage des champs selon l'état
- État 'Annulé' distinct de 'Brouillon'
    """,
    'author': 'ADICOPS',
    'website': 'https://adicops-dz.com',
    'depends': [
        'adi_simple_production_cost',
        'stock',
        'purchase',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/cancel_production_wizard_views.xml',
        'views/ron_daily_production_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

- [ ] **Step 2: Créer les `__init__.py`**

`adi_production_lifecycle/__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import models
from . import wizard
```

`adi_production_lifecycle/models/__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import ron_daily_production
```

`adi_production_lifecycle/wizard/__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import cancel_production_wizard
```

- [ ] **Step 3: Créer le modèle hérité minimal**

`models/ron_daily_production.py`:
```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RonDailyProductionLifecycle(models.Model):
    _inherit = 'ron.daily.production'

    state = fields.Selection(
        selection_add=[
            ('cancelled', 'Annulé'),
        ],
        ondelete={'cancelled': 'set default'},
    )

    cancel_reason = fields.Text(
        string="Motif d'annulation",
        tracking=True,
    )
    cancel_date = fields.Datetime(
        string="Date d'annulation",
        readonly=True,
    )
    cancel_uid = fields.Many2one(
        'res.users',
        string="Annulé par",
        readonly=True,
    )
```

- [ ] **Step 4: Créer le wizard minimal (placeholder)**

`wizard/cancel_production_wizard.py`:
```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CancelProductionWizard(models.TransientModel):
    _name = 'ron.cancel.production.wizard'
    _description = "Assistant d'annulation de production"

    production_id = fields.Many2one(
        'ron.daily.production',
        string='Production',
        required=True,
    )
    reason = fields.Text(
        string="Motif d'annulation",
        required=True,
    )
```

- [ ] **Step 5: Créer le fichier de sécurité**

`security/ir.model.access.csv`:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cancel_wizard_user,cancel.wizard.user,model_ron_cancel_production_wizard,adi_simple_production_cost.group_ron_production_user,1,1,1,1
access_cancel_wizard_manager,cancel.wizard.manager,model_ron_cancel_production_wizard,adi_simple_production_cost.group_ron_production_manager,1,1,1,1
```

- [ ] **Step 6: Commit**

```bash
git add adi_dev/adi_dev2/adi_production_lifecycle/
git commit -m "feat(production_lifecycle): squelette du module avec état cancelled et wizard"
```

---

## Task 2 : Wizard d'annulation complet

**Files:**
- Modify: `adi_dev/adi_dev2/adi_production_lifecycle/wizard/cancel_production_wizard.py`
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/wizard/cancel_production_wizard_views.xml`

- [ ] **Step 1: Implémenter le wizard complet**

Le wizard doit :
1. Afficher un résumé des documents liés et leur état
2. Demander un motif obligatoire
3. Permettre de choisir entre "Remettre en brouillon" et "Annuler définitivement"
4. Afficher un avertissement si des factures sont payées

`wizard/cancel_production_wizard.py`:
```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CancelProductionWizard(models.TransientModel):
    _name = 'ron.cancel.production.wizard'
    _description = "Assistant d'annulation de production"

    production_id = fields.Many2one(
        'ron.daily.production',
        string='Production',
        required=True,
    )
    production_state = fields.Selection(
        related='production_id.state',
    )
    reason = fields.Text(
        string="Motif d'annulation",
        required=True,
    )
    action_type = fields.Selection([
        ('reset_draft', 'Remettre en brouillon (pour modification)'),
        ('cancel', 'Annuler définitivement'),
    ], string='Action', required=True, default='reset_draft')

    # --- Champs informatifs (computed) ---
    has_validated_pickings = fields.Boolean(
        compute='_compute_document_summary',
    )
    has_confirmed_purchases = fields.Boolean(
        compute='_compute_document_summary',
    )
    has_posted_invoices = fields.Boolean(
        compute='_compute_document_summary',
    )
    has_paid_invoices = fields.Boolean(
        compute='_compute_document_summary',
    )
    document_summary = fields.Html(
        string="Documents liés",
        compute='_compute_document_summary',
    )

    @api.depends('production_id')
    def _compute_document_summary(self):
        for wiz in self:
            prod = wiz.production_id
            if not prod:
                wiz.has_validated_pickings = False
                wiz.has_confirmed_purchases = False
                wiz.has_posted_invoices = False
                wiz.has_paid_invoices = False
                wiz.document_summary = ''
                continue

            lines = []
            pickings = self._get_all_pickings(prod)
            purchases = self._get_all_purchases(prod)
            invoices = self._get_all_invoices(purchases)

            wiz.has_validated_pickings = any(p.state == 'done' for p in pickings)
            wiz.has_confirmed_purchases = any(p.state in ('purchase', 'done') for p in purchases)
            wiz.has_posted_invoices = any(i.state == 'posted' for i in invoices)
            wiz.has_paid_invoices = any(
                i.payment_state in ('in_payment', 'paid') for i in invoices
            )

            for pick in pickings:
                label = pick.origin or pick.name
                lines.append(f"<li><b>{pick.name}</b> ({label}) - {pick.state}</li>")
            for po in purchases:
                lines.append(f"<li><b>{po.name}</b> ({po.origin or ''}) - {po.state}</li>")
            for inv in invoices:
                lines.append(
                    f"<li><b>{inv.name}</b> - {inv.state}"
                    f" (paiement: {inv.payment_state})</li>"
                )

            if lines:
                wiz.document_summary = "<ul>" + "".join(lines) + "</ul>"
            else:
                wiz.document_summary = "<p><em>Aucun document lié.</em></p>"

    @api.model
    def _get_all_pickings(self, production):
        """Retourne tous les pickings liés à la production."""
        pickings = self.env['stock.picking']
        if production.picking_consumption_id:
            pickings |= production.picking_consumption_id
        if production.picking_packaging_id:
            pickings |= production.picking_packaging_id
        for po in self._get_all_purchases(production):
            pickings |= po.picking_ids
        return pickings

    @api.model
    def _get_all_purchases(self, production):
        """Retourne tous les achats liés à la production."""
        purchases = self.env['purchase.order']
        if production.purchase_finished_id:
            purchases |= production.purchase_finished_id
        if production.purchase_scrap_id:
            purchases |= production.purchase_scrap_id
        if production.purchase_paste_id:
            purchases |= production.purchase_paste_id
        return purchases

    @api.model
    def _get_all_invoices(self, purchases):
        """Retourne toutes les factures liées aux achats."""
        invoices = self.env['account.move']
        for po in purchases:
            invoices |= po.invoice_ids
        return invoices

    def action_apply(self):
        """Exécute l'annulation ou la remise en brouillon."""
        self.ensure_one()
        prod = self.production_id

        if self.has_paid_invoices:
            raise UserError(_(
                "Impossible d'annuler : des factures liées sont déjà payées.\n"
                "Veuillez d'abord annuler les paiements ou créer un avoir manuellement."
            ))

        if self.action_type == 'cancel':
            prod._action_cancel_production(self.reason)
        else:
            prod._action_reset_to_draft(self.reason)

        return {'type': 'ir.actions.act_window_close'}
```

- [ ] **Step 2: Créer la vue du wizard**

`wizard/cancel_production_wizard_views.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="cancel_production_wizard_form" model="ir.ui.view">
        <field name="name">ron.cancel.production.wizard.form</field>
        <field name="model">ron.cancel.production.wizard</field>
        <field name="arch" type="xml">
            <form string="Annuler la production">
                <group>
                    <field name="production_id" readonly="1"/>
                    <field name="production_state" invisible="1"/>
                    <field name="action_type" widget="radio"/>
                    <field name="reason" placeholder="Saisissez le motif de l'annulation..."/>
                </group>

                <div class="alert alert-danger" role="alert"
                     invisible="not has_paid_invoices">
                    <strong>ATTENTION :</strong> Des factures liées sont déjà payées.
                    L'annulation est bloquée. Annulez d'abord les paiements.
                </div>
                <div class="alert alert-warning" role="alert"
                     invisible="not has_validated_pickings">
                    <strong>Note :</strong> Des bons de livraison sont déjà validés.
                    Des retours de stock seront créés automatiquement pour inverser les mouvements.
                </div>
                <div class="alert alert-warning" role="alert"
                     invisible="not has_posted_invoices">
                    <strong>Note :</strong> Des factures fournisseur sont comptabilisées.
                    Elles seront annulées (avoir automatique).
                </div>

                <group string="Documents liés">
                    <field name="document_summary" nolabel="1" colspan="2"/>
                </group>

                <field name="has_validated_pickings" invisible="1"/>
                <field name="has_confirmed_purchases" invisible="1"/>
                <field name="has_posted_invoices" invisible="1"/>
                <field name="has_paid_invoices" invisible="1"/>

                <footer>
                    <button name="action_apply" string="Confirmer l'annulation"
                            type="object" class="btn-danger"
                            invisible="has_paid_invoices"/>
                    <button string="Fermer" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
```

- [ ] **Step 3: Commit**

```bash
git add adi_dev/adi_dev2/adi_production_lifecycle/wizard/
git commit -m "feat(production_lifecycle): wizard d'annulation avec résumé des documents"
```

---

## Task 3 : Logique d'annulation en cascade (pickings)

**Files:**
- Modify: `adi_dev/adi_dev2/adi_production_lifecycle/models/ron_daily_production.py`

- [ ] **Step 1: Implémenter `_cancel_picking` pour annuler/retourner un picking**

Cette méthode traite chaque picking selon son état :
- `draft` / `waiting` / `confirmed` / `assigned` → `action_cancel()`
- `done` → créer un retour via `stock.return.picking` wizard

```python
def _cancel_picking(self, picking):
    """Annule ou retourne un picking selon son état.

    Returns:
        stock.picking: le picking de retour créé (si done), ou False
    """
    if not picking or picking.state == 'cancel':
        return False

    if picking.state == 'done':
        # Créer un retour via le wizard standard Odoo
        return_wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id,
            active_ids=picking.ids,
            active_model='stock.picking',
        ).create({})
        # Le wizard pré-remplit les lignes de retour
        # On lance la création du retour
        result = return_wizard.action_create_returns()
        if not result or not result.get('res_id'):
            _logger.warning("Retour non créé pour picking %s", picking.name)
            return False
        return_picking = self.env['stock.picking'].browse(result['res_id'])
        # Valider le retour immédiatement
        if return_picking.state == 'draft':
            return_picking.action_confirm()
        if return_picking.state in ('confirmed', 'waiting'):
            return_picking.action_assign()
        if return_picking.state == 'assigned':
            for move in return_picking.move_ids:
                move.quantity = move.product_uom_qty
            return_picking.button_validate()
        _logger.info("Retour créé et validé: %s pour %s", return_picking.name, picking.name)
        return return_picking
    else:
        # draft, confirmed, assigned, waiting → annuler directement
        picking.action_cancel()
        _logger.info("Picking annulé: %s", picking.name)
        return False
```

- [ ] **Step 2: Implémenter `_cancel_all_pickings` pour annuler tous les pickings de la production**

```python
def _cancel_all_pickings(self):
    """Annule tous les pickings liés à cette production."""
    self.ensure_one()
    return_pickings = self.env['stock.picking']

    # 1. BL Consommation MP
    if self.picking_consumption_id:
        ret = self._cancel_picking(self.picking_consumption_id)
        if ret:
            return_pickings |= ret

    # 2. BL Consommation Emballage
    if self.picking_packaging_id:
        ret = self._cancel_picking(self.picking_packaging_id)
        if ret:
            return_pickings |= ret

    return return_pickings
```

- [ ] **Step 3: Commit**

```bash
git add adi_dev/adi_dev2/adi_production_lifecycle/models/
git commit -m "feat(production_lifecycle): annulation en cascade des pickings avec retours"
```

---

## Task 4 : Logique d'annulation en cascade (achats + factures)

**Files:**
- Modify: `adi_dev/adi_dev2/adi_production_lifecycle/models/ron_daily_production.py`

- [ ] **Step 1: Implémenter `_cancel_invoice` pour annuler/avoir une facture**

```python
def _cancel_invoice(self, invoice):
    """Annule une facture ou crée un avoir selon son état.

    Returns:
        account.move: l'avoir créé (si posted), ou False
    """
    if not invoice or invoice.state == 'cancel':
        return False

    if invoice.payment_state in ('in_payment', 'paid'):
        raise UserError(_(
            "La facture %s est déjà payée. "
            "Annulez le paiement avant d'annuler la production."
        ) % invoice.name)

    if invoice.state == 'posted':
        # Créer un avoir (credit note)
        credit_note_wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'reason': _("Annulation production %s") % self.name,
            'journal_id': invoice.journal_id.id,
        })
        result = credit_note_wizard.reverse_moves()
        # reverse_moves peut retourner res_id ou domain selon le nombre
        if result and result.get('res_id'):
            credit_note = self.env['account.move'].browse(result['res_id'])
            credit_note.action_post()
            _logger.info("Avoir créé et validé: %s pour %s", credit_note.name, invoice.name)
            return credit_note
        elif result and result.get('domain'):
            # Cas multi-avoir : poster tous les avoirs créés
            credit_notes = self.env['account.move'].search(result['domain'])
            for cn in credit_notes:
                if cn.state == 'draft':
                    cn.action_post()
            _logger.info("Avoirs créés pour %s", invoice.name)
            return credit_notes[:1] if credit_notes else False
    elif invoice.state == 'draft':
        invoice.button_cancel()
        _logger.info("Facture annulée: %s", invoice.name)

    return False
```

- [ ] **Step 2: Implémenter `_cancel_purchase` pour annuler un achat et ses documents liés**

```python
def _cancel_purchase(self, purchase):
    """Annule un achat, ses réceptions et ses factures.

    Ordre: factures → réceptions → achat
    """
    if not purchase or purchase.state == 'cancel':
        return

    # 1. Annuler les factures d'abord
    for invoice in purchase.invoice_ids:
        if invoice.state != 'cancel':
            self._cancel_invoice(invoice)

    # 2. Annuler/retourner les réceptions
    for picking in purchase.picking_ids:
        if picking.state != 'cancel':
            self._cancel_picking(picking)

    # 3. Annuler l'achat lui-même
    if purchase.state in ('draft', 'sent'):
        purchase.button_cancel()
    elif purchase.state in ('purchase', 'done'):
        # En Odoo 17, un PO 'done' (verrouillé) doit être déverrouillé avant annulation
        if purchase.state == 'done':
            purchase.button_unlock()
        purchase.button_cancel()
    _logger.info("Achat annulé: %s", purchase.name)
```

- [ ] **Step 3: Implémenter `_cancel_all_purchases`**

```python
def _cancel_all_purchases(self):
    """Annule tous les achats liés à cette production."""
    self.ensure_one()

    if self.purchase_finished_id:
        self._cancel_purchase(self.purchase_finished_id)

    if self.purchase_scrap_id:
        self._cancel_purchase(self.purchase_scrap_id)

    if self.purchase_paste_id:
        self._cancel_purchase(self.purchase_paste_id)
```

- [ ] **Step 4: Commit**

```bash
git add adi_dev/adi_dev2/adi_production_lifecycle/models/
git commit -m "feat(production_lifecycle): annulation achats, factures et avoirs automatiques"
```

---

## Task 5 : Actions principales (reset draft + cancel)

**Files:**
- Modify: `adi_dev/adi_dev2/adi_production_lifecycle/models/ron_daily_production.py`

- [ ] **Step 1: Implémenter `_action_reset_to_draft` et `_action_cancel_production`**

```python
def _action_reset_to_draft(self, reason=False):
    """Remet la production en brouillon en annulant tous les documents."""
    self.ensure_one()

    if self.state == 'draft':
        raise UserError(_("La production est déjà en brouillon."))

    # Vérifier les factures payées
    self._check_no_paid_invoices()

    # Annuler les documents si on est en validated ou done
    if self.state in ('validated', 'done'):
        self._cancel_all_purchases()
        self._cancel_all_pickings()

    # Nettoyer les liens vers les documents annulés
    self._clear_document_links()

    vals = {'state': 'draft'}
    if reason:
        vals['cancel_reason'] = reason
    self.write(vals)

    body = _("Production remise en brouillon.")
    if reason:
        body += _("<br/><b>Motif :</b> %s") % reason
    self.message_post(body=body)


def _action_cancel_production(self, reason):
    """Annule définitivement la production.

    Note: contrairement à _action_reset_to_draft, les liens vers les documents
    annulés sont CONSERVÉS pour l'audit trail (on peut voir les documents
    annulés depuis la fiche production).
    """
    self.ensure_one()

    if self.state == 'cancelled':
        raise UserError(_("La production est déjà annulée."))

    if not reason:
        raise UserError(_("Le motif d'annulation est obligatoire."))

    # Vérifier les factures payées
    self._check_no_paid_invoices()

    # Annuler les documents si nécessaire
    if self.state in ('validated', 'done'):
        self._cancel_all_purchases()
        self._cancel_all_pickings()

    # Les liens vers les documents sont conservés (audit trail)
    self.write({
        'state': 'cancelled',
        'cancel_reason': reason,
        'cancel_date': fields.Datetime.now(),
        'cancel_uid': self.env.uid,
    })

    self.message_post(body=_(
        "<b>Production annulée.</b><br/>"
        "<b>Motif :</b> %s<br/>"
        "<b>Par :</b> %s"
    ) % (reason, self.env.user.name))


def _check_no_paid_invoices(self):
    """Vérifie qu'aucune facture liée n'est payée."""
    self.ensure_one()
    purchases = self.env['purchase.order']
    if self.purchase_finished_id:
        purchases |= self.purchase_finished_id
    if self.purchase_scrap_id:
        purchases |= self.purchase_scrap_id
    if self.purchase_paste_id:
        purchases |= self.purchase_paste_id

    for po in purchases:
        for inv in po.invoice_ids:
            if inv.payment_state in ('in_payment', 'paid'):
                raise UserError(_(
                    "Impossible d'annuler : la facture %s (achat %s) est payée.\n"
                    "Annulez d'abord le paiement."
                ) % (inv.name, po.name))


def _clear_document_links(self):
    """Remet à False les liens vers les documents annulés."""
    self.ensure_one()
    self.write({
        'picking_consumption_id': False,
        'picking_packaging_id': False,
        'purchase_finished_id': False,
        'purchase_scrap_id': False,
        'purchase_paste_id': False,
    })
```

- [ ] **Step 2: Surcharger `action_reset_draft` pour passer par le wizard**

```python
def action_reset_draft(self):
    """Surcharge: ouvre le wizard d'annulation au lieu de reset direct."""
    self.ensure_one()

    if self.state == 'draft':
        raise UserError(_("La production est déjà en brouillon."))

    # Si aucun document n'a été généré (état confirmed), reset direct
    if self.state == 'confirmed':
        self.write({'state': 'draft'})
        self.message_post(body=_("Production remise en brouillon."))
        return True

    # Si des documents existent, ouvrir le wizard
    return {
        'name': _("Annuler / Remettre en brouillon"),
        'type': 'ir.actions.act_window',
        'res_model': 'ron.cancel.production.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_production_id': self.id,
        },
    }
```

- [ ] **Step 3: Surcharger `unlink` pour permettre la suppression des annulés**

```python
def unlink(self):
    """Étend: bloque la suppression des productions validées/done.

    Seuls les états draft et cancelled sont supprimables.
    Note: le parent bloque déjà 'done', on ajoute 'validated'.
    """
    for rec in self:
        if rec.state in ('validated',):
            raise UserError(_(
                "Impossible de supprimer la production '%s' car elle est validée.\n"
                "Veuillez d'abord l'annuler ou la remettre en brouillon."
            ) % rec.name)
    # Le parent bloque 'done', on laisse passer 'draft' et 'cancelled'
    return super().unlink()
```

- [ ] **Step 4: Commit**

```bash
git add adi_dev/adi_dev2/adi_production_lifecycle/models/
git commit -m "feat(production_lifecycle): actions reset draft et cancel avec wizard et cascade"
```

---

## Task 6 : Vues héritées (boutons, verrouillage, état annulé)

**Files:**
- Create: `adi_dev/adi_dev2/adi_production_lifecycle/views/ron_daily_production_views.xml`

- [ ] **Step 1: Créer les vues héritées**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- ==================== HÉRITAGE VUE FORMULAIRE ==================== -->
    <record id="ron_daily_production_view_form_lifecycle" model="ir.ui.view">
        <field name="name">ron.daily.production.form.lifecycle</field>
        <field name="model">ron.daily.production</field>
        <field name="inherit_id" ref="adi_simple_production_cost.ron_daily_production_view_form"/>
        <field name="arch" type="xml">

            <!-- Ajouter l'état cancelled dans le statusbar -->
            <field name="state" position="attributes">
                <attribute name="statusbar_visible">draft,confirmed,validated,done</attribute>
            </field>

            <!-- Remplacer le bouton "Remettre en Brouillon" pour inclure done et cancelled -->
            <button name="action_reset_draft" position="attributes">
                <attribute name="invisible">state in ('draft', 'cancelled')</attribute>
            </button>

            <!-- Ajouter bouton "Annuler" visible depuis validated et done -->
            <button name="action_done" position="after">
                <button name="action_cancel_production" string="Annuler"
                        type="object" class="btn-danger" icon="fa-times"
                        invisible="state not in ('validated', 'done')"
                        groups="adi_simple_production_cost.group_ron_production_manager"/>
            </button>

            <!-- Ajouter bouton "Remettre en brouillon" depuis cancelled -->
            <button name="action_done" position="after">
                <button name="action_reopen_from_cancelled" string="Rouvrir en Brouillon"
                        type="object" class="btn-warning" icon="fa-undo"
                        invisible="state != 'cancelled'"
                        groups="adi_simple_production_cost.group_ron_production_manager"/>
            </button>

            <!-- Verrouiller les lignes de consommation quand pas en draft -->
            <field name="consumption_line_ids" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>

            <!-- Verrouiller les rebuts quand pas en draft -->
            <field name="scrap_line_ids" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>

            <!-- Verrouiller la pâte quand pas en draft -->
            <field name="paste_line_ids" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>

            <!-- Verrouiller les produits finis quand pas en draft -->
            <field name="finished_product_ids" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>

            <!-- Verrouiller la date et le type quand pas en draft -->
            <field name="production_date" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="production_type" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>

            <!-- Verrouiller les champs d'emballage quand pas en draft -->
            <field name="emballage_solo_qty" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="emballage_solo_unit_cost" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="emballage_classico_qty" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="emballage_classico_unit_cost" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="film_solo_qty" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="film_solo_unit_cost" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="film_classico_qty" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="film_classico_unit_cost" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="emballage_sandwich_qty" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="emballage_sandwich_unit_cost" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="film_sandwich_qty" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>
            <field name="film_sandwich_unit_cost" position="attributes">
                <attribute name="readonly">state != 'draft'</attribute>
            </field>

            <!-- Afficher le motif d'annulation dans le résumé -->
            <field name="notes" position="before">
                <group string="Annulation" invisible="not cancel_reason">
                    <field name="cancel_reason" readonly="1"/>
                    <field name="cancel_date" readonly="1"/>
                    <field name="cancel_uid" readonly="1"/>
                </group>
            </field>

        </field>
    </record>

    <!-- ==================== HÉRITAGE VUE LISTE ==================== -->
    <record id="ron_daily_production_view_tree_lifecycle" model="ir.ui.view">
        <field name="name">ron.daily.production.tree.lifecycle</field>
        <field name="model">ron.daily.production</field>
        <field name="inherit_id" ref="adi_simple_production_cost.ron_daily_production_view_tree"/>
        <field name="arch" type="xml">
            <!-- Ajouter la décoration pour l'état cancelled -->
            <tree position="attributes">
                <attribute name="decoration-danger">state == 'cancelled'</attribute>
            </tree>
        </field>
    </record>

    <!-- ==================== HÉRITAGE VUE RECHERCHE ==================== -->
    <record id="ron_daily_production_view_search_lifecycle" model="ir.ui.view">
        <field name="name">ron.daily.production.search.lifecycle</field>
        <field name="model">ron.daily.production</field>
        <field name="inherit_id" ref="adi_simple_production_cost.ron_daily_production_view_search"/>
        <field name="arch" type="xml">
            <!-- Ajouter le filtre Annulé après Terminé -->
            <filter name="done" position="after">
                <filter string="Annulé" name="cancelled"
                        domain="[('state', '=', 'cancelled')]"/>
            </filter>
        </field>
    </record>

</odoo>
```

- [ ] **Step 2: Implémenter les actions boutons dans le modèle**

Ajouter dans `models/ron_daily_production.py` :

```python
def action_cancel_production(self):
    """Ouvre le wizard d'annulation définitive."""
    self.ensure_one()
    return {
        'name': _("Annuler la production"),
        'type': 'ir.actions.act_window',
        'res_model': 'ron.cancel.production.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_production_id': self.id,
            'default_action_type': 'cancel',
        },
    }

def action_reopen_from_cancelled(self):
    """Rouvre une production annulée en brouillon."""
    self.ensure_one()
    if self.state != 'cancelled':
        raise UserError(_("Seule une production annulée peut être rouverte."))
    self.write({
        'state': 'draft',
        'cancel_reason': False,
        'cancel_date': False,
        'cancel_uid': False,
    })
    self.message_post(body=_("Production rouverte en brouillon (depuis annulé)."))
```

- [ ] **Step 3: Commit**

```bash
git add adi_dev/adi_dev2/adi_production_lifecycle/
git commit -m "feat(production_lifecycle): vues héritées avec verrouillage, boutons et état annulé"
```

---

## Task 7 : Test d'installation et vérification

- [ ] **Step 1: Vérifier la structure complète du module**

```bash
find adi_dev/adi_dev2/adi_production_lifecycle/ -type f | sort
```

Attendu :
```
__init__.py
__manifest__.py
models/__init__.py
models/ron_daily_production.py
security/ir.model.access.csv
views/ron_daily_production_views.xml
wizard/__init__.py
wizard/cancel_production_wizard.py
wizard/cancel_production_wizard_views.xml
```

- [ ] **Step 2: Vérifier la syntaxe Python**

```bash
python3 -m py_compile adi_dev/adi_dev2/adi_production_lifecycle/models/ron_daily_production.py
python3 -m py_compile adi_dev/adi_dev2/adi_production_lifecycle/wizard/cancel_production_wizard.py
```

- [ ] **Step 3: Vérifier la syntaxe XML**

```bash
python3 -c "import xml.etree.ElementTree as ET; ET.parse('adi_dev/adi_dev2/adi_production_lifecycle/views/ron_daily_production_views.xml')"
python3 -c "import xml.etree.ElementTree as ET; ET.parse('adi_dev/adi_dev2/adi_production_lifecycle/wizard/cancel_production_wizard_views.xml')"
```

- [ ] **Step 4: Commit final**

```bash
git add adi_dev/adi_dev2/adi_production_lifecycle/
git commit -m "feat(production_lifecycle): module complet v1.0.0 - gestion cycle de vie production"
```

---

## Récapitulatif des cas traités

| # | Cas | Solution |
|---|---|---|
| 1 | Reset draft depuis confirmed | Reset direct (pas de documents) |
| 2 | Reset draft depuis validated (docs non validés) | Annulation directe des pickings et PO |
| 3 | Reset draft depuis validated (docs validés/done) | Retours de stock + annulation PO + avoirs factures |
| 4 | Annulation depuis done | Même cascade + état `cancelled` + motif obligatoire |
| 5 | Modification en état non-draft | Verrouillage `readonly` sur tous les champs éditables |
| 6 | Documents partiellement validés | Traitement différentiel par état de chaque document |
| 7 | Factures payées | Blocage avec message explicite |
| 8 | Traçabilité | Messages chatter, motif, date, utilisateur |
| 9 | Suppression non contrôlée | Blocage validated/done, permission draft/cancelled |
| 10 | Distinction brouillon vs annulé | État `cancelled` séparé avec possibilité de réouverture |
| 11 | Impact AVCO | Inversé automatiquement par les retours de stock Odoo |
