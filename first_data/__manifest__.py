# -*- coding: utf-8 -*-
{
    'name': "FirstData Module",

    'summary': """FirstData""",

    'description': """

    """,

    'author': "Alan Gon",
    'website': "",

    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    'category': 'Invoicing',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','account_payment_group','account_payment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_bank_view.xml',
        'views/firt_data_view.xml',
        'views/account_move.xml', 
        'views/first_data_code_response_view.xml', 
        'views/first_data_response_view.xml'     
    ],
}
