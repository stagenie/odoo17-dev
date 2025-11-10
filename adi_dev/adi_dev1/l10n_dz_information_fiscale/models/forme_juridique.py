# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FormeJuridique(models.Model):
    _name = 'forme.juridique'

    code = fields.Char(
        string="Code"
    )

    name = fields.Char(
        string="Nom",
        required=True
    )

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, "[{}] {}".format(record.code, record.name)))
        return res
