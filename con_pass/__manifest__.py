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
    'depends': ['base','mail'],

    # always loaded
    'data': [
        'security/acces_group.xml',
        'security/ir.model.access.csv',
#        'views/cam_live_view.xml',
        'schendule_bloqued.xml',
        'views/general_pass_view.xml',
        'views/general_pass_user_view.xml',
    ],
}
