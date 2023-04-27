# -*- coding: utf-8 -*-
{
    'name': "Add general pass view",

    'summary': """General pass""",

    'description': """

    """,

    'author': "Alan Gon",
    'website': "",

    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    'category': 'Integration',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account','mail'],

    # always loaded
    'data': [
        'security/acces_group.xml',
        'security/ir.model.access.csv',
#        'views/cam_live_view.xml',
        'views/notify_debtor_view.xml',
        'views/account_move_view.xml',
        'views/city_prefix_view.xml',

    ],
}
