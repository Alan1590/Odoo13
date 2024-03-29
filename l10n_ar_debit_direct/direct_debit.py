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

	def fill_invoices(self):
		invoices_ids = self._get_invoices()
		self.invoice_ids = invoices_ids
		self.state = 'open'

	def _get_invoices(self):
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
				datos = self._procesar_registros(response[1])
				self._procesar_pagos(datos)

			except Exception as e:
				raise ValidationError(e)

	def _procesar_pagos(self,resultado):
		for pago in resultado:
			invoice = self._get_invoices(pago['r_referencia'])
			self.env["direct.debit.response.result"].create({
				'invoice_id':invoice.id,
				'debit_id':self.id,
				'receipt_id':pago['r_referencia'],
				'partner_id':invoice.partner_id,
				'amount':pago['r_importe'],
				})
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
		for reg in registros.split("\n"):
			l_reg.append({
			'r_registro': registros[0:1],
			'r_reservado': registros[2:5],
			'r_cbu': registros[6:27],
			'r_cod_operacion': registros[28:29],
			'r_importe': registros[29:42],
			'r_fecha_imputacion': registros[43:50],
			'r_n_comprobante': registros[51:60],
			'r_cuit_cuil_dni': registros[61:71],
			'r_den_cuenta': registros[72:87],
			'r_referencia': registros[88:102],
			'r_reverso': registros[103:103],
			'r_trace_original': registros[104:118],
			'r_dest_debito': registros[119:120],
			'r_cod_rechazo': registros[121:123],
			'r_desc_rechazo': registros[124:153],
			'r_trace': registros[154:168],
			'r_trace_camara': registros[169:183],
			'r_fecha_real_imputacion': registros[184:191],
			'r_empresa': registros[192:195],
			'r_convenio': registros[196:199],
			'r_fecha_archivo': registros[200:207],
			'r_n_archivo': registros[208:213],
			'r_observacion': registros[214:],
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

