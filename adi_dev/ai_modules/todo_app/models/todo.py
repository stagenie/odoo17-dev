from odoo import models, fields, api


class TodoTask(models.Model):
    _name = 'todo.task'
    _description = 'Todo Task'
    _order = 'sequence, id'

    name = fields.Char(
        string='Task',
        required=True,
        help='The title of the todo task'
    )

    description = fields.Text(
        string='Description',
        help='Detailed description of the task'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence for sorting'
    )

    state = fields.Selection(
        selection=[
            ('todo', 'To Do'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
        ],
        string='Status',
        default='todo',
        required=True,
    )

    due_date = fields.Date(
        string='Due Date',
        help='Due date for this task'
    )

    priority = fields.Selection(
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        string='Priority',
        default='medium',
    )

    assigned_to = fields.Many2one(
        comodel_name='res.users',
        string='Assigned To',
        default=lambda self: self.env.user,
    )

    tags = fields.Many2many(
        comodel_name='todo.tag',
        relation='todo_task_tag_rel',
        column1='task_id',
        column2='tag_id',
        string='Tags',
    )

    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True,
    )

    completion_date = fields.Datetime(
        string='Completion Date',
        readonly=True,
    )

    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True,
    )

    @api.depends('due_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for record in self:
            if record.state != 'done' and record.due_date and record.due_date < today:
                record.is_overdue = True
            else:
                record.is_overdue = False

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'done':
            self.completion_date = fields.Datetime.now()
        elif self.state != 'done':
            self.completion_date = None


class TodoTag(models.Model):
    _name = 'todo.tag'
    _description = 'Todo Tag'
    _order = 'name'

    name = fields.Char(
        string='Tag Name',
        required=True,
        unique=True,
    )

    color = fields.Integer(
        string='Color',
        default=0,
        help='Color for the tag'
    )
