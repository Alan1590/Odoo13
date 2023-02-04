"""Summary
"""
# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, Warning
from datetime import datetime
import datetime
from dateutil.relativedelta import relativedelta
import ast
import logging

_logger = logging.getLogger(__name__)

class control_contract(models.Model):
	_name = "contract.contract"
	_inherit = "contract.contract"

	external_id = fields.Integer("External ID")
	state_control = fields.Selection ([
		('normal','Normal'),
		('failed_invoice','Sin factura'),
		('failed_period','Erro en periodo'),
		],default='normal')

	@api.model
	def exist_invoice(self,date_invoice,name_contract):
		inv = self.env['account.move'].search([('&'),
			('invoice_date','>=',date_invoice),('invoice_origin','=',name_contract)],)
		return inv

	def control_invoices(self):
		all_contract = self.search([])
		for contract in all_contract:
			invoice_date = contract.recurring_next_date  - relativedelta(months=1)
			inv = self.exist_invoice(invoice_date,contract.name)
			if inv:
				service_start_date = inv[0]['invoice_date'].replace(day=1) - relativedelta(months=1)
				service_end_date = self.last_day_of_month(inv[0]['invoice_date']) - relativedelta(months=1)
				if service_start_date == inv[0]['l10n_ar_afip_service_start'] and service_end_date == inv[0]['l10n_ar_afip_service_end']:
					contract.state_control = 'normal'
				else:
					contract.state_control = 'failed_period'
			else:
				contract.state_control = 'failed_invoice'

	def recurring_create_invoice(self):
		invoice = super(control_contract, self).recurring_create_invoice()
		return invoice

	def last_day_of_month(self,any_day):
		next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
		return next_month - datetime.timedelta(days=next_month.day)

class MasiveContractLine(models.TransientModel):
	_name = "massive.edit.line.contract"

	product_ids = fields.Many2many('product.product','product_id')

	def cancel_multiple_orders(self):
		list_product_to_cancel = []
		for record in self._context.get('active_ids'):
			contract = self.env[self._context.get('active_model')].browse(record)
			contract_lines = self._get_lines_contract(record)
			for lines in contract_lines:
				if lines['product_id'] in self.product_ids:
					lines['is_auto_renew'] = False
					lines['is_canceled'] = True
					lines['date_end'] = datetime.today().strftime('%Y-%m-%d')
				else:
					continue

	def _get_lines_contract(self,contract_id):
		lines = self.env['contract.line'].search([('contract_id','=',contract_id)],)
		return lines

class MasiveContractLine(models.TransientModel):
	_name = "massive.create.invoice.contract"

	def create_invoice_selected(self):
		model_contract = self._context.get('active_model')
		err_contract = []
		for record in self._context.get('active_ids'):
			contract = self.env[model_contract].browse(record)
			try:
				_logger.warning(record)
				res = contract.recurring_create_invoice()
			except Exception as e:
				err_contract.append(e.message)

			






