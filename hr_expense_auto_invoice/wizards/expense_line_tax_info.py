# -*- coding: utf-8 -*-
# © 2016 Kitti U.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, models, fields


class ExpenseLineTaxInfo(models.TransientModel):
    _name = "expense.line.tax.info"

    date_invoice = fields.Date('Date', required=True, default=fields.Date.today(), )
    invoice_number = fields.Char('Number', required=True, )
    supplier_name = fields.Char('Supplier', required=True, )
    supplier_vat = fields.Char('Tax ID', required=True, )
    supplier_taxbranch = fields.Char('Branch No.', required=True, )

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
                })
        return True