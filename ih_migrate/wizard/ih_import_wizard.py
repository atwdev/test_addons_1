# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, formatLang

from collections import defaultdict
from itertools import groupby
import json
import io
import logging
import tempfile
import binascii
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')


class IHImportWizard(models.TransientModel):
    _name = 'ih.import.wizard'

    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)", attachment=False)
    file_name = fields.Char("File Name")
    file_type = fields.Char('File Type')

    def action_process_file(self):
        if not self.file:
            raise UserError(_('Please upload a file.'))

    button_import_file = fields.Boolean()

    @api.onchange('button_import_file')
    def onchange_button_import_file(self):
        if self.file:
            self.import_file()

    def import_file(self):
        if not self.file:
            raise UserError(_('Please upload a file.'))
        data_file = self.file
        file_name = self.file_name.lower()
        try:
            if file_name.strip().endswith('.xlsx'):
                statement = False
                try:
                    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                    fp.write(binascii.a2b_base64(data_file))
                    fp.seek(0)
                    values = {}
                    workbook = xlrd.open_workbook(fp.name)
                    sheet = workbook.sheet_by_index(0)

                except Exception as e:
                    raise UserError(_("Invalid file!"))
                vals_list = []
                for row_no in range(sheet.nrows):
                    val = {}
                    values = {}
                    if row_no <= 0:
                        fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(map(
                            lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                row.value), sheet.row(row_no)))
                        print('IH ID ',line[8])
                        if line[1] == 'Pendapatan' and line[6] and float(line[6]) > 0:
                            self._process_line_pendapatan(line)
                        elif line[1] == 'HPP':
                            if line[5] and float(line[5]) > 0:
                                self._process_line_hpp_purchase(line)
                            elif line[6] and float(line[6]) > 0:
                                self._process_line_hpp_payment(line)
                        elif line[1] == 'Expense':
                            self._process_line_expense(line)
                        elif line[1] == 'Pajak':
                            self._process_line_pajak(line)
                        elif line[1] == 'Bank':
                            self._process_line_bank(line)
                self._post_account_move()
            else:
                raise ValidationError(_("Unsupported File Type"))
        except Exception as e:
            print(e)
            raise ValidationError(_("Please upload in specified format ! \n"
                                    "date, payment reference, reference, partner, amount, currency ! \n"
                                    "Date Format: %Y-%m-%d"))



    def _process_line_hpp_purchase(self, line):
        analytic_account_id = self._get_analytic_account(line)
        Purchase = self.env['purchase.order']
        purchase_id = Purchase.search([('ih_migrate_id', '=', int(float(line[8])))])
        product_id = self._get_purchase_product(line)
        if not purchase_id:
            purchase_id = Purchase.create({
                'partner_id': self.env.ref('ih_migrate.partner_vendor').id,
                'ih_migrate_id': int(float(line[8])),
                'ih_analytic_account_id': analytic_account_id.id,
                'date_approve': xlrd.xldate_as_datetime(float(line[0]), 0),
                'date_planned': xlrd.xldate_as_datetime(float(line[0]), 0),
                'order_line': [
                    (0, 0, {
                        'product_id': product_id.id,
                        'name': product_id.name,
                        'price_unit': float(line[5]),
                    }),
                ]
            })
        purchase_id.button_confirm()
        purchase_id.write({'date_approve': xlrd.xldate_as_datetime(float(line[0]), 0),
                           'create_date': xlrd.xldate_as_datetime(float(line[0]), 0),})
        return True

    def _process_line_hpp_payment(self, line):
        previous_line_id = int(float(line[8])) - 1
        Purchase = self.env['purchase.order']
        PaymentRegister = self.env['account.payment.register']
        purchase_id = Purchase.search([('ih_migrate_id', '=', previous_line_id)])
        if not purchase_id:
            raise UserError(_("Purchase Order cannot be found for line %s" % previous_line_id))
        if not purchase_id.invoice_ids:
            purchase_id.action_create_invoice()
        move_id = purchase_id.invoice_ids[0]
        if move_id.amount_residual == 0:
            return True
        move_id.write({
            'invoice_date': purchase_id.date_approve.date(),
            'date': purchase_id.date_approve.date(),
            'invoice_date_due': purchase_id.date_approve.date(),
        })
        if move_id.state == 'draft':
            move_id.action_post()
        if move_id.payment_state != 'not_paid':
            return True
        payment_register_id = PaymentRegister.with_context(
            active_model='account.move',
            active_ids=move_id.ids).create({})
        payment_register_id.write({
            'amount': float(line[6]),
            'payment_date': purchase_id.date_approve.date(),
        })
        if line[4] == 'Kas Besar':
            payment_register_id.journal_id = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('company_id', '=', payment_register_id.company_id.id),
                ], limit=1)
        payment_register_id.action_create_payments()
        return True


    def _process_line_pendapatan(self, line):
        analytic_account_id = self._get_analytic_account(line)
        Sales = self.env['sale.order']
        PaymentRegister = self.env['account.payment.register']
        sale_order_id = Sales.search([('ih_migrate_id', '=', int(float(line[8])))])
        product_id = self.env.ref('ih_migrate.product_installation_service')
        if not sale_order_id:
            sale_order_id = Sales.create({
                'partner_id': self.env.ref('ih_migrate.partner_atw_sejahtera').id,
                'partner_invoice_id': self.env.ref('ih_migrate.partner_atw_sejahtera').id,
                'partner_shipping_id': self.env.ref('ih_migrate.partner_atw_sejahtera').id,
                'ih_migrate_id': int(float(line[8])),
                'analytic_account_id': analytic_account_id.id,
                'date_order': xlrd.xldate_as_datetime(float(line[0]), 0),
                'order_line': [
                    (0, 0, {
                        'product_id': product_id.id,
                        'name': product_id.name,
                        'price_unit': float(line[6]),
                    }),
                ]
            })
        sale_order_id.action_confirm()
        sale_order_id.write({'date_order': xlrd.xldate_as_datetime(float(line[0]), 0),
                            'create_date': xlrd.xldate_as_datetime(float(line[0]), 0),
        })
        if not sale_order_id.invoice_ids:
            move_id = sale_order_id._create_invoices()
        else:
            move_id = sale_order_id.invoice_ids[0]
        move_id.write({
            'invoice_date': sale_order_id.date_order.date(),
            'date': sale_order_id.date_order.date(),
            'invoice_date_due': sale_order_id.date_order.date(),
        })
        if move_id.state == 'draft':
            move_id.action_post()
        if line[7] == 'BELUM BAYAR' or move_id.payment_state != 'not_paid':
            return True
        payment_register_id = PaymentRegister.with_context(
            active_model='account.move',
            active_ids=move_id.ids).create({})
        payment_register_id.write({
            'payment_date': sale_order_id.date_order.date(),
            'amount': float(line[6]) * 0.98,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.env.ref('l10n_id.1_a_1_151002').id,
            'writeoff_label': 'PPH 23',
        })
        payment_register_id.action_create_payments()
        return True

    def _process_line_expense(self, line):
        move_id = self._get_account_move(line, 'expense')
        self._write_account_move(line, move_id)

    def _process_line_bank(self, line):
        move_id = self._get_account_move(line, 'bank')
        self._write_account_move(line, move_id)


    def _process_line_pajak(self, line):
        move_id = self._get_account_move(line, 'pajak')
        self._write_account_move(line, move_id)

    def _get_analytic_account(self, line):
        Project = self.env['project.project']
        project_id = Project.search([('name', '=', line[2])])
        if project_id:
            return project_id.analytic_account_id
        project_id = Project.create({
            'name': line[2],
            'partner_id': self.env.ref('ih_migrate.partner_atw_sejahtera').id
        })
        return project_id.analytic_account_id

    def _get_purchase_product(self, line):
        if line[4] == 'HPP Man Power':
            return self.env.ref('ih_migrate.product_man_power')
        elif line[4] == 'HPP Akomodasi':
            return self.env.ref('ih_migrate.product_akom')
        elif line[4] == 'HPP Material':
            return self.env.ref('ih_migrate.product_material')
        elif line[4] == 'Transportasi':
            return self.env.ref('ih_migrate.product_transport')

    def _get_account_move(self, line, category):
        JournalEntry = self.env['account.move'].with_context(default_move_type='entry')
        date = xlrd.xldate_as_datetime(float(line[0]), 0)
        move_id = JournalEntry.search([
            ('ih_category', '=', category),
            ('date', '=', date)])
        if not move_id:
            name = False
            if category == 'expense':
                name = 'EXPS/%s/%s/%s' % (date.year, date.month, date.day)
            elif category == 'bank':
                name = 'BANK/%s/%s/%s' % (date.year, date.month, date.day)
            elif category == 'pajak':
                name = 'TAX/%s/%s/%s' % (date.year, date.month, date.day)
            move_id = JournalEntry.create({
                'name': name,
                'date': date,
                'ih_category': category,
            })
        return move_id

    def _write_account_move(self, line, move_id):
        line_id = move_id.line_ids.filtered(lambda l: l.ih_migrate_id == int(float(line[8])))
        if line_id:
            return True
        account_id = self._get_account_account(line)
        line_value = {
            'name': line[2],
            'account_id': account_id.id,
            'debit': float(line[5]) if line[5] else 0,
            'credit': float(line[6]) if line[6] else 0,
            'ih_migrate_id': int(float(line[8])),
        }
        move_id.with_context(ih_migrate=True).write({
            'line_ids': [
                (0, 0, line_value)
            ]
        })
        return True

    def _get_account_account(self, line):
        if line[4] == 'Adm dan Bunga Bank':
            return self.env.ref('l10n_id.1_a_6_511002')
        elif line[4] == 'Bank Mandiri':
            journal_id = self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('company_id', '=', self.env.ref('base.main_company').id),
            ], limit=1)
            return journal_id.default_account_id
        elif line[4] == 'Kas Besar':
            journal_id = self.env['account.journal'].search([
                ('type', '=', 'cash'),
                ('company_id', '=', self.env.ref('base.main_company').id),
            ], limit=1)
            return journal_id.default_account_id
        elif line[4] == 'Pendapatan Bunga':
            return self.env.ref('l10n_id.1_a_8_110001')
        elif line[4] == 'Piutang Usaha':
            return self.env.ref('l10n_id.1_a_1_121001')
        elif line[4] == 'General':
            return self.env.ref('l10n_id.1_a_6_900000')
        elif line[4] == 'Salary':
            return self.env.ref('l10n_id.1_a_6_110001')
        elif line[4] == 'Pajak Pendapatan':
            return self.env.ref('l10n_id.1_a_6_511008')

    def _post_account_move(self):
        JournalEntry = self.env['account.move']
        move_ids = JournalEntry.search([('ih_category', '!=', False)])
        for move in move_ids:
            print('move', move.id)
            if move.state == 'draft' and move._ih_check_balanced() == 0:
                move.action_post()