# -*- coding: utf-8 -*-
from openerp import fields, models
from openerp import tools


class VatReport(models.Model):
    _name = 'vat.report'
    _auto = False

    base_amount = fields.Float(
        string='Base Amount'
    )
    tax_amount = fields.Float(
        string='Tax Amount'
    )
    date = fields.Date(
        string='Date',
    )
    number = fields.Char(
        string='Number',
    )
    partner_name = fields.Char(
        string='Partner Name',
    )
    tax_id = fields.Char(
        string='Tax ID'
    )
    base_code_id = fields.Many2one(
        'account.tax.code',
        string='Base Code'
    )
    tax_code_id = fields.Many2one(
        'account.tax.code',
        string='Tax Code'
    )
    period_id = fields.Many2one(
        'account.period',
        string='Period'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
    )

    # Methods for create voucher tax query
    def _get_voucher_tax_select(self):
        select_str = """
            MIN(avt.id) as id,
            SUM(avt.base_amount) as base_amount,
            SUM(avt.tax_amount) as tax_amount,
            voucher.date as date,
            voucher.number as number,
            avt.base_code_id as base_code_id,
            avt.tax_code_id as tax_code_id,
            voucher.period_id as period_id,
            voucher.company_id as company_id,
            p.name as partner_name,
            p.vat as tax_id
        """
        return select_str

    def _get_voucher_tax_from(self):
        voucher_tax_from = """
                account_voucher_tax as avt
            LEFT JOIN account_voucher voucher ON
                (avt.voucher_id = voucher.id)
            LEFT JOIN res_partner p ON
                (voucher.partner_id = p.id)
        """
        return voucher_tax_from

    def _get_voucher_tax_where(self):
        voucher_tax_where = """
            voucher.state in ('posted') AND
            voucher.number is not null AND
            avt.tax_code_type = 'normal' AND
            voucher.type not in ('payment')
        """
        return voucher_tax_where

    def _get_voucher_tax_groupby(self):
        invoice_groupby = """
            voucher.date,
            voucher.number,
            avt.base_code_id,
            avt.tax_code_id,
            voucher.period_id,
            voucher.company_id,
            p.name,
            p.vat
        """
        return invoice_groupby

    # Methods for create invoice tax query
    def _get_invoice_tax_select(self):
        select_str = """
            MIN(ait.id) as id,
            SUM(ait.base_amount) as base_amount,
            SUM(ait.tax_amount) as tax_amount,
            invoice.date_invoice as date,
            invoice.internal_number as number,
            ait.base_code_id as base_code_id,
            ait.tax_code_id as tax_code_id,
            invoice.period_id as period_id,
            invoice.company_id as company_id,
            p.name as partner_name,
            p.vat as tax_id
        """
        return select_str

    def _get_invoice_tax_from(self):
        invoice_tax_from = """
                account_invoice_tax as ait
            LEFT JOIN account_invoice invoice ON
                (ait.invoice_id = invoice.id)
            LEFT JOIN res_partner p ON
                (invoice.partner_id = p.id)
        """
        return invoice_tax_from

    def _get_invoice_tax_where(self):
        invoice_tax_where = """
            invoice.state in ('open', 'paid') AND
            invoice.internal_number is not null AND
            ait.tax_code_type = 'normal' AND
            invoice.type not in ('in_refund', 'in_invoice')
        """
        return invoice_tax_where

    def _get_invoice_tax_groupby(self):
        invoice_tax_groupby = """
            invoice.date_invoice,
            invoice.internal_number,
            ait.base_code_id ,
            ait.tax_code_id,
            invoice.period_id,
            invoice.company_id,
            p.name,
            p.vat
        """
        return invoice_tax_groupby

    def _get_invoice_tax_query(self):
        invoice_tax_query = """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            GROUP BY
                %s
        """ % (self._get_invoice_tax_select(),
               self._get_invoice_tax_from(),
               self._get_invoice_tax_where(),
               self._get_invoice_tax_groupby())
        return invoice_tax_query

    def _get_voucher_tax_query(self):
        voucher_tax_query = """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            GROUP BY
                %s
        """ % (self._get_voucher_tax_select(),
               self._get_voucher_tax_from(),
               self._get_voucher_tax_where(),
               self._get_voucher_tax_groupby())
        return voucher_tax_query

    # Methods for create main sql view
    def _get_select(self):
        select = """
            MIN(id) as id,
            base_amount,
            tax_amount,
            date,
            number,
            base_code_id,
            tax_code_id,
            period_id,
            company_id,
            partner_name,
            tax_id
        """
        return select

    def _get_from(self):
        from_str = """
            ( %s )
                UNION
                    ( %s )
        """ % (self._get_invoice_tax_query(),
               self._get_voucher_tax_query(),)
        return from_str

    def _get_groupby(self):
        groupby_str = """
            id,
            base_amount,
            tax_amount,
            date,
            number,
            base_code_id,
            tax_code_id,
            period_id,
            company_id,
            partner_name,
            tax_id
        """
        return groupby_str

    def _get_orderby(self):
        order_by = "date"
        return order_by

    def _get_sql_view(self):
        sql_query = """
            SELECT
                %s
            FROM
                (%s)
            AS foo
            GROUP BY
                %s
            ORDER BY
                %s
        """ % (self._get_select(),
               self._get_from(),
               self._get_groupby(),
               self._get_orderby())
        return sql_query

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute(""" CREATE or REPLACE VIEW %s as (%s)
        """ % (self._table, self._get_sql_view()))