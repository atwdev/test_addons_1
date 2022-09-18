from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning

class Purchase(models.Model):
    _inherit = "purchase.order"

    ih_analytic_account_id = fields.Many2one('account.analytic.account', string='IH Analytic Account', check_company=True)    