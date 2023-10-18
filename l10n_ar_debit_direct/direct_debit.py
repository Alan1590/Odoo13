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
#from hikvisionapi import Client

class DirectDebit(models.Model):
	_name = "direct.debit"
	_inherit = 'mail.thread'
	#Cabecera
	name = fields.Char("Name",size=256, required=True)
	cabecera_id = fields.Many2one('direct.debit.cabecera')
	date_debit = fields.Date("Fecha debito",required=True)
	amount_total = fields.Float("Total amount debit",readonly=True, compute='_compute_amount_total')    
	number_debits = fields.Integer("Number of debit",readonly=True, compute='_compute_number_debit')  
	#Espacios en blanco 9  
	result = fields.Text("Resultado", readonly=True)
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
		fecha_debito = self.date_debit + datetime.timedelta(days=3)
		for invoices in self.invoice_ids:
			amount_invoice = str(('%.3f')%(float(invoices.amount_residual))).replace(".","").zfill(14)
			nro_comprobante = str(invoices.id).zfill(10)
			partner_bank = self._get_partner_bank(invoices.partner_id)
			sistema = type_account[partner_bank.type_of_account]
			partner_name = partner_bank.debit_owner_id.name.replace(" ","")[:16].ljust(16).upper()
			ref_uniq = invoices.name.replace("-","").replace("/","")
			str_result += ("%s%s%s%s%s%s%s%s%s%s%s%s%s%s" %(
				sistema,
				res_nbsf,
				str(partner_bank.acc_number).zfill(22),
				cod_oper,
				amount_invoice,
				fecha_debito.strftime("%Y%m%d"),
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
		for invoice in invoice_ids:
			partner_bank = self._get_partner_bank(invoice.partner_id)
			if not partner_bank:
				raise ValidationError("El cliente %s no posee un cbu para debito directo asignado" %invoice.partner_id.name)
			elif len(partner_bank.acc_number) < 22:
				raise ValidationError("El cliente %s posee un cbu no valido (22 digitos)" %invoice.partner_id.name)
		return True


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

