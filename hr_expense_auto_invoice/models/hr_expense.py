# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError
from openerp.addons import decimal_precision as dp


class HRExpenseExpese(models.Model):
    _inherit = "hr.expense.expense"

    pay_to = fields.Selection(
        [('employee', 'Employee'),
         ('supplier', 'Supplier')],
        string='Pay to',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default='employee',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain=[('supplier', '=', True)],
    )
    invoice_id = fields.Many2one(
        'account.invoice',
        string='Supplier Invoice',
        readonly=True,
        copy=False,
    )
    date_invoice = fields.Date(
        string='Invoice Date',
        readonly=True,
        copy=False,
    )
    journal_id = fields.Many2one(
        readonly=True,
        copy=False,
    )
    account_move_id = fields.Many2one(
        readonly=True,
        copy=False,
        ondelete='set null',
        compute='_compute_general_entries',
        store=True,
    )
    vat_expense_line_ids = fields.One2many(
        'hr.expense.line',
        'expense_id',
        string="Vat Info",
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
    )

    @api.depends('invoice_id', 'invoice_id.state', 'invoice_id.move_id')
    def _compute_general_entries(self):
        for expense in self:
            if expense.invoice_id and expense.invoice_id.move_id:
                expense.account_move_id = expense.invoice_id.move_id

    @api.model
    def _prepare_inv_line(self, account_id, exp_line):
        line_vals = {
            'name': exp_line.name,
            'account_id': account_id,
            'price_unit': exp_line.unit_amount or 0.0,
            'quantity': exp_line.unit_quantity,
            'product_id': exp_line.product_id.id or False,
            'invoice_line_tax_id': [(6, 0, [x.id for x in exp_line.tax_ids])],
        }
        if exp_line.pay_to == 'employee':
            line_vals.update(
                invoice_number=exp_line.invoice_number,
                supplier_name=exp_line.supplier_name,
                supplier_vat=exp_line.supplier_vat,
                supplier_taxbranch=exp_line.supplier_taxbranch,
                date_invoice=exp_line.date_invoice,
                expense_partner_id=exp_line.expense_partner_id.id,
            )
        return line_vals

    @api.model
    def _prepare_inv(self, expense):
        Invoice = self.env['account.invoice']
        Journal = self.env['account.journal']
        # Journal
        journal_id = False
        if expense.journal_id:
            journal_id = expense.journal_id.id
        else:
            journal = Journal.search([('type', '=', 'purchase'),
                                      ('company_id', '=',
                                       expense.company_id.id)])
            if not journal:
                raise UserError(
                    _("No expense journal found. Please make sure you "
                      "have a journal with type 'purchase' configured."))
            journal_id = journal[0].id
        # Partner, account_id, payment_term
        if expense.pay_to == 'employee':
            if not expense.employee_id.address_home_id:
                raise UserError(
                    _('The employee must have a home address.'))
            if not expense.employee_id.address_home_id.\
                    property_account_payable:
                raise UserError(
                    _('The employee must have a payable account '
                      'set on his home address.'))
        partner = (expense.pay_to == 'employee' and
                   expense.employee_id.address_home_id or
                   expense.partner_id)
        res = Invoice.onchange_partner_id(
            type, partner.id, expense.date_valid, payment_term=False,
            partner_bank_id=False, company_id=expense.company_id.id)['value']
        return {
            'origin': expense.number,
            'comment': expense.name,
            'date_invoice': expense.date_invoice,
            'user_id': expense.user_id.id,
            'partner_id': partner.id,
            'account_id': res.get('account_id', False),
            'payment_term': res.get('payment_term', False),
            'type': 'in_invoice',
            'fiscal_position': res.get('fiscal_position', False),
            'company_id': expense.company_id.id,
            'currency_id': expense.currency_id.id,
            'journal_id': journal_id,
            'pay_to': expense.pay_to,
        }

    @api.model
    def _choose_account_from_exp_line(self, exp_line, fpos=False):
        FiscalPos = self.env['account.fiscal.position']
        account_id = False
        if exp_line.product_id:
            account_id = exp_line.product_id.property_account_expense.id
            if not account_id:
                categ = exp_line.product_id.categ_id
                account_id = categ.property_account_expense_categ.id
            if not account_id:
                raise UserError(
                    _('Define an expense account for this '
                      'product: "%s" (id:%d).') %
                    (exp_line.product_id.name, exp_line.product_id.id,))
        else:
            account_id = exp_line._get_non_product_account_id()
        if fpos:
            fiscal_pos = FiscalPos.browse(fpos)
            account_id = fiscal_pos.map_account(account_id)
        return account_id

    @api.multi
    def _create_supplier_invoice_from_expense(self):
        self.ensure_one()
        inv_lines = []
        Invoice = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']
        expense = self
        invoice_vals = expense._prepare_inv(expense)
        line_total = 0.0
        for exp_line in expense.line_ids:
            account_id = self._choose_account_from_exp_line(
                exp_line, invoice_vals['fiscal_position'])
            line_total += exp_line.total_amount
            inv_line_data = self._prepare_inv_line(account_id, exp_line)
            inv_line = InvoiceLine.create(inv_line_data)
            inv_lines.append(inv_line.id)
            exp_line.write({'invoice_line_ids': [(4, inv_line.id)]})
        if line_total != expense.amount:
            raise UserError(_('Expense amount is mismatched.'))
        invoice_vals.update({'invoice_line': [(6, 0, inv_lines)]})
        # Create Invoice
        invoice = Invoice.create(invoice_vals)
        invoice.button_compute(set_total=True)
        return invoice

    @api.multi
    def action_move_create(self):
        '''
        Create Supplier Invoice (instead of the old style Journal Entries)
        '''
        for expense in self:
            if not expense.invoice_id:
                invoice = expense._create_supplier_invoice_from_expense()
                expense.invoice_id = invoice
            expense.write({'state': 'done'})
        return True


class HRExpenseLine(models.Model):
    _inherit = "hr.expense.line"

    date_invoice = fields.Date(
        string='Date',
        copy=False,
    )
    invoice_number = fields.Char(
        string='Number',
        copy=False,
    )
    supplier_name = fields.Char(
        string='Supplier',
        copy=False,
    )
    supplier_vat = fields.Char(
        string='Tax ID',
        copy=False,
    )
    supplier_taxbranch = fields.Char(
        string='Branch No.',
        copy=False,
    )
    expense_partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        copy=False,
    )
    expense_state = fields.Selection(
        [('draft', 'New'),
         ('cancelled', 'Refused'),
         ('confirm', 'Waiting Approval'),
         ('accepted', 'Approved'),
         ('done', 'Waiting Payment'),
         ('paid', 'Paid'),
         ],
        string='Expense state',
        readonly=True,
        related='expense_id.state',
        store=True,
    )
    pay_to = fields.Selection(
        [('employee', 'Employee'),
         ('supplier', 'Supplier')],
        string='Pay to',
        related='expense_id.pay_to',
        readonly=True,
        store=True,
    )
    tax_ids = fields.Many2many(
        'account.tax',
        'expense_line_tax_rel',
        'expense_line_id', 'tax_id',
        domain=[('parent_id', '=', False),
                ('type_tax_use', '=', 'purchase')],
        string='Taxes',
    )
    total_amount = fields.Float(
        string='Total',
        digits=dp.get_precision('Account'),
        store=True,
        readonly=True,
        compute='_compute_price',
    )
    invoice_line_ids = fields.Many2many(
        'account.invoice.line',
        'expense_line_invoice_line_rel',
        'expense_line_id',
        'invoice_line_id',
        readonly=True,
        copy=False,
    )
    invoiced_qty = fields.Float(
        string='Invoiced Quantity',
        digits=(12, 6),
        compute='_compute_invoiced_qty',
        store=True,
        copy=False,
        default=0.0,
        help="This field calculate invoiced quantity at line level. "
        "Will be used to calculate committed budget",
    )

    @api.depends('invoice_line_ids.invoice_id.state')
    def _compute_invoiced_qty(self):
        Uom = self.env['product.uom']
        for expense_line in self:
            invoiced_qty = 0.0
            for invoice_line in expense_line.invoice_line_ids:
                invoice = invoice_line.invoice_id
                if invoice.state and invoice.state not in ['draft', 'cancel']:
                    # Invoiced Qty in PO Line's UOM
                    invoiced_qty += Uom._compute_qty(invoice_line.uos_id.id,
                                                     invoice_line.quantity,
                                                     expense_line.uom_id.id)
            expense_line.invoiced_qty = min(expense_line.unit_quantity,
                                            invoiced_qty)

    @api.one
    @api.depends('unit_amount', 'unit_quantity', 'tax_ids', 'product_id',
                 'expense_id.partner_id', 'expense_id.currency_id')
    def _compute_price(self):
        taxes = self.tax_ids.compute_all(self.unit_amount, self.unit_quantity,
                                         product=self.product_id,
                                         partner=self.expense_id.partner_id)
        self.total_amount = taxes['total_included']
        if self.expense_id:
            currency = self.expense_id.currency_id
            self.total_amount = currency.round(self.total_amount)

    @api.multi
    def onchange_product_id(self, product_id):
        res = super(HRExpenseLine, self).onchange_product_id(product_id)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            taxes = [tax.id for tax in product.supplier_taxes_id]
            res['value']['tax_ids'] = [(6, 0, taxes)]
        return res

    @api.model
    def _get_non_product_account_id(self):
        Property = self.env['ir.property']
        return Property.get('property_account_expense_categ',
                            'product.category').id
