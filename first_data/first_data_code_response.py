# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, Warning

import logging

class FirstDataCodeResponse(models.Model):
	_name = "first.data.code.response"
	name = fields.Char("Code",required=True,size=3)
	description = fields.Char("Descripcion", required=True, size=256)

	@api.model
	def create(self, vals):
		if len(vals['name']) < 3:
			raise ValidationError("El codigo debe ser de 3 caracteres")
		return super(FirstDataCodeResponse, self).create(vals)
