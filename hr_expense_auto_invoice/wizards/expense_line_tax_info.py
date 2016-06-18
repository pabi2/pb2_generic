# -*- coding: utf-8 -*-
# © 2016 Kitti U.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date
from openerp import api, models, fields


class ExpenseLineTaxInfo(models.TransientModel):
    _name = "expense.line.tax.info"

    date_invoice = fields.Date(
        'Date',
        required=True,
        default=fields.Date.today(),
    )
    invoice_number = fields.Char('Number', required=True, )
    supplier_name = fields.Char('Supplier Text', required=True, )
    supplier_vat = fields.Char('Tax ID', required=True, )
    supplier_taxbranch = fields.Char('Branch No.', required=True, )
    expense_partner_id = fields.Many2one(
        'res.partner',
        string='Supplier ID',
        required=False,
    )

    @api.multi
    def action_add_tax_info(self):
        line_id = self.env.context.get('active_id', False)
        for record in self:
            if line_id:
                line = self.env['hr.expense.line'].browse(line_id)
                line.write({
                    'date_invoice': record.date_invoice,
                    'invoice_number': record.invoice_number,
                    'supplier_name': record.supplier_name,
                    'supplier_vat': record.supplier_vat,
                    'supplier_taxbranch': record.supplier_taxbranch,
                    'expense_partner_id': record.expense_partner_id.id,
                })
        return True

    @api.model
    def default_get(self, fields):
        rec = super(ExpenseLineTaxInfo, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_id = context.get('active_id')
        expense_line = self.env[active_model].browse(active_id)
        date_invoice = date.today().strftime('%Y-%m-%d')
        if expense_line.date_invoice:
            date_invoice = expense_line.date_invoice
        rec.update({
            'invoice_number': expense_line.invoice_number,
            'supplier_name': expense_line.supplier_name,
            'supplier_vat': expense_line.supplier_vat,
            'supplier_taxbranch': expense_line.supplier_taxbranch,
            'date_invoice': date_invoice,
            'expense_partner_id': expense_line.expense_partner_id.id,
        })
        return rec
