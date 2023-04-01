# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in root directory
##############################################################################

from odoo import models, fields, api, _
import odoo
from odoo.tools.safe_eval import safe_eval, time
from odoo.tools.misc import find_in_path
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval, test_python_expr

import logging
import sys

_logger = logging.getLogger(__name__)


class IrActionsReportCode(models.Model):
    _inherit = 'ir.actions.report'

    template_based_company = fields.Boolean()
    template_id_company = fields.Many2one("ir.attachment", "Template *.odt", company_dependent=True)

    @api.onchange('template_based_company')
    def _onchange_template_based_company(self):
        if self.template_based_company:
            self.template_id = False
        else:
            company_ids = self.env['res.company'].search([])
            for company in company_ids:
                self.with_company(company).template_id_company = False

    @api.constrains('template_based_company')
    def _check_model_company_id(self):
        for report in self:
            if report.template_based_company and 'company_id' not in self.env[report.model]._fields:
                raise ValidationError("The model '%s' does not have field 'company_id'" % report.model)

    DEFAULT_PYTHON_CODE = """# Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - float_compare: Odoo function to compare floats based on specific precisions
    #  - UserError: Warning Exception to use with raise\n\n\n\n"""

    # Python code
    code = fields.Text(string='Python Code', groups='base.group_system',
                       default=DEFAULT_PYTHON_CODE,
                       help="Write Python code that the action will execute. Some variables are "
                            "available for use; help about python expression is given in the help tab.")

    @api.constrains('code')
    def _check_python_code(self):
        for action in self.sudo().filtered('code'):
            msg = test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.model
    def _get_eval_context_report(self, res_ids, action=None):
        eval_context = self._get_eval_context(action)
        model_name = action.model_id.sudo().model
        model = self.env[model_name]

        eval_context.update({
            # orm
            'env': self.env,
            'model': model,
            # Exceptions
            'Warning': odoo.exceptions.Warning,
            'UserError': odoo.exceptions.UserError,
            # record
            'record': model.search([('id', 'in', res_ids)]),
            'records': model.search([('id', 'in', res_ids)]),
        })
        return eval_context


    def _render_qweb_pdf(self, res_ids=None, data=None):
        for action in self.sudo().filtered(lambda r: r.report_type == 'qweb-pdf'):
            safe_eval(self.code.strip(), self._get_eval_context_report(res_ids, action), mode="exec", nocopy=True)
        return super(IrActionsReportCode, self)._render_qweb_pdf(res_ids=res_ids, data=data)

    def get_template_id(self, res_ids):
        if not self.template_based_company:
            return super(IrActionsReportCode, self).get_template_id(res_ids)
        records = self.env[self.model].browse(res_ids)
        company_id = self.env['res.company']
        for record in records:
            if not record.company_id:
                raise UserError(_("This report only applies for records with Company ID"))
            if record.company_id not in company_id:
                company_id |= record.company_id
        if len(company_id) > 1:
            raise UserError(_("Cannot print records from different companies"))
        template_id = self.with_company(company_id).template_id_company
        if not template_id:
            raise UserError(_("Cannot find a template for %s" % company_id.name))
        return template_id
