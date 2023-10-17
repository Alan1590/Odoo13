# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied
import random, string

import logging
_logger = logging.getLogger(__name__)
#from hikvisionapi import Client

class ResPartnerBank(models.Model):
	_name = "res.partner.bank"
	_inherit = 'res.partner.bank'
	#Cabecera
	is_for_direct_debit = fields.Boolean("Para debito directo")
	debit_owner_id = fields.Many2one("res.partner",string="Propietario")
	type_of_account = fields.Selection ([
			('cta_corriente','Cuenta corriente'),
			('cja_ahorro','Caja de ahorro'),
			],default='cja_ahorro')


	@api.model
	def create(self, vals):
		num_regis = self._get_list_bank_c(vals)
		if num_regis==1 and vals["is_for_direct_debit"]:
			raise ValidationError("Ya existe una cuenta para debito directo")
		else:
			return super(ResPartnerBank, self).create(vals)

	def write(self, values):
		num_regis = self._get_list_bank(self.partner_id)
		if num_regis==1:
			raise ValidationError("Ya existe un cbu asignado para debito directo")
		else:
			res = super(ResPartnerBank, self).write(values)
		return res

	def _get_list_bank(self,partner_id):
		already_asing = self.search([("&"),("partner_id", "=" ,partner_id.id),("is_for_direct_debit", "=", True), ("id", "!=",self.id)])
		return len(already_asing)

	def _get_list_bank_c(self,partner_id):
		already_asing = self.search([("&"),("partner_id", "=" ,partner_id["partner_id"]),("is_for_direct_debit", "=", True)])
		return len(already_asing)
