# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
	"""docstring for ClassName"""
	_inherit = "account.move"

	type_payment_id = fields.Many2one("account.move.extension","Type of payment")


class AccountMoveExtension(models.Model): 
	_name = "account.move.extension"

	name = fields.Char("Name of payment")
