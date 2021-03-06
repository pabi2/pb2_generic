# -*- coding: utf-8 -*-
from openerp import models, fields, api


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    payment_type = fields.Selection(
        [('cheque', 'Cheque'),
         ('transfer', 'Transfer'),
         ],
        string='Payment Type',
        readonly=True, states={'draft': [('readonly', False)]},
        help="Specified Payment Type, can be used to screen Payment Method",
    )
    transfer_type = fields.Selection(
        [('direct', 'DIRECT'),
         ('smart', 'SMART')
         ],
        string='Transfer Type',
        help="- DIRECT is transfer within same bank.\n"
        "- SMART is transfer is between different bank."
    )
    is_cheque_lot = fields.Boolean(
        string='Is Cheque Lot Available',
        compute='_compute_is_cheque_lot',
        help="True if the payment method also have cheque lot",
    )
    cheque_lot_id = fields.Many2one(
        'cheque.lot',
        string='Cheque Lot',
        domain="[('journal_id', '=', journal_id)]",
        ondelete="restrict",
        readonly=True, states={'draft': [('readonly', False)]},
    )
    supplier_bank_id = fields.Many2one(
        'res.partner.bank',
        string='Supplier Bank Account',
        domain="[('partner_id', '=', partner_id)]",
        readonly=True, states={'draft': [('readonly', False)]},
    )
    supplier_bank_branch = fields.Char(
        string='Supplier Bank Branch',
        related='supplier_bank_id.bank_branch',
        readonly=True,
    )

    @api.one
    @api.depends('journal_id')
    def _compute_is_cheque_lot(self):
        Lot = self.env['cheque.lot']
        lots = Lot.search([('journal_id', '=', self.journal_id.id)])
        self.is_cheque_lot = lots and True or False
