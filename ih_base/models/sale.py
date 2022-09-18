from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning

class Sales(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        invoice_vals = super(Sales, self)._prepare_invoice()
        invoice_vals['ih_sale_order_id'] = self.id
        return invoice_vals

    