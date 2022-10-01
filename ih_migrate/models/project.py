# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning

class Project(models.Model):
    _inherit = "project.project"

    @api.model_create_multi
    def create(self, vals_list):
        """ Create an analytic account if project allow timesheet and don't provide one
            Note: create it before calling super() to avoid raising the ValidationError from _check_allow_timesheet
        """
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