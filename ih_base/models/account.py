# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning


class AccountMove(models.Model):
    _inherit = "account.move"

    ih_sale_order_id = fields.Many2one('sale.order', string='IH Sale Order')
    ih_purchase_id = fields.Many2one('purchase.order', string='IH Purchase Order')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(AccountMoveLine, self).create(vals_list)
        for line in lines:
            if not line.exclude_from_invoice_tab:
                line.ih_input_analytic_account_id()
        
        return lines

    def ih_input_analytic_account_id(self):
        analytic_account_id = False

        if self.move_id.ih_sale_order_id:
            analytic_account_id = self.move_id.ih_sale_order_id.analytic_account_id
        elif self.move_id.ih_purchase_id:
            analytic_account_id = self.move_id.ih_purchase_id.ih_analytic_account_id

        if analytic_account_id:
            self.analytic_account_id = analytic_account_id

