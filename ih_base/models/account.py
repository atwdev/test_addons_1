# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning


class AccountMove(models.Model):
    _inherit = "account.move"

    ih_sale_order_id = fields.Many2one('sale.order', string='IH Sale Order')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def create(self, vals):
        res = super(AccountMoveLine, self).create(vals)

        analytic_account_id = False
        if res.move_id.ih_sale_order_id:
            analytic_account_id = res.move_id.ih_sale_order_id.analytic_account_id
        elif res.move_id.purchase_id:
            analytic_account_id = res.move_id.purchase_id.ih_analytic_account_id

        if analytic_account_id:
            res.analytic_account_id = analytic_account_id
        
        return res
