# -*- coding: utf-8 -*-
from datetime import date
from openerp.tests import common


class TestBudgetOperatingUnit(common.TransactionCase):

    def setUp(self):
        super(TestBudgetOperatingUnit, self).setUp()
        self.ResUsers = self.env['res.users']
        self.BudgetObj = self.env['account.budget']
        self.BudgetLineObj = self.env['account.budget.lines']
        # company
        self.company1 = self.env.ref('base.main_company')
        # groups
        self.group_account_user = self.env.ref('account.group_account_user')
        # Main Operating Unit
        self.ou1 = self.env.ref('operating_unit.main_operating_unit')
        # B2C Operating Unit
        self.b2c = self.env.ref('operating_unit.b2c_operating_unit')
        # Budgetary Position
        self.budget_post_purchase = self.env.\
            ref('account_budget.account_budget_post_purchase0')
        # Create users
        self.user1_id = self._create_user('budget_user_1',
                                          [self.group_account_user],
                                          self.company1,
                                          [self.ou1, self.b2c])
        self.user2_id = self._create_user('budget_user_2',
                                          [self.group_account_user],
                                          self.company1,
                                          [self.b2c])
        # Create Main OU budget
        self.budget_ou1 = self._create_budget(self.user1_id,
                                              self.ou1.id,
                                              'Budget Main OU',
                                              'BG-MOU')
        # Create B2C budget
        self.budget_b2c = self._create_budget(self.user2_id,
                                              self.b2c.id,
                                              'Budget B2C',
                                              'BG-B2C')

    def _create_user(self, login, groups, company, operating_units):
        """ Create a user."""
        group_ids = [group.id for group in groups]
        user =\
            self.ResUsers.with_context({'no_reset_password': True}).\
            create({
                'name': 'Budget User',
                'login': login,
                'password': 'demo',
                'email': 'chicago@yourcompany.com',
                'company_id': company.id,
                'company_ids': [(4, company.id)],
                'operating_unit_ids': [(4, ou.id) for ou in operating_units],
                'groups_id': [(6, 0, group_ids)]
            })
        return user.id

    def _create_budget(self, user_id, ou_id, name, code):
        """Create a Budget."""
        budget = self.BudgetObj.sudo(user_id).create({
            'name': name,
            'code': code,
            'creating_user_id': user_id,
            'operating_unit_id': ou_id,
            'date_from': date.today(),
            'date_to': date.today(),
        })
        self.BudgetLineObj.sudo(user_id).create({
            'budget_id': budget.id,
            'planned_amount': 100.0,
            'date_from': date.today(),
            'date_to': date.today(),
        })
        return budget
