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
    ih_migrate_id = fields.Integer()

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


class AccountPayment(models.Model):
    _inherit = "account.payment"

    journal_type = fields.Selection(related='journal_id.type',
                                    help="Technical field used for usability purposes")


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    ih_month = fields.Float()
    ih_year = fields.Float()

    def ih_update_cash_balance(self):
        previous_month = (self.ih_month - 1) if self.ih_month != 1 else 12
        previous_year = self.ih_year if self.ih_month != 1 else (self.ih_year - 1)
        previous_statement_id = self.env['account.bank.statement'].search([
            ('ih_month', '=', previous_month),
            ('ih_year', '=', previous_year),
            ('journal_id', '=', self.journal_id.id),
        ])
        balance_start = 0
        if previous_statement_id:
            balance_start = previous_statement_id.balance_end_real
        self.write({
            'balance_start': balance_start,
            'balance_end_real': balance_start + self.balance_end
        })


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    ih_migrate_id = fields.Integer()
    ih_payment_id = fields.Many2one('account.payment')