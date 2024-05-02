# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied
import random, string
import os
import pathlib
import logging
import base64
import datetime
_logger = logging.getLogger(__name__)

class DirectDebit(models.Model):
	_name = "direct.debit"
	_inherit = 'mail.thread'
	#Cabecera
	name = fields.Char("Name",size=256, required=True)
	cabecera_id = fields.Many2one('direct.debit.cabecera')
	date_debit = fields.Date("Fecha debito",required=True)
	real_date_debit = fields.Date("Fecha debito cliente",required=True)
	amount_total = fields.Float("Total amount debit",readonly=True, compute='_compute_amount_total')    
	number_debits = fields.Integer("Number of debit",readonly=True, compute='_compute_number_debit')  
	#Espacios en blanco 9  
	result = fields.Text("Resultado", readonly=True)
	response = fields.Text("Respuesta")
	payments_ids = fields.Many2many("direct.debit.response.result")
	file = fields.Binary(string="Resultado",readonly=True)

	state = fields.Selection ([
		('draft','Draft'),
		('open','Open'),
		('responsed','Responsed'),
		('wait_response','Wait response'),			
		('wait_validation','Wait Validation'),			
		('posted','Posted'),
		],default='draft')

	invoice_ids = fields.Many2many("account.move", 
		domain=[('&'),('state','=','posted'),
				('type','=','out_invoice'),
				('invoice_payment_state', '!=', 'paid')])

	def cancel(self):
		self.state = "draft"

	def _compute_amount_total(self):
		total = 0
		for item in self:
			for inv in item.invoice_ids:
				total += inv.amount_residual
			item.amount_total = total
		return 0

	def _compute_number_debit(self):
		n_debit = 0
		for item in self:
			n_debit = len(self.invoice_ids)
			item.number_debits = n_debit
		return n_debit

	def generate_debits_lines(self):
		path = str(pathlib.Path(__file__).parent.absolute())
		name_file = path+"/debit_files/%s.txt" %self.date_debit
		f = open(name_file, "w")
		header = self._generate_header()
		data = self._generate_data()
		if self._validation_fields(self.invoice_ids):
			self.result = ("%s%s%s") %(header,"\n",data)
			f.write(self.result)
			f.close()
			self.file = base64.b64encode(self.result.encode())
		self.state = 'wait_response'

	def _generate_header(self):
		cabecera = self.cabecera_id
		header = ("%s%s%s%s%s%s%s%s%s%s%s") %(
			cabecera.n_cabecera,
			cabecera.n_company,
			cabecera.n_convenio,
			self.date_debit.strftime("%Y%m%d"), 
			"000001",
			str(('%.3f')%(float(self.amount_total))).replace(".","").zfill(14),
			str(self.number_debits).zfill(6),
			"SERVICIO".ljust(10),
			"".ljust(10),
			self.date_debit.strftime("%Y%m%d"),
			"".ljust(151))
		return header

	def _generate_data(self):
		type_account = {'cta_corriente':'00', 'cja_ahorro':'01'}
		res_nbsf = "0000"
		cod_oper = "01"
		date_debit = self.date_debit.strftime("%Y%m%d")
		dest_cbu = self.env.company.vat
		reverso = "O"
		trace_original = "".ljust(15)
		uso_interno = "".ljust(105)
		str_result = ""
		for invoices in self.invoice_ids:
			amount_invoice = str(('%.3f')%(float(invoices.amount_residual))).replace(".","").zfill(14)
			nro_comprobante = str(invoices.id).zfill(10)
			partner_bank = self._get_partner_bank(invoices.partner_id)
			sistema = type_account[partner_bank.type_of_account]
			partner_name = partner_bank.debit_owner_id.name.replace(" ","")[:16].ljust(16).upper()
			ref_uniq = str(invoices.id)
			str_result += ("%s%s%s%s%s%s%s%s%s%s%s%s%s%s" %(
				sistema,
				res_nbsf,
				str(partner_bank.acc_number).zfill(22),
				cod_oper,
				amount_invoice,
				self.real_date_debit.strftime("%Y%m%d"),
				str(invoices.partner_id.id).zfill(10),
				str(dest_cbu).zfill(11),
				partner_name,
				ref_uniq.ljust(15).upper(),
				" ",
				trace_original,
				uso_interno,
				"\n"))
		return str_result

	def _get_partner_bank(self,partner_id):
		partner_bank = self.env['res.partner.bank'].search([("&"),("partner_id","=",partner_id.id),("is_for_direct_debit","=",True)])
		return partner_bank

	def _get_invoice(self,invoice_id):
		invoice = self.env['account.move'].search([("id","=",invoice_id)])
		return invoice


	def fill_invoices(self):
		invoices_ids = self._get_all_invoices()
		self.invoice_ids = invoices_ids
		self.state = 'open'

	def _get_all_invoices(self):
		partner_bank = self.env['res.partner.bank'].search([("is_for_direct_debit","=",True)])
		invoice = self.env['account.move'].search([('&'),('state','=','posted'),
				('type','=','out_invoice'),
				('invoice_payment_state', '!=', 'paid'),("partner_id","in",partner_bank.partner_id.ids)])
		return invoice	

	def _validation_fields(self, invoice_ids):
		diferences = self.real_date_debit - self.date_debit 
		if diferences.days < 3:
			raise ValidationError("La diferencia entre fecha debe ser minimo 3 dias")
		elif self.real_date_debit.isoweekday() == 6 or self.real_date_debit.isoweekday() == 7:
			raise ValidationError("La fecha de debito no puede ser en fin de semana")
		for invoice in invoice_ids:
			partner_bank = self._get_partner_bank(invoice.partner_id)
			if not partner_bank:
				raise ValidationError("El cliente %s no posee un cbu para debito directo asignado" %invoice.partner_id.name)
			elif len(partner_bank.acc_number) < 22:
				raise ValidationError("El cliente %s posee un cbu no valido (22 digitos)" %invoice.partner_id.name)
		return True

	def process_response(self):
		if not self.response:
			raise ValidationError("Campo de respuesta vacio")
		else:
			try:
				response = self.response.split("\n")
				cabecera = self._procces_cabecera(response[0])
				datos = self._procesar_registros(response[1:])
				#raise ValidationError(datos)
				self._procesar_pagos(datos)

			except Exception as e:
				raise ValidationError(e)

	def _procesar_pagos(self,resultado):
		for pago in resultado:
			raise ValidationError('%.2f' % float(int(pago['r_importe'])))
			invoice = self._get_invoice(pago['r_referencia'].replace(" ",""))
			id_response = self.env["direct.debit.response.result"].create({
				'debit_id':self.id,
				'invoice_id':invoice.id,
				'partner_id':invoice.partner_id.id,
				'amount':'%.2f' % float(int(pago['r_importe'])),
				})
			self.payments_ids = [(4,id_response.id)]
		self.state = 'wait_validation'

	def validate_response(self):
		for item in self.payments_ids:
			inv_id = self.__get_invoice_from_move_line(item.invoice_id.id,
					item.invoice_id.name).id
			if item.state == '0000':
				vals = {
				'to_pay_move_line_ids': [(6,0,[inv_id])],
				'partner_id':item.invoice_id.partner_id.id,
				'notes':'Payment from direct debit',
				'partner_type':'customer',
				'company_id':1,
				}
				id_receipt = self.env['account.payment.group'].create(vals)
				self.__create_payment(item.amount,id_receipt)
				self.payments_ids = [(1,item.id,{'receipt_id':id_receipt})]
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

	def _get_data_invoice(self,id_invoice):
		invoice = self.env['account.move'].search([('id','=',id_invoice)])
		return invoice

	def _procces_cabecera(self,cabecera):
		try:
			r_cabecera = {
			'c_cabecera': cabecera[0:3],
			'c_empresa': cabecera[4:7],
			'c_convenio': cabecera[8:11],
			'c_fecha_respuesta': cabecera[12:21],
			'c_n_archivo': cabecera[22:27],
			'c_total': cabecera[28:41],
			'c_n_registros': cabecera[42:47],
			'c_observacion': cabecera[48:],
			}
		except Exception as e:
			raise ValidationError(e)
		return 

	def _procesar_registros(self,registros):
		l_reg = []
		for reg in registros:
			reg.replace(" ","")
			#raise ValidationError(reg)
			l_reg.append({
				'r_registro': reg[0:2],
				'r_reservado': reg[3:7],
				'r_cbu': reg[8:30],
				'r_cod_operacion': reg[31:33],
				'r_importe': reg[33:44],
				'r_fecha_imputacion': reg[44:52],
				'r_n_comprobante': reg[52:62],
				'r_cuit_cuil_dni': reg[62:73],
				'r_den_cuenta': reg[73:89],
				'r_referencia': reg[89:104],
				'r_reverso': reg[104:105],
				'r_trace_original': reg[105:120],
				'r_dest_debito': reg[120:122],
				'r_cod_rechazo': reg[122:125],
				'r_desc_rechazo': reg[125:155],
				'r_trace': reg[155:170],
				'r_trace_camara': reg[170:185],
				'r_fecha_real_imputacion': reg[185:193],
				'r_empresa': reg[193:197],
				'r_convenio': reg[197:201],
				'r_fecha_archivo': reg[201:209],
				'r_n_archivo': reg[209:215],
				'r_observacion': reg[215:],
				})
		return l_reg

class DirectDebitCabecera(models.Model):
	_name = "direct.debit.cabecera"
	name = fields.Char("Nombre",size=128, required=True)
	n_cabecera = fields.Char("Numero cabecera",size=4, required=True)
	n_company = fields.Char("Numero compania",size=4, required=True)
	n_convenio = fields.Char("Numero convenio",size=4, required=True)

	@api.model
	def create(self, vals):
		if len(vals['n_cabecera']) < 4:
			raise ValidationError("El campo cabecera no cumple con el minimo de digitos (4)")
		elif len(vals['n_company']) < 4:
			raise ValidationError("El campo compañia no cumple con el minimo de digitos (4)")
		elif len(vals['n_convenio']) < 4:
			raise ValidationError("El campo convenio no cumple con el minimo de digitos (4)")
		return super(DirectDebitCabecera, self).create(vals)		

	def write(self, vals):
		if 'n_cabecera' in vals:
			if len(vals['n_cabecera']) < 4:
				raise ValidationError("El campo cabecera no cumple con el minimo de digitos (4)")
		elif 'n_company' in vals:
			if len(vals['n_company']) < 4:
				raise ValidationError("El campo compañia no cumple con el minimo de digitos (4)")
		elif 'n_convenio' in vals:
			if len(vals['n_convenio']) < 4:
				raise ValidationError("El campo convenio no cumple con el minimo de digitos (4)")
		res = super(DirectDebitCabecera, self).write(vals)
		return res

