# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied
import random, string

import logging
_logger = logging.getLogger(__name__)

class NotifyDebtor(models.Model):
	_name = "notify.debtor"
	_inherit = 'mail.thread'
	name = fields.Char("Nombre", size=256, required=True)
	partner_ids = fields.Many2many("res.partner",readonly=True)
	journal_id = fields.Many2one("account.journal", required=True)
	note = fields.Text("Notas")
	init_date = fields.Date("Fecha inicio",required=True)
	end_date = fields.Date("Fecha final",required=True)


	def get_invoices(self):
		invoice_ids = self._get_list_invoices(self.init_date, self.end_date)
		lpartner =[]
		for inv in invoice_ids:
			if inv.partner_id.id not in lpartner:
				lpartner.append(inv.partner_id.id)
		self.partner_ids = [(6,0,lpartner)]
		return lpartner
		
	def _get_list_invoices(self,init_date,end_date):
		l_invoices = self.env["account.move"].search([("&"),('invoice_date_due', '>', self.init_date),('invoice_date_due', '<', self.end_date)
			,('state','=','posted'),('type','=','out_invoice'),('journal_id','=',self.journal_id.id),('invoice_payment_state', '!=', 'paid')])
		return l_invoices

class NotifyDebtorInvoices(models.Model):
	_inherit = "res.partner"
	num_notification = fields.Integer("Num envios", readonly=True)

	def _get_linvoices(self,debtor, partner_id):
		l_invoices = self.env["account.move"].search([("&"),('invoice_date_due', '>', debtor.init_date),('invoice_date_due', '<', debtor.end_date)
			,('state','=','posted'),('type','=','out_invoice'),('invoice_payment_state', '!=', 'paid'),('journal_id','=',debtor.journal_id.id),('partner_id', '=', partner_id)])
		return l_invoices


	def send_wp(self):
		debtor = self.env["notify.debtor"].search([("id","=",self.env.context.get("parent_id"))])

		l_invoices = self._get_linvoices(debtor,self.id)
		amount_total = 0
		for invoices in l_invoices:
			amount_total += invoices.amount_residual

		message = self._get_message(self.name,amount_total,self.email)
		phone = self._get_telphone()
		url = ("https://wa.me/{}?text={}".format(phone,message))
		client_action = {

		'type': 'ir.actions.act_url',

		'name': "sendWP",

		'target': 'new',

		'url': url,

		}
		n_not = self.num_notification + 1 
		self.write({'num_notification': n_not})

		return client_action

	def _get_message(self,partner_name, amount_total, partner_email):
		message = """
		Estimado-a:%20Nos%20comunicamos%20de%20Marinozzi%20Sistemas%20de%20Seguridad,%20tenemos%20registradas%20facturas%20pendientes%20de%20la%20cuenta%20de%20{},%20
		en%20total%20suman%20un%20saldo%20de%20{},%20recuerde%20que%20para%20evitar%20la%20acumulacion%20de%20saldo%20debe%20revisar%20su%20mail%20(allí%20es%20donde%20se%20envían%20todos%20los%20meses%20las%20facturas),%20
		favor%20de%20confirmar%20si%20es%20correcto%20el%20mail%20que%20tenemos%20registrado%20{}%20le%20informamos%20que%20contamos%20con%20la%20opción%20de%20pago%20
		por%20Débito%20Automático%20por%20Tarjeta%20de%20Crédito,%20que%20realizamos%20los%20primeros%20días%20del%20mes,%20lo%20invitamos%20a%20que%20se%20sume%20y%20lograr%20mayor%20practicidad.
		Muchas%20gracias.
		Cordiales%20saludos.""".format(partner_name, amount_total, partner_email) 
		return message

	def _get_telphone(self):
		mobile = self.mobile
		if not mobile:
			raise ValidationError("El cliente no posee telefono asignado")
		else:
			mobile = self._format_number(mobile)
			return mobile
			

	def _format_number(self, mobile):
		if len(mobile) < 6:
			raise ValidationError("La cantidad de digitos no es correcto.")
		else:
			prefix = self._get_prefix(self.city)
			mobile = prefix + mobile[-7:]
		return mobile.replace("-","")


	def _get_prefix(self,city):
		result = self.env["city.prefix"].search([('name', '=', city),])
		if result:
			return result.prefix
		else:
			raise ValidationError("No existe prefijo para esta ciudad.")
