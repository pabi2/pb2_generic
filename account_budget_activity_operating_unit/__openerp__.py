# -*- coding: utf-8 -*-
{
    'name': 'Budget with Operating Units',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': '''

Budget with Operating Units
===========================
This module introduces the following features:
- Adds the OU as a required field in the budget plan / budget line
- Security rules are defined to ensure that users can only display the
budget in which they are allowed access to.

''',
    'author': "Eficent",
    'website': 'http://www.eficent.com',
    'depends': ['account_budget_activity',
                'operating_unit'],
    'data': [
        'views/account_budget_view.xml',
        'security/account_budget_security.xml'
    ],
    'installable': True,
}
