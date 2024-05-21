# -*- coding: utf-8 -*-
{
	'name': "Module to direct debit",

	'summary': """Derict debit""",

	'description': """

	""",

	'author': "Alan Gon",
	'website': "",

	# Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
	'category': 'Integration',
	'version': '0.1',

	# any module necessary for this one to work correctly
	'depends': ['base','account','mail','account_payment_group','account_payment'],

	# always loaded
	'data': [
#        'security/acces_group.xml',
		'security/ir.model.access.csv',
		'views/res_partner_bank_view.xml',
		'views/direct_debit_view.xml',
		'views/direct_debit_response_result_view.xml',  
		'views/direct_debit_response_result_code_view.xml',  
		'views/direct_debit_cabecera_view.xml',

	],
}
