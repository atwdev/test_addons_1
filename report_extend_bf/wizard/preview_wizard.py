# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PreviewWizard(models.TransientModel):
    _name = 'preview.wizard'
    _description = 'Preview Wizard Report'

    url = fields.Char('Document Model Name', compute='_compute_url')
    report_id = fields.Many2one('ir.actions.report', string="Report")

    @api.depends('report_id')
    def _compute_url(self):
        for preview in self:
            base_url = self.get_base_url()
            if preview.report_id.report_type == 'qweb-html':
                converter = 'html'
            elif preview.report_id.report_type == 'qweb-pdf':
                converter = 'pdf'
            else:
                converter = 'text'
            ids = ','.join(map(str, self._context.get('active_ids', [])))
            preview.url = f'{base_url}/report/{converter}/{preview.report_id.report_name}/{ids}'
