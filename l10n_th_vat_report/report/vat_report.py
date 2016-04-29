# -*- coding: utf-8 -*-
from openerp.report import report_sxw
import datetime
from openerp.osv import osv


class VatReportParser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(VatReportParser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_lines': self.get_lines,
            'get_year': self.get_year,
            'get_base_total': self.get_base_total,
        })

    def get_year(self, period):
        start_date = period.date_start
        year = datetime.datetime.strptime(start_date, '%Y-%m-%d').year
        return year

    def get_base_total(self, data):
        res = self.get_lines(data)
        base_total = 0.0
        tax_total = 0.0
        for r in res:
            base_total += r['base_amount']
            tax_total += r['tax_amount']
        return {'base_total': base_total, 'tax_total': tax_total}

    def get_lines(self, data):
        period = data.period_id
        company = data.company_id
        tax = data.tax_id
        base_code = data.base_code_id
        tax_code = data.tax_code_id

        self.cr.execute("""
            SELECT
                avt.id,
                SUM(avt.base_amount) as base_amount,
                SUM(avt.amount) as tax_amount,
                voucher.date as date,
                voucher.number as number,
                p.name as partner_name,
                p.vat as tax_id,
                avt.tax_id as tax
            FROM
                account_voucher_tax as avt
            LEFT JOIN account_voucher voucher ON
                (avt.voucher_id = voucher.id)
            LEFT JOIN res_partner p ON
                (voucher.partner_id = p.id)
            WHERE
                avt.tax_id = %s AND
                avt.base_code_id = %s AND
                avt.tax_code_id = %s AND
                voucher.period_id = %s AND
                avt.company_id =%s
            GROUP BY
                avt.id,voucher.date,voucher.number,p.name,p.vat,avt.tax_id
        """, (tax.id, base_code.id, tax_code.id, period.id, company.id))

        result = self.cr.dictfetchall()
        return result


class VatReportAbstarct(osv.AbstractModel):
    _name = "report.l10n_th_vat_report.report_vat"
    _inherit = "report.abstract_report"
    _template = "l10n_th_vat_report.report_vat"
    _wrapped_report_class = VatReportParser

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
