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
                try:
                    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                    fp.write(binascii.a2b_base64(data_file))
                    fp.seek(0)
                    workbook = xlrd.open_workbook(fp.name)
                    sheet = workbook.sheet_by_index(0)

                except Exception as e:
                    raise UserError(_("Invalid file!"))
            else:
                raise ValidationError(_("Unsupported File Type"))
        except Exception as e:
            print(e)
            raise ValidationError(_("Please upload in specified format ! \n"
                                    "date, payment reference, reference, partner, amount, currency ! \n"
                                    "Date Format: %Y-%m-%d"))
        if not sheet:
            return True
        # line_count = 0
        for row_no in range(sheet.nrows):
            # if line_count > 500:
            #     break
            # if row_no <= 0:
            #     fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
            if row_no > 0:
                line = list(map(
                    lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                        row.value), sheet.row(row_no)))
                print('IH ID ', line)
                if line[1] == 'Pendapatan':
                    if line[6] and float(line[6]) > 0:
                        self._process_line_pendapatan(line)
                elif line[1] == 'HPP':
                    if line[5] and float(line[5]) > 0:
                        self._process_line_hpp_purchase(line)
                    elif line[6] and float(line[6]) > 0:
                        self._process_line_register_payment(line)
                elif line[1] == 'Bank':
                    self._process_line_bank(line)
                else:
                    if line[5] and float(line[5]) > 0:
                        self._process_line_other_bill(line)
                    elif line[6] and float(line[6]) > 0:
                        self._process_line_register_payment(line)
            # line_count += 1
        self._post_account_bank_statement()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

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

        if not purchase_id.invoice_ids:
            purchase_id.action_create_invoice()
        move_id = purchase_id.invoice_ids[0]

        move_id.write({
            'invoice_date': purchase_id.date_approve.date(),
            'date': purchase_id.date_approve.date(),
            'invoice_date_due': purchase_id.date_approve.date(),
            'ih_migrate_id': int(float(line[8])),
        })
        if move_id.state == 'draft':
            move_id.action_post()
        return True

    def _process_line_pendapatan(self, line):
        analytic_account_id = self._get_analytic_account(line)
        Sales = self.env['sale.order']
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
            'ih_migrate_id': int(float(line[8])),
        })
        if move_id.state == 'draft':
            move_id.action_post()
<<<<<<< HEAD
        if line[7] == 'BELUM BAYAR' or move_id.payment_state != 'not_paid':
            return True
        payment_register_id = PaymentRegister.with_context(
            active_model='account.move',
            active_ids=move_id.ids).create({})
        payment_register_id.write({
            'payment_date': sale_order_id.date_order.date(),
            'amount': float(line[6]) * 0.98,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.env.ref('l10n_id.1_l10n_id_11510030').id,
            'writeoff_label': 'PPH 23',
        })
        payment_register_id.action_create_payments()
        return True
=======
        self._process_line_register_payment(line)
>>>>>>> 1b7b801afe69c01be5aa1353fdf69a29620d8ad3

        return True

    def _process_line_bank(self, line):
        statement_id = self._get_account_bank_statement(line)
        if not statement_id:
            return True
        self._write_account_bank_statement(line, statement_id)

    def _process_line_other_bill(self, line):
        print('_process_line_other_bill', line)
        move_id = self._get_account_move(line)
        if not move_id:
            return True
        self._write_account_move(line, move_id)
        if move_id.state == 'draft':
            move_id.action_post()

    def _process_line_register_payment(self, line):
        ih_migrate_id = (int(float(line[8])) - 1) if line[1] != 'Pendapatan' else int(float(line[8]))
        Move = self.env['account.move']
        PaymentRegister = self.env['account.payment.register']
        move_id = Move.search([('ih_migrate_id', '=', ih_migrate_id)])
        if not move_id or move_id.payment_state != 'not_paid' or move_id.amount_total != float(line[6]) or line[7] == 'BELUM BAYAR':
            return True
        payment_register_id = PaymentRegister.with_context(
            active_model='account.move',
            active_ids=move_id.ids).create({})
        write_vals = {
            'payment_date': move_id.date,
            'amount': move_id.amount_total,
        }
        if line[4] == 'Kas Besar':
            write_vals['journal_id'] = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('company_id', '=', payment_register_id.company_id.id),
                ], limit=1).id
        if line[1] == 'Pendapatan':
            amount = float(line[6]) * 0.98
            write_vals['amount'] = amount
            write_vals['payment_difference_handling'] = 'reconcile'
            write_vals['writeoff_account_id'] = self.env.ref('l10n_id.1_a_1_151002').id
            write_vals['writeoff_label'] = 'PPH 23'
        payment_register_id.write(write_vals)
        payment_register_id.action_create_payments()
        if line[1] != 'Pendapatan':
            self._process_line_bank(line)

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

    def _get_account_move(self, line):
        JournalEntry = self.env['account.move'].with_context(default_move_type='in_invoice')
        date = xlrd.xldate_as_datetime(float(line[0]), 0).date()
        name = line[8]
        ih_migrate_id = int(float(line[8]))
        move_id = JournalEntry.search([
            ('ih_migrate_id', '=', ih_migrate_id)])
        if not move_id:
            move_id = JournalEntry.create({
                'name': '%s/%s' % (line[1], name),
                'partner_id': self.env.ref('ih_migrate.partner_vendor').id,
                'date': date,
                'invoice_date': date,
                'invoice_date_due': date,
                'ih_migrate_id': ih_migrate_id,
            })
        return move_id

    def _write_account_move(self, line, move_id):
        self = self.with_context(default_move_type='in_invoice')
        line_id = move_id.line_ids.filtered(lambda l: l.ih_migrate_id == int(float(line[8])))
        if line_id:
            return True
        account_id = self._get_account_account(line)
        amount = 0
        if line[5] and float(line[5]) > 0:
            amount = float(line[5])
        elif line[6] and float(line[6]) > 0:
            amount = -float(line[6])
        line_value = {
            'name': line[2],
            'account_id': account_id.id,
            'price_unit': amount,
            'ih_migrate_id': int(float(line[8])),
        }
        move_id.write({
            'invoice_line_ids': [
                (0, 0, line_value)
            ]
        })

        return True

    def _get_account_account(self, line):
<<<<<<< HEAD
        if line[4] == 'Adm dan Bunga Bank':
            return self.env.ref('l10n_id.1_l10n_id_65110020')
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
            return self.env.ref('l10n_id.1_l10n_id_81100010')
        elif line[4] == 'Piutang Usaha':
            return self.env.ref('l10n_id.1_l10n_id_11210010')
        elif line[4] == 'General':
            return self.env.ref('l10n_id.1_l10n_id_69000000')
=======
        if line[4] == 'General':
            return self.env.ref('l10n_id.1_a_6_900000')
>>>>>>> 1b7b801afe69c01be5aa1353fdf69a29620d8ad3
        elif line[4] == 'Salary':
            return self.env.ref('l10n_id.1_l10n_id_61100010')
        elif line[4] == 'Pajak Pendapatan':
<<<<<<< HEAD
            return self.env.ref('l10n_id.1_l10n_id_65110070')
=======
            return self.env.ref('l10n_id.1_a_6_511008')
        else:
            return False

    def _get_account_bank_statement(self, line):
        if line[4] == 'Kas Besar':
            Statement = self.env['account.bank.statement'].with_context(journal_type='cash')
        elif line[4] == 'Bank Mandiri':
            Statement = self.env['account.bank.statement'].with_context(journal_type='bank')
        else:
            return False
        date = xlrd.xldate_as_datetime(float(line[0]), 0)
        statement_id = Statement.search([
            ('ih_month', '=', float(date.month)),
            ('ih_year', '=', float(date.year)),
            ('journal_id', '=', Statement._default_journal().id),
        ])
        if not statement_id:
            statement_id = Statement.create({
                'name': '%s/%s/%s' % (line[4], date.year, date.month),
                'date': date.date(),
                'ih_month': float(date.month),
                'ih_year': float(date.year),
            })
        return statement_id

    def _write_account_bank_statement(self, line, statement_id):
        line_id = statement_id.line_ids.filtered(lambda l: l.ih_migrate_id == int(float(line[8])))
        if line_id:
            return True
        amount = 0
        if line[5] and float(line[5]) > 0:
            amount = float(line[5])
        elif line[6] and float(line[6]) > 0:
            amount = -float(line[6])
        line_value = {
            'payment_ref': line[2],
            'amount': amount,
            'ih_migrate_id': int(float(line[8])),
        }
        statement_id.write({
            'line_ids': [
                (0, 0, line_value)
            ]
        })
        return True

    def _post_account_bank_statement(self):
        self._sort_account_bank_statement('bank')
        self._sort_account_bank_statement('cash')

>>>>>>> 1b7b801afe69c01be5aa1353fdf69a29620d8ad3

    def _sort_account_bank_statement(self, journal_type):
        Statement = self.env['account.bank.statement']
        statement_ids = Statement.search([('journal_type', '=', journal_type)]).sorted('date')
        previous_balance_end = 0
        for statement_id in statement_ids:
            statement_id.write({'balance_start': previous_balance_end,
                        'balance_end_real': previous_balance_end + statement_id.total_entry_encoding})
            statement_id.button_post()
            previous_balance_end = statement_id.balance_end