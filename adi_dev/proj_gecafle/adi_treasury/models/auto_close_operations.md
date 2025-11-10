# Cela les changements à faire si on souaihite
# Totalement automatiser les opérations de clôtures de caissses 

*** treasury_cash_operation.py


# Ajouter cette méthode après la méthode create
@api.model_create_multi
def create(self, vals_list):
    """Override pour gérer la numérotation et l'assignation automatique à une clôture"""
    for vals in vals_list:
        # Si pas de clôture spécifiée, en chercher ou créer une
        if 'closing_id' not in vals or not vals.get('closing_id'):
            if 'cash_id' in vals:
                cash = self.env['treasury.cash'].browse(vals['cash_id'])
                
                # Rechercher une clôture en cours pour aujourd'hui
                today = fields.Date.today()
                pending_closing = self.env['treasury.cash.closing'].search([
                    ('cash_id', '=', vals['cash_id']),
                    ('state', 'in', ['draft', 'confirmed']),
                    ('closing_date', '=', today)
                ], limit=1)
                
                if not pending_closing:
                    # Créer automatiquement une clôture
                    closing_vals = {
                        'cash_id': vals['cash_id'],
                        'closing_date': today,
                    }
                    pending_closing = self.env['treasury.cash.closing'].create(closing_vals)
                    cash.message_post(
                        body=_("✓ Clôture automatique créée pour permettre l'enregistrement d'opérations : %s") % pending_closing.name
                    )
                
                vals['closing_id'] = pending_closing.id
        
        # Marquer comme manuel si créé directement
        if not vals.get('payment_id'):
            vals['is_manual'] = True
        
        # Générer la référence
        if vals.get('name', _('Nouveau')) == _('Nouveau'):
            sequence = self.env['ir.sequence'].search([
                ('code', '=', 'treasury.cash.operation'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if not sequence:
                sequence = self.env['ir.sequence'].create({
                    'name': 'Opération de caisse',
                    'code': 'treasury.cash.operation',
                    'prefix': 'OPC/%(year)s/',
                    'padding': 5,
                    'company_id': self.env.company.id,
                })
            vals['name'] = sequence.next_by_id()
    
    # Créer les opérations
    operations = super().create(vals_list)
    
    # NOUVEAU : Rafraîchir automatiquement les clôtures concernées
    closings_to_refresh = operations.mapped('closing_id')
    for closing in closings_to_refresh:
        if closing and closing.state in ['draft', 'confirmed']:
            closing.with_context(skip_auto_load=True)._compute_closing_lines()
    
    return operations

# Ajouter aussi après action_post
def action_post(self):
    """Comptabiliser l'opération et rafraîchir la clôture"""
    res = super().action_post()
    
    # Rafraîchir la clôture si elle existe
    for operation in self:
        if operation.closing_id and operation.closing_id.state in ['draft', 'confirmed']:
            operation.closing_id.with_context(skip_auto_load=True)._compute_closing_lines()
    
    return res


***  treasury_cash_closing.py
# Modifier la méthode _compute_closing_lines pour être appelée automatiquement
@api.depends('operation_ids', 'operation_ids.state', 'balance_start', 'cash_id', 'period_start', 'period_end')
def _compute_closing_lines(self):
    """Calculer automatiquement les lignes de détail avec solde cumulé"""
    for closing in self:
        if not closing.id or self._context.get('skip_compute'):
            continue
        
        # Charger automatiquement les nouvelles opérations si non fait
        if not self._context.get('skip_auto_load'):
            closing._load_new_operations()
        
        # Supprimer les anciennes lignes
        closing.line_ids.unlink()
        
        lines_data = []
        running_balance = closing.balance_start
        
        # Ligne de solde initial
        lines_data.append({
            'sequence': 0,
            'date': closing.period_start or fields.Datetime.now(),
            'operation_type': 'initial',
            'description': _('Solde initial (report du solde précédent)') if closing.balance_start != 0 else _('Solde initial'),
            'amount_in': 0,
            'amount_out': 0,
            'cumulative_balance': running_balance,
            'closing_id': closing.id,
        })
        
        # Lignes des opérations
        operations = closing.operation_ids.filtered(
            lambda o: o.state == 'posted'
        ).sorted('date')
        
        for seq, op in enumerate(operations, 1):
            if op.operation_type == 'in':
                running_balance += op.amount
                amount_in = op.amount
                amount_out = 0
            else:
                running_balance -= op.amount
                amount_in = 0
                amount_out = op.amount
            
            lines_data.append({
                'sequence': seq,
                'date': op.date,
                'operation_id': op.id,
                'partner_id': op.partner_id.id if op.partner_id else False,
                'category_id': op.category_id.id,
                'operation_type': op.operation_type,
                'description': op.description,
                'reference': op.reference,
                'amount_in': amount_in,
                'amount_out': amount_out,
                'cumulative_balance': running_balance,
                'closing_id': closing.id,
            })
        
        # Créer les nouvelles lignes
        self.env['treasury.cash.closing.line'].create(lines_data)

# Nouvelle méthode pour charger les opérations non assignées
def _load_new_operations(self):
    """Charger automatiquement les nouvelles opérations non assignées"""
    self.ensure_one()
    
    if not self.period_start or not self.period_end:
        return
    
    # Rechercher les opérations non clôturées de la période
    new_operations = self.env['treasury.cash.operation'].search([
        ('cash_id', '=', self.cash_id.id),
        ('date', '>=', self.period_start),
        ('date', '<=', self.period_end),
        ('state', '=', 'posted'),
        ('closing_id', '=', False),
    ])
    
    if new_operations:
        new_operations.write({'closing_id': self.id})
        self.message_post(
            body=_("✓ %d nouvelle(s) opération(s) chargée(s) automatiquement.") % len(new_operations)
        )
    
    # Créer aussi les opérations depuis les paiements non traités
    self._create_operations_from_payments()

# Ajouter ce champ dans la classe pour rafraîchir automatiquement
line_ids = fields.One2many(
    'treasury.cash.closing.line',
    'closing_id',
    string='Détail des opérations',
    compute='_compute_closing_lines',
    store=True
)


***  account_payment.py


# Modifier action_post pour rafraîchir la clôture
def action_post(self):
    """Override pour créer automatiquement une opération de caisse"""
    res = super().action_post()
    
    for payment in self:
        # IMPORTANT : Vérifier qu'il n'y a pas déjà une opération
        if payment.treasury_operation_id:
            continue
            
        # Créer une opération UNIQUEMENT si :
        # 1. Le journal est de type 'cash'
        # 2. Il n'y a pas déjà une opération liée
        if payment.journal_id.type == 'cash':
            # Chercher la caisse associée au journal
            cash = self.env['treasury.cash'].search([
                ('journal_id', '=', payment.journal_id.id),
                ('state', '=', 'open')
            ], limit=1)
            
            if cash:
                # Vérifier qu'une clôture est en cours pour cette caisse
                today = fields.Date.today()
                pending_closing = self.env['treasury.cash.closing'].search([
                    ('cash_id', '=', cash.id),
                    ('state', 'in', ['draft', 'confirmed']),
                    ('closing_date', '=', today)
                ], limit=1)
                
                if not pending_closing:
                    # Créer automatiquement une clôture
                    pending_closing = self.env['treasury.cash.closing'].create({
                        'cash_id': cash.id,
                        'closing_date': today,
                    })
                
                # Déterminer le type et la catégorie...
                # [Code existant pour créer l'opération]
                
                # NOUVEAU : Forcer le rafraîchissement de la clôture
                if pending_closing:
                    pending_closing.with_context(skip_auto_load=True)._compute_closing_lines()
    
    return res
