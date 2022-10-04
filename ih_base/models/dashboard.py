# -*- coding: utf-8 -*-

from odoo import _, fields, models, api
from odoo.exceptions import UserError

class MenuDashboard(models.Model):
    _name = "menu.dashboard"
    _order = "sequence"

    name = fields.Char()
    description = fields.Text()
    sequence = fields.Integer(default=10)

    active = fields.Boolean(default=True)

    action_id = fields.Many2one('ir.actions.act_window')
    action_server_id = fields.Many2one('ir.actions.server')
    button_id = fields.Many2one('ir.actions.act_window')
    button_server_id = fields.Many2one('ir.actions.server')
    button_text = fields.Char()
    parent_id = fields.Many2one('menu.dashboard')
    child_ids = fields.One2many('menu.dashboard', 'parent_id')

    def open_action(self):
        self = self.sudo()
        if not (self.action_id or self.action_server_id):
            raise UserError(_("No action for this item"))
        return self.action_id.read()[0] if self.action_id else {"type": "ir.actions.server", "id": self.action_server_id.id}

    def open_button(self):
        self = self.sudo()
        if not (self.button_id or self.button_server_id):
            raise UserError(_("No button action for this item"))
        return self.button_id.read()[0] if self.button_id else {"type": "ir.actions.server", "id": self.button_server_id.id}
