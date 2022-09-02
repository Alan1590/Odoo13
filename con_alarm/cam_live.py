# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)

class FirstData(models.Model):
	DUES_PLAN = "001"
	DUES = 999
	FRECUENCIE_DB = 1
	MONTHS = {
	'01':'Ene',
	'02':'Feb',
	'03':'Mar',
	'04':'Abr',
	'05':'May',
	'06':'Jun',
	'07':'Jul',
	'08':'Ago',
	'09':'Sep',
	'10':'Oct',
	'11':'Nov',
	'12':'Dic',
	}
	_name = "first.data"
	name = fields.Char("Name",size=256, required=True)
	number_company = fields.Char("Number company",size=8, required=True)
	type_register = fields.Char("Type Register", size=2)
	presentation_date = fields.Date("Date presentation",required=True)
	expired_date = fields.Date("Expired date",required=True)
	number_debits = fields.Integer("Number of debit",readonly=True)
	amount_debits = fields.Float("Total amount debit",readonly=True)
	filters = fields.Many2one("account.move.extension",required=True)
	filters_journal_id = fields.Many2one('account.journal')
	list_invoices = fields.Many2many("account.move", 
		domain=[('&'),('state','=','posted'),
				('type','=','out_invoice'),
				('invoice_payment_state', '!=', 'paid')])
	send_result = fields.Text("Result")
	get_response = fields.Text("Response")
	include_partner = fields.Boolean("Include partner on search")
	procesed_response = fields.Many2many("first.data.response", ondelete="cascade", readonly=True)
	journal_id = fields.Many2one("account.journal",
		domain=[('|'),('type','=','cash'),('type','=','bank')])
	state = fields.Selection ([
		('draft','Draft'),
		('open','Open'),
		('responsed','Responsed'),
		('wait_validation','Wait validation'),			
		('posted','Posted'),
		],default='draft')


	@api.onchange('expired_date')
	def __restrict_date(self):
		if self.expired_date < self.presentation_date:
			raise ValidationError("Expired date can not we minor to presentation date")

	def _generate_header(self):
		header = ("%s%s%s%s%s%s%s%s") %(str(self.number_company).zfill(8),str(1),
			self.presentation_date.strftime("%d%m%y"), str(self.number_debits).zfill(7),0,
			str(('%.2f')%(float(self.amount_debits))).replace(".","").zfill(14),"".ljust(91),"\n")
		return header

	def generate_line_debits(self):
		body = []
		self.send_result=""
		self._get_cost_and_number_debit()

		header = self._generate_header()
		self.send_result += header
		for item in self.list_invoices:
			n_comer = self.number_company
			cbu = self._data_of_cbu_from_partner(item['partner_id'])
			ref = item['id']
			#DUES
			#DUES_PLAN
			#FRECUENCIE_DB
			amount = str(('%.2f')%(float(item['amount_residual']))).replace(".","").zfill(11)
			date_format = str(self.presentation_date).split("-")
			period = ('%s%s') %(self.MONTHS[date_format[1]],date_format[0][:2])
			filler = "".ljust(1)
			date_final = str(self.expired_date).replace("-","")
			data_aux = "".zfill(40)
			if not cbu:
				raise Warning("The field cbu is empty or dont have type of payment 'first data' on the partner %s" %item['partner_id'].name)

			self.send_result += ("%s%s%s%s%s%s%s%s%s%s%s%s%s%s") %(n_comer,2,cbu.zfill(16),
				str(ref).zfill(12),str(self.DUES_PLAN).zfill(2),str(self.DUES).zfill(2)
				,str(self.FRECUENCIE_DB).zfill(2),
				amount,period,filler,date_final[2:],data_aux,"".zfill(20),'\n')
			self.state = 'open'
		return body

	def process_response(self):
		if not self.get_response:
			raise Warning("The field response is empty")
		else:
			response = self.get_response.split("\n")
			details = ''
			list_response = []
			for lines in response:
				amount = lines.split(";")[7].replace('\"','')
				invoice_data = self.__get_invoice(lines.split(";")[1])
				state_payment = lines.split(";")[9].replace('\"','')
				if lines.split(";")[11].replace('\"','') != '':
					details = lines.split(";")[11].replace('\"','') 
				else:
					details = "ACPT"
				list_response.append({
				'first_data_id': self.id,
				'invoice_id': invoice_data.id,
				'partner_id': invoice_data.partner_id.id,
				'amount':amount,
				'details':details,
				'state_payment':state_payment,
				})
			for res in list_response:
				if not self.__is_load(res['invoice_id'],self.id):
					id_first_data_responsed = self.env['first.data.response'].create(res)
					self.procesed_response = [(4,id_first_data_responsed.id)]
			self.state="wait_validation"

	def __is_load(self,id_invoice,first_data_id):
		already_load = self.env['first.data.response'].search([('&'),
			('invoice_id','=',id_invoice),('first_data_id','=',first_data_id)])
		return already_load
		
	def __get_invoice(self,inv_id):
		invoice = self.env['account.move'].search([('&'),('state','=','posted'),('id','=',inv_id)])
		return invoice	

	def _data_of_cbu_from_partner(self, partner_id):
		partner_bank = self.env['res.partner.bank'].search([('&'),
			('partner_id','=',partner_id.id),('type_of_debit','=',self.filters.id)])
		if len(partner_bank) > 1:
			raise Warning('The partner %s have more 1 type of debit %s' %(partner_id.name, len(partner_bank)))
		cbu = partner_bank['acc_number']
		return cbu

	@api.onchange('list_invoices')
	def _get_cost_and_number_debit(self):
		total_amount = 0
		self.number_debits = len(self.list_invoices)
		for item in self.list_invoices:
			total_amount += item['amount_residual']
		self.amount_debits = total_amount


	def fill_invoices(self):
		invoices_ids = []
		if not self.filters:
			raise Warning("List of filter is empty")
		if self.include_partner:
			result_partner = self.env['res.partner.bank'].search(
				[('type_of_debit','=',self.filters.id)])
			for item in result_partner:
				id_invoice = self.__get_list_of_invoice_for_partner(item['partner_id'],self.filters_journal_id)
				_logger.warning(id_invoice)
				for linv in id_invoice:
					invoices_ids.append(linv['id'])
		else:				
			for item in self.__get_list_of_invoices(self.filters_journal_id):
				invoices_ids.append(item['id'])
		self.list_invoices = [(6, 0,invoices_ids)]
		self._get_cost_and_number_debit()

	#Search list of invoice ignoring type of payment in invoice, instead, 
	#search based on type of payment in bank
	def __get_list_of_invoice_for_partner(self, partner_id, journal_id):
		result_invoice = []
		result_invoice = self.env['account.move'].search([('&'),('state','=','posted'),
					('type','=','out_invoice'),('invoice_payment_state', '!=', 'paid'),
					('partner_id','=',partner_id.id),('journal_id', '=', journal_id.id)])
			

		return result_invoice

	#Search list of invoices taking into account the type of payment 
	def __get_list_of_invoices(self,journal_id):
		result = []
		result = self.env['account.move'].search([('&'),('state','=','posted'),
				('type','=','out_invoice'),
				('type_payment_id','=',self.filters.id),
				('invoice_payment_state', '!=', 'paid'),('journal_id', '=', journal_id.id)])
		return result


	def validate_response(self):
		for item in self.procesed_response:
			inv_id = self.__get_invoice_from_move_line(item.invoice_id.id,
					item.invoice_id.name).id
			if item.state_payment != 'Rechazado' and item.invoice_id.invoice_payment_state != "paid":
				vals = {
				'to_pay_move_line_ids': [(6,0,[inv_id])],
				'partner_id':item.partner_id.id,
				'notes':'Payment for first data',
				'partner_type':'customer',
				'company_id':1,
				}
				id_receipt = self.env['account.payment.group'].create(vals)
				self.__create_payment(item.amount,id_receipt)
				self.procesed_response = [(1,item.id,{'receipt_id':id_receipt})]
		self.state = 'posted'

	def __get_invoice_from_move_line(self,id_invoice,inv_name):
		search_value = self._get_to_pay_move_lines_domain(id_invoice)
		vals = self.env['account.move.line'].search(search_value)
		if vals == False:
			raise Warning("Te invoice with id %s is already paid" %inv_name)
		else:
			return vals		

	def _get_to_pay_move_lines_domain(self,move_id):
	        self.ensure_one()
	        return [
	            ('move_id', '=',
	                move_id),
	        ('account_id.reconcile', '=', True),
            ('move_id.type', 'in', ['out_invoice']),
            ('reconciled', '=', False),
            ('full_reconcile_id', '=', False),
#            ('company_id', '=', 1),
#            ('company_id', '=', 1),
	        ]

	def __create_payment(self,amount,id_receipt):
		vals = {
		'payment_group_id': id_receipt.id,
		'payment_type':'inbound',
		'payment_method_id':2,
		'journal_id': self.journal_id.id,
		'amount':amount,
		'partner_type':'customer'
		}
		self.env['account.payment'].create(vals)
		
		return vals

	def cancel(self):
		self.state = 'draft'

	def reject_response(self):
		for response in self.procesed_response:
			self.procesed_response = [(2,response.id)]
		self.state = 'open'

class FirstDataResponse(models.Model):

	_name ="first.data.response"


	invoice_id = fields.Many2one('account.move','Invoice')
	first_data_id = fields.Many2one ('first.data','first_data_id')
	receipt_id = fields.Many2one('account.payment.group','Receipt')
	partner_id = fields.Many2one('res.partner','Partner')
	amount = fields.Float('Amount')
	details = fields.Selection (
		[
		('000','Indicación de transacción aceptada o tarjeta con cambio de numero'),
		('001','Comercio informado no existe o dado de baja / Marca de la tarjeta no habilitada para el comercio'),
		('013','Falta importe de Debito'),
		('014','Importe del débito invalido'),
		('015','Adhesión dada de baja'),
		('017','Cuota referencia ya fue ingresada'),
		('050','Causa de rechazo en boletín'),
		('061','Socio dado de baja en maestro'),
		('062','Tarjeta vencida'),
		('063','Cantidad de cuotas del plan inválida'),
		('064','Tarjeta privada en comercio no autorizado'),
		('065','Tarjeta no vigente'),
		('066','Tarjeta inexistente'),
		('072','Cuota inicial invalida'),
		('073','Frecuencia de debilitación inválida'),
		('075','Número de referencia inválido'),
		('081','Comercio no autorizado a operar en dólares'),
		('083','Entidad Pagadora inexistente'),
		('085','Stop Debit'),
		('086','Autorización inexistente o rechazada'),
		('087','Importe supera tope /débito acotado'),
		('088','Autorización rechazada socio en mora'),
		('089','Autorización rechazada socio Líder'),
		('090','Imp. Cupón crédito supera suma ult. deb'),
		('091','Adh. Inexstente para cupón crédito'),
		('092','Socio internacional p/cupón crédito'),
		('CT','Observación: Cambio de Tarjeta'),
		('ACPT','Aceptado'),
		]
		,default='draft')
	state_payment = fields.Selection([
		('Aceptado','Aceptado'),
		('Rechazado','Rechazado'),
		])

