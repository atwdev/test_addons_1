# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError, ValidationError, RedirectWarning

class Purchase(models.Model):
    _inherit = "purchase.order"

    ih_migrate_id = fields.Integer()