# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning

class AccountMove(models.Model):
    _inherit = "account.move"

    ih_category = fields.Char()
    ih_month = fields.Char()
    ih_year = fields.Char()

    def _check_balanced(self):
        if self.env.context.get('ih_migrate'):
            return True
        return super(AccountMove, self)._check_balanced()

    def _ih_check_balanced(self):
        balance = 0
        for line in self.line_ids:
            balance += round(line.debit - line.credit)
        return balance

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ih_migrate_id = fields.Integer()