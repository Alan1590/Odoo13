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
	notified_ids = fields.Many2many("notify.debtor.notified",readonly=True)
	init_date = fields.Date("Fecha inicio",required=True)
	end_date = fields.Date("Fecha final",required=True)
	notify_debtor_partner_ids = fields.Many2many("notify.debtor.partner",readonly=True)
	template_id = fields.Many2one("notify.debtor.template",required=True)

	state = fields.Selection ([
			('new','Nuevo'),
			('open','En tratamiento'),
			('close','finalizado'), 			
			],default='new')

	def unlink(self):
		self.env["notify.debtor.notified"].search([('notify_id', '=', self.id),]).unlink()
		return super(NotifyDebtor, self).unlink()

	def get_invoices(self):
		lnotify_ids = []
		lpartner_ids = []
		invoice_ids = self._get_list_invoices(self.init_date, self.end_date)
		for inv in invoice_ids:
			total_invoices = 0
			invoices_for_partner = self._get_list_invoices_partner(self.init_date, self.end_date,inv.partner_id.id)
			n_invoices = len(invoices_for_partner)
			for id_invoice in invoices_for_partner:
				total_invoices += id_invoice.amount_residual
			if inv.partner_id.id not in lpartner_ids:
				l_notify = self.env['notify.debtor.partner'].create({
					'partner_id': invoices_for_partner.partner_id.id,
					'telephone': invoices_for_partner.partner_id.mobile,					
					'num_notification': 0,
					'n_invoices': n_invoices,
					'amount_toltal_invoices': total_invoices,
					'alredy_notified': 'not_notified',
				})
				lnotify_ids.append(l_notify.id)
			lpartner_ids.append(inv.partner_id.id)
		self.write({'notify_debtor_partner_ids': [(6,0,lnotify_ids)] })
		self.state = 'open'
		return lpartner_ids

	def close(self):
		self.state = 'close'

	def _get_list_notified(self):
		l_notified = self.env["notify.debtor.notified"].search([('notify_id', '=', self.id),])
		l_ids = []
		for ids_notified in l_notified:
			l_ids.append(ids_notified.id)

		return l_ids

	def _get_list_invoices_partner(self,init_date,end_date, partner_id):
		l_invoices = self.env["account.move"].search([("&"),('invoice_date_due', '>', init_date),('invoice_date_due', '<', end_date)
			,('state','=','posted'),('type','=','out_invoice'),('invoice_payment_state', '!=', 'paid'),
			('partner_id', '=', partner_id)])
		return l_invoices	


	def _get_list_invoices(self,init_date,end_date):
		l_invoices = self.env["account.move"].search([("&"),('invoice_date_due', '>', init_date),('invoice_date_due', '<', end_date)
			,('state','=','posted'),('type','=','out_invoice'),('invoice_payment_state', '!=', 'paid')])
		return l_invoices	

class NotifyDebtorPartner(models.Model):
	_name="notify.debtor.partner"
	partner_id = fields.Many2one("res.partner",readonly=True)
	telephone = fields.Char("Telefono",size=256, readonly=True)
	num_notification = fields.Integer("Num envios", readonly=True)
	n_invoices = fields.Integer("Num facturas", readonly=True)
	amount_toltal_invoices = fields.Float("Total facturas", readonly=True)
	notified_ids = fields.Many2many("notify.debtor.notified",readonly=True)

	alredy_notified = fields.Selection ([
			('notified','Notificado'),
			('not_notified','No notificado'),
			],default='not_notified')

	def _get_list_invoices_partner(self, partner_id, init_date, end_date):
		l_invoices = self.env["account.move"].search([("&"),('invoice_date_due', '>', init_date),('invoice_date_due', '<', end_date)
			,('state','=','posted'),('type','=','out_invoice'),('invoice_payment_state', '!=', 'paid'),
			('partner_id', '=', partner_id)])
		return l_invoices


	def send_wp(self):
		client_action = {}
		debtor = self.env["notify.debtor"].search([("id","=",self.env.context.get("parent_id"))])
		if debtor.state == 'close':
			raise ValidationError("El documento se encuentra cerrado")
		l_invoices = self._get_list_invoices_partner(self.partner_id.id,debtor.init_date,debtor.end_date)
		if len(l_invoices) == 0:
			client_action = {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': ('Informacion'),
					'message': 'El cliente seleccionado ya no posee facturas pendientes, se elimina',
					'type':'info',  #types: success,warning,danger,info
					'sticky': True,  #True/False will display for few seconds if false
				},
			}
			self.unlink()
		else:
			amount_total = self.amount_toltal_invoices
			message = self._get_message(self.partner_id.name,self.amount_toltal_invoices,self.partner_id.email)
			phone = self._get_telphone()
			url = ("https://wa.me/{}?text={}".format(phone,message))
			client_action = {

			'type': 'ir.actions.act_url',

			'name': "sendWP",

			'target': 'new',

			'url': url,

			}
		return client_action

	def is_notified(self):
		debtor = self.env["notify.debtor"].search([("id","=",self.env.context.get("parent_id"))])
		
		if debtor.state == 'close':
			raise ValidationError("El documento se encuentra cerrado")

		return {'type': 'ir.actions.act_window',
			'name': _('Is notified'),
			'res_model': 'notify.debtor.notified',
			'target': 'new',
			'view_mode': 'form',
			'context': {'default_notify_id': self.env.context.get("parent_id"), 'default_partner_id': self.partner_id.id, 
			'default_notify_debtor_partner':self.id}
			}

	def _get_message(self,partner_name, amount_total, partner_email):
		debtor = self.env["notify.debtor"].search([("id","=",self.env.context.get("parent_id"))])
		message = debtor.template_id.text
		if partner_email == False:
			raise ValidationError("El campo email se encuentra vacio")
		else:
			message = message.replace("partner",partner_name).replace("amount_total",str(amount_total)).replace("email",partner_email).replace(" ","%20").replace("\n","%0A") 
		return message

	def _get_telphone(self):
		mobile = self.partner_id.mobile
		if not mobile:
			raise ValidationError("El cliente no posee telefono asignado")
		else:
			mobile = self._format_number(mobile)
			return mobile
			

	def _format_number(self, mobile):
		if len(mobile) < 6:
			raise ValidationError("La cantidad de digitos no es correcto.")
		else:
			prefix = self._get_prefix(self.partner_id.city)
			mobile = prefix +  mobile.strip()[-6:]
		return mobile.replace("-","")


	def _get_prefix(self,city):
		result = self.env["city.prefix"].search([('name', '=', city),])
		if result:
			return "%s9%s" %((self.partner_id.country_id.phone_code), result.prefix)
		else:
			raise ValidationError("No existe prefijo para esta ciudad.")


class NotifyDebtorNotified(models.Model):
	_name = "notify.debtor.notified"
	name = fields.Char("Mensaje", size=256, required=True,readonly=False)
	notify_id = fields.Many2one("notify.debtor", readonly=True)
	partner_id = fields.Many2one("res.partner",readonly=True)
	
	@api.model
	def create(self,vals):
		debtor_partner_id = self._get_partner_id(self.env.context.get("default_notify_debtor_partner"))
		n_not = debtor_partner_id.num_notification + 1
		debtor_partner_id.num_notification = n_not
		debtor_partner_id.alredy_notified = 'notified'
		res = super(NotifyDebtorNotified, self).create(vals)
		debtor_partner_id.notified_ids = [(4,res.id)]
		return res


	def _get_partner_id(self,partner_id):
		return self.env["notify.debtor.partner"].search([('id', '=', partner_id)])
