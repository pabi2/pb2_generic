# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import Warning


class AccountBudget(models.Model):
    _inherit = "account.budget"

    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
        default=lambda self: self.env['res.users'].
        operating_unit_default_get(self._uid),
    )

    @api.one
    @api.constrains('operating_unit_id', 'company_id')
    def _check_company_operating_unit(self):
        if self.company_id and self.operating_unit_id and \
                self.company_id != self.operating_unit_id.company_id:
            raise Warning(_('The Company in the Move Line and in the '
                            'Operating Unit must be the same.'))


class AccountBudgetLines(models.Model):
    _inherit = "account.budget.line"

    operating_unit_id = fields.Many2one(
        'operating.unit',
        related='budget_id.operating_unit_id',
        string='Operating Unit', readonly=True, store=True,
    )
