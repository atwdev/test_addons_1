# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning

class Company(models.Model):
    _inherit = "res.company"


    def ih_change_tax_ids(self):
        self.write({
            'account_sale_tax_id': self.env.ref('l10n_id.1_tax_ST0').id,
            'account_purchase_tax_id': self.env.ref('l10n_id.1_tax_PT2').id,
        })