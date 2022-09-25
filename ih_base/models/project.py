# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning


class Project(models.Model):
    _inherit = "project.project"

    ih_so_count = fields.Integer(compute="_compute_ih_order_count")
    ih_so_total = fields.Integer(compute="_compute_ih_order_count")
    ih_po_count = fields.Integer(compute="_compute_ih_order_count")
    ih_po_total = fields.Integer(compute="_compute_ih_order_count")

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(['analytic_account_id'])
        for values in vals_list:
            analytic_account_id = values.get('analytic_account_id', defaults.get('analytic_account_id'))
            if not analytic_account_id:
                analytic_account = self._create_analytic_account_from_values(values)
                values['analytic_account_id'] = analytic_account.id
        return super(Project, self).create(vals_list)

    def write(self, values):
        # create the AA for project still allowing timesheet
        if not values.get('analytic_account_id'):
            for project in self:
                if not project.analytic_account_id:
                    project._create_analytic_account()
        return super(Project, self).write(values)

    def _compute_ih_order_count(self):
        for project in self:
            sales_order_ids = self.env['sale.order'].search([
                ('analytic_account_id', '=', project.analytic_account_id.id),
            ])
            purchase_order_ids = self.env['purchase.order'].search([
                ('ih_analytic_account_id', '=', project.analytic_account_id.id),
            ])
            project.ih_so_count = len(sales_order_ids)
            project.ih_so_total = sum(sales_order_ids.mapped('amount_total')) if sales_order_ids else 0
            project.ih_po_count = len(purchase_order_ids)
            project.ih_po_total = sum(purchase_order_ids.mapped('amount_total')) if purchase_order_ids else 0

    def ih_action_view_sale_order(self):
        action = self.env.ref('ih_base.action_sale_order').read()[0]
        action['domain'] = [('default_analytic_account_id', '=', self.analytic_account_id.id)]
        action['context'] = dict(analytic_account_id=self.analytic_account_id.id)
        return action

    def ih_action_view_purchase_order(self):
        action = self.env.ref('ih_base.action_purchase_order').read()[0]
        action['domain'] = [('default_ih_analytic_account_id', '=', self.analytic_account_id.id)]
        action['context'] = dict(ih_analytic_account_id=self.analytic_account_id.id)
        return action
        