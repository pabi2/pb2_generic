# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    expense_partner_id = fields.Many2one('res.partner', 'Supplier')
    invoice_number = fields.Char('Document')

    @api.model
    def get_invoice_tax_key(self, val, line_id):
        line = self.env['account.invoice.line'].browse(line_id)
        invoice = line.invoice_id
        if invoice.type in ('in_invoice', 'in_refund') and\
                invoice.pay_to == 'employee':
            val.update(invoice_number=line.invoice_number,
                       expense_partner_id=line.expense_partner_id and
                       line.expense_partner_id.id or False)
            key = (val['tax_code_id'],
                   val['base_code_id'],
                   val['account_id'],
                   val['invoice_number'],
                   val['expense_partner_id'])
            return key, val
        else:
            return super(AccountInvoiceTax, self).\
                get_invoice_tax_key(val, line_id)


class AccountVoucherTax(models.Model):
    _inherit = "account.voucher.tax"

    expense_partner_id = fields.Many2one('res.partner', 'Supplier')
    invoice_number = fields.Char('Document')

    @api.model
    def _get_one_tax_key(self, val, line_id):
        line = self.env['account.invoice.line'].browse(line_id)
        invoice = line.invoice_id
        if invoice.type in ('in_invoice', 'in_refund') and\
                invoice.pay_to == 'employee':
            if not val.get('invoice_number', False):
                val.update(invoice_number=line.invoice_number)
            if not val.get('expense_partner_id', False):
                val.update(expense_partner_id=line.expense_partner_id and
                           line.expense_partner_id.id or False)
            key = (val['invoice_id'],
                   val['tax_code_id'],
                   val['base_code_id'],
                   val['account_id'],
                   val['invoice_number'],
                   val['expense_partner_id'])
            return val, key
        else:
            return super(AccountVoucherTax, self).\
                _get_one_tax_key(val, line_id)
