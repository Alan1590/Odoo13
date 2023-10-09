# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)

class ResPartnerBank(models.Model):
	"""docstring for ClassName"""
	_inherit = "res.partner.bank"
	type_of_debit = fields.Many2one("account.move.extension", required=True)

	@api.model
	def create(self, values):
		partner_bank = super(ResPartnerBank, self).create(values)
		exist_cbu_type = self.search([('&'),('partner_id','=',values['partner_id']),
					('type_of_debit','=',values['type_of_debit'])])
		if len(exist_cbu_type)>1:
			raise ValidationError("Already exist this type of payment for this partner")
		return partner_bank

	def check_duplication(self):
	    message = {


	       'type': 'ir.actions.client',

	       'tag': 'display_notification',

	       'params': {

	           'title': _('Warning!'),

	           'message': 'This cbu is already loaded on other/s partner/s',

	           'sticky': False,

	       }
	    }
	    exist_cbu = False
	    exist_cbu = self.search([('acc_number','=',self.acc_number)])
	    if len(exist_cbu) > 1:
	    	return message
	    else:
	    	return {
		       'type': 'ir.actions.client',

		       'tag': 'display_notification',

		       'params': {

		           'title': _('Information!'),

		           'message': 'This cbu is unique',

		           'sticky': False,
					    }
		    		}


