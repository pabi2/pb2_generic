# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.tools import float_compare


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    tax_invoice_line = fields.One2many(
        'account.invoice.line',
        'invoice_id',
        string='Invoice Lines',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True,
    )
    pay_to = fields.Selection(
        [('employee', 'Employee'),
         ('supplier', 'Supplier')],
        string='Pay to',
        default='supplier',
        readonly=True,
    )

    @api.multi
    def confirm_paid(self):
        expenses = self.env['hr.expense.expense'].search([('invoice_id',
                                                           'in', self._ids)])
        if expenses:
            expenses.write({'state': 'paid'})
        return super(AccountInvoice, self).confirm_paid()

    @api.multi
    def action_cancel(self):
        expenses = self.env['hr.expense.expense'].search([('invoice_id',
                                                           'in', self._ids)])
        if expenses:
            expenses.signal_workflow('done_to_refuse')
        return super(AccountInvoice, self).action_cancel()

    @api.multi
    def invoice_validate(self):
        for invoice in self:
            if invoice.type in ('in_invoice', 'in_refund') and\
                    invoice.pay_to == 'employee':
                for tax in invoice.tax_line:
                    if not tax.expense_partner_id:
                        raise except_orm(
                            _('Warning!'),
                            _("Please define supplier in tax line."))
        expenses = self.env['hr.expense.expense'].search([('invoice_id',
                                                           'in', self._ids)])
        for expense in expenses:
            if expense.amount != expense.invoice_id.amount_total:
                raise except_orm(
                    _('Amount Error!'),
                    _("This invoice amount is not equal to amount in "
                      "expense: %s" % (expense.number,)))
            expense.signal_workflow('refuse_to_done')
        return super(AccountInvoice, self).invoice_validate()

    @api.multi
    def check_tax_lines(self, compute_taxes):
        if self.type not in ('in_invoice', 'in_refund') or\
                self.pay_to != 'employee':
            return super(AccountInvoice, self).check_tax_lines(compute_taxes)
        account_invoice_tax = self.env['account.invoice.tax']
        company_currency = self.company_id.currency_id
        if not self.tax_line:
            for tax in compute_taxes.values():
                account_invoice_tax.create(tax)
        else:
            tax_key = []
            precision = self.env['decimal.precision'].precision_get('Account')
            for tax in self.tax_line:
                if tax.manual:
                    continue
                # TODO: create hook method
                key = (tax.tax_code_id.id, tax.base_code_id.id,
                       tax.account_id.id, tax.invoice_number,
                       tax.expense_partner_id.id)
                tax_key.append(key)
                if key not in compute_taxes:
                    raise except_orm(_('Warning!'),
                                     _('Global taxes defined,\
                                    but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                if float_compare(abs(base - tax.base),
                                 company_currency.rounding,
                                 precision_digits=precision) == 1:
                    raise except_orm(_('Warning!'),
                                     _('Tax base different!\nClick \
                                     on compute to update the tax base.'))
            for key in compute_taxes:
                if key not in tax_key:
                    raise except_orm(_('Warning!'),
                                     _('Taxes are missing!\nClick on\
                                     compute button.'))


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    date_invoice = fields.Date('Date')
    invoice_number = fields.Char('Document')
    supplier_name = fields.Char('Supplier Name')
    supplier_vat = fields.Char('Tax ID')
    supplier_taxbranch = fields.Char('Branch No.')
    expense_partner_id = fields.Many2one('res.partner', 'Supplier')
