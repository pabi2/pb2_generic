# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError
from openerp.addons import decimal_precision as dp


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    expense_partner_id = fields.Many2one('res.partner', 'Supplier')
    invoice_number = fields.Char('Document')

    @api.v8
    def compute(self, invoice):
        if invoice.pay_to != 'employee' or invoice.type \
            not in ('in_invoice', 'in_refund'):
            return super(AccountInvoiceTax, self).compute(invoice)
        tax_grouped = {}
        currency = invoice.currency_id.with_context(
            date=invoice.date_invoice or fields.Date.context_today(invoice)
        )
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            if not line.expense_partner_id:
                return super(AccountInvoiceTax, self).compute(invoice) 
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                line.quantity, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] 
                                           * line['quantity']),
                    'invoice_number': line.invoice_number,#probuse
                    'expense_partner_id': line.expense_partner_id and\
                        line.expense_partner_id.id or False, #probuse
                }
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(
                        val['base'] * tax['base_sign'],
                        company_currency, round=False)
                    val['tax_amount'] = currency.compute(
                        val['amount'] * tax['tax_sign'],
                        company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or \
                        line.account_id.id
                    val['account_analytic_id'] =\
                        tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(
                        val['base'] * tax['ref_base_sign'],
                        company_currency, round=False)
                    val['tax_amount'] = currency.compute(
                        val['amount'] * tax['ref_tax_sign'],
                        company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or\
                        line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and \
                    line.account_analytic_id and \
                    val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id
                key = (val['tax_code_id'], val['base_code_id'],
                       val['account_id'], val['invoice_number'],#probuse
                       val['expense_partner_id'])#probuse
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']
        
        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])
        return tax_grouped
    

class AccountVoucherTax(models.Model):
    _inherit = "account.voucher.tax"

    expense_partner_id = fields.Many2one('res.partner', 'Supplier')
    invoice_number = fields.Char('Document')
    
    
    @api.model
    def _compute_one_tax_grouped(self, taxes, voucher, voucher_cur,
                                 invoice, invoice_cur, company_currency,
                                 journal, line_sign, payment_ratio,
                                 line, revised_price):
        
        if invoice.pay_to != 'employee' or\
            invoice.type not in ('in_invoice', 'in_refund'):
            return super(AccountVoucherTax, self)._compute_one_tax_grouped(
                taxes, voucher, voucher_cur,invoice, invoice_cur,
                company_currency, journal, line_sign, payment_ratio,
                line, revised_price)
        tax_gp = {}
        tax_obj = self.env['account.tax']
        for tax in taxes:
            # For Normal
            val = {}
            val['voucher_id'] = voucher.id
            val['invoice_id'] = invoice.id
            val['invoice_number'] = line.invoice_number#probuse
            val['expense_partner_id'] = line.expense_partner_id.id#probuse
            val['tax_id'] = tax['id']
            val['name'] = tax['name']
            val['amount'] = self._to_voucher_currency(
                invoice, journal,
                (tax['amount'] *
                 payment_ratio *
                 line_sign))
            val['manual'] = False
            val['sequence'] = tax['sequence']
            val['base'] = self._to_voucher_currency(
                invoice, journal,
                voucher_cur.round(
                    tax['price_unit'] * line.quantity) *
                payment_ratio * line_sign)
            # For Undue
            vals = {}
            vals['voucher_id'] = voucher.id
            vals['invoice_id'] = invoice.id
            vals['invoice_number'] = line.invoice_number#probuse
            vals['expense_partner_id'] = line.expense_partner_id.id#probuse
            vals['tax_id'] = tax['id']
            vals['name'] = tax['name']
            vals['amount'] = self._to_invoice_currency(
                invoice, journal,
                (-tax['amount'] *
                 payment_ratio *
                 line_sign))
            vals['manual'] = False
            vals['sequence'] = tax['sequence']
            vals['base'] = self._to_invoice_currency(
                invoice, journal,
                voucher_cur.round(
                    -tax['price_unit'] * line.quantity) *
                payment_ratio * line_sign)

            # Register Currency Gain for Normal
            val['tax_currency_gain'] = -(val['amount'] + vals['amount'])
            vals['tax_currency_gain'] = 0.0
            # Check the if services, which has been using undue account
            # This time, it needs to cr: non-undue acct and dr: undue acct
            tax1 = tax_obj.browse(tax['id'])
            is_wht = tax1.is_wht
            # -------------------> Adding Tax for Posting
            if is_wht:
                # Check Threshold first
                base = invoice_cur.compute((revised_price * line.quantity),
                                           company_currency)
                t = tax_obj.browse(val['tax_id'])
                if abs(base) and abs(base) < t.threshold_wht:
                    continue
                # For WHT, change sign.
                val['base'] = -val['base']
                val['amount'] = -val['amount']
                # Case Withholding Tax Dr.
                if voucher.type in ('receipt', 'payment'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = voucher_cur.compute(
                        val['base'] *
                        tax['base_sign'],
                        company_currency) * payment_ratio
                    val['tax_amount'] = voucher_cur.compute(
                        val['amount'] *
                        tax['tax_sign'],
                        company_currency) * payment_ratio
                    val['account_id'] = (tax['account_collected_id'] or
                                         line.account_id.id)
                    val['account_analytic_id'] = \
                        tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = voucher_cur.compute(
                        val['base'] *
                        tax['ref_base_sign'],
                        company_currency) * payment_ratio
                    val['tax_amount'] = voucher_cur.compute(
                        val['amount'] *
                        tax['ref_tax_sign'],
                        company_currency) * payment_ratio
                    val['account_id'] = (tax['account_paid_id'] or
                                         line.account_id.id)
                    val['account_analytic_id'] = \
                        tax['account_analytic_paid_id']

                if not val.get('account_analytic_id', False) and \
                        line.account_analytic_id and \
                        val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['invoice_id'], val['tax_code_id'],
                       val['base_code_id'], val['account_id'],
                       val['invoice_number'], val['expense_partner_id'])#probuse
                if not (key in tax_gp):
                    tax_gp[key] = val
                    tax_gp[key]['amount'] = tax_gp[key]['amount']
                    tax_gp[key]['base'] = tax_gp[key]['base']
                    tax_gp[key]['base_amount'] = tax_gp[key]['base_amount']
                    tax_gp[key]['tax_amount'] = tax_gp[key]['tax_amount']
                    tax_gp[key]['tax_currency_gain'] = 0.0  # No gain for WHT
                else:
                    tax_gp[key]['amount'] += val['amount']
                    tax_gp[key]['base'] += val['base']
                    tax_gp[key]['base_amount'] += val['base_amount']
                    tax_gp[key]['tax_amount'] += val['tax_amount']
                    tax_gp[key]['tax_currency_gain'] += 0.0  # No gain for WHT
            # --> Adding Tax for Posting 1) Contra-Undue 2) Non-Undue
            elif tax1.is_undue_tax:
                # First: Do the Cr: with Non-Undue Account
                refer_tax = tax1.refer_tax_id
                if not refer_tax:
                    raise UserError(
                        _('Undue Tax require Counterpart Tax when setup'))
                # Change name to refer_tax_id
                val['name'] = refer_tax.name
                if voucher.type in ('receipt', 'payment'):
                    val['tax_id'] = refer_tax and refer_tax.id or val['tax_id']
                    val['base_code_id'] = refer_tax.base_code_id.id
                    val['tax_code_id'] = refer_tax.tax_code_id.id
                    val['base_amount'] = voucher_cur.compute(
                        val['base'] *
                        refer_tax.base_sign,
                        company_currency) * payment_ratio
                    val['tax_amount'] = voucher_cur.compute(
                        val['amount'] *
                        refer_tax.tax_sign,
                        company_currency) * payment_ratio
                    val['account_id'] = (refer_tax.account_collected_id.id or
                                         line.account_id.id)
                    val['account_analytic_id'] = \
                        refer_tax.account_analytic_collected_id.id
                else:
                    val['tax_id'] = refer_tax and refer_tax.id or val['tax_id']
                    val['base_code_id'] = refer_tax.ref_base_code_id.id
                    val['tax_code_id'] = refer_tax.ref_tax_code_id.id
                    val['base_amount'] = voucher_cur.compute(
                        val['base'] *
                        refer_tax.ref_base_sign,
                        company_currency) * payment_ratio
                    val['tax_amount'] = voucher_cur.compute(
                        val['amount'] *
                        refer_tax.ref_tax_sign,
                        company_currency) * payment_ratio
                    val['account_id'] = (refer_tax.account_paid_id.id or
                                         line.account_id.id)
                    val['account_analytic_id'] = \
                        refer_tax.account_analytic_paid_id.id

                if not val.get('account_analytic_id', False) and \
                        line.account_analytic_id and \
                        val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['invoice_id'], val['tax_code_id'],
                       val['base_code_id'], val['account_id'],
                       val['invoice_number'], val['expense_partner_id'])#probuse
                if not (key in tax_gp):
                    tax_gp[key] = val
                else:
                    tax_gp[key]['amount'] += val['amount']
                    tax_gp[key]['base'] += val['base']
                    tax_gp[key]['base_amount'] += val['base_amount']
                    tax_gp[key]['tax_amount'] += val['tax_amount']
                    tax_gp[key]['tax_currency_gain'] += \
                        val['tax_currency_gain']

                # Second: Do the Dr: with Undue Account
                if voucher.type in ('receipt', 'payment'):
                    vals['base_code_id'] = tax['base_code_id']
                    vals['tax_code_id'] = tax['tax_code_id']
                    vals['base_amount'] = voucher_cur.compute(
                        val['base'] *
                        tax['base_sign'],
                        company_currency) * payment_ratio
                    vals['tax_amount'] = voucher_cur.compute(
                        val['amount'] *
                        tax['tax_sign'],
                        company_currency) * payment_ratio
                    # USE UNDUE ACCOUNT HERE
                    vals['account_id'] = \
                        (tax1.account_collected_id.id or
                         line.account_id.id)
                    vals['account_analytic_id'] = \
                        tax['account_analytic_collected_id']
                else:
                    vals['base_code_id'] = tax['ref_base_code_id']
                    vals['tax_code_id'] = tax['ref_tax_code_id']
                    vals['base_amount'] = voucher_cur.compute(
                        val['base'] *
                        tax['ref_base_sign'],
                        company_currency) * payment_ratio
                    vals['tax_amount'] = voucher_cur.compute(
                        val['amount'] *
                        tax['ref_tax_sign'],
                        company_currency) * payment_ratio
                    # USE UNDUE ACCOUNT HERE
                    vals['account_id'] = \
                        (tax1.account_paid_id.id or
                         line.account_id.id)
                    vals['account_analytic_id'] = \
                        tax['account_analytic_paid_id']

                if not vals.get('account_analytic_id') and \
                        line.account_analytic_id and \
                        vals['account_id'] == line.account_id.id:
                    vals['account_analytic_id'] = line.account_analytic_id.id

                key = (vals['invoice_id'], vals['tax_code_id'],
                       vals['base_code_id'], vals['account_id'],
                       vals['invoice_number'], vals['expense_partner_id'])#probuse
                if not (key in tax_gp):
                    tax_gp[key] = vals
                else:
                    tax_gp[key]['amount'] += vals['amount']
                    tax_gp[key]['base'] += vals['base']
                    tax_gp[key]['base_amount'] += vals['base_amount']
                    tax_gp[key]['tax_amount'] += vals['tax_amount']
                    tax_gp[key]['tax_currency_gain'] += \
                        vals['tax_currency_gain']
        return tax_gp