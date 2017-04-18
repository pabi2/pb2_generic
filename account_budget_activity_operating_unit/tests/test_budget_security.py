# -*- coding: utf-8 -*-
from openerp.addons.account_budget_activity_operating_unit.tests import\
    test_budget_operating_unit as test_budget_ou


class TestBudgetSecurity(test_budget_ou.TestBudgetOperatingUnit):

    def test_budget_ou_security(self):
        """Test Security of Budget Operating Unit"""
        # User 1 can list the budget assigned to
        # Main and B2C OU
        budget_ids =\
            self.BudgetObj.sudo(self.user1_id).\
            search([('operating_unit_id', 'in',
                     [self.ou1.id, self.b2c.id])]).ids
        self.assertNotEqual(budget_ids, [], 'User does not have access to'
                            'Budget which belong to Main and B2C'
                            'Operating Unit.')
        # User 1 can list budget line assigned to Main and b2c OU
        budget_line_ids =\
            self.BudgetLineObj.sudo(self.user1_id).\
            search([('operating_unit_id', 'in',
                     [self.ou1.id, self.b2c.id])]).ids
        self.assertNotEqual(budget_line_ids, [], 'User does not have access to'
                            'Budget Line which belong to Main and B2C'
                            'Operating Unit.')
        # User 2 cannot list the budget assigned to Main OU
        budget_ids =\
            self.BudgetObj.sudo(self.user2_id).\
            search([('operating_unit_id', '=', self.ou1.id)]).ids
        self.assertEqual(budget_ids, [], 'User 2 should not be able to list'
                         'the budget assigned to Main Operating Unit.')
        # User 2 cannot list the budget line assigned to Main OU
        budget_line_ids =\
            self.BudgetLineObj.sudo(self.user2_id).\
            search([('operating_unit_id', 'in',
                     [self.ou1.id])]).ids
        self.assertEqual(budget_line_ids, [], 'User 2 should not be able to '
                         'list the locations assigned to Main OU.')
