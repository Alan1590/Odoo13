# -*- coding: utf-8 -*-
{
    'name': "Add notification menu",

    'summary': """Notified to debtor""",

    'description': """

    """,

    'author': "Alan Gon",
    'website': "",

    'category': 'Integration',
    'version': '0.1',

    'depends': ['account','mail'],

    'data': [
        'security/acces_group.xml',
        'security/ir.model.access.csv',
        'views/notify_debtor_view.xml',
        'views/account_move_view.xml',
        'views/city_prefix_view.xml',

    ],
}
