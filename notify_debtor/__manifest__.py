# -*- coding: utf-8 -*-
{
    'name': "Add notification menu",

    'summary': """Notified to debtor""",

    'description': """

    """,

    'author': "Alan Gon",
    'website': "",

    'category': 'Integration',
    'version': '0.3',

    'depends': ['account','mail'],

    'data': [
        'security/acces_group.xml',
        'security/ir.model.access.csv',
        'views/notify_debtor_view.xml',
        'views/notify_debtor_partner_view.xml',
        'views/city_prefix_view.xml',
        'views/notify_debtor_wizard.xml',
    ],
}