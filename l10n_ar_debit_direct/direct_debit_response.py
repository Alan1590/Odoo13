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

class DirectDebitResponseResult(models.Model):
	_name = "direct.debit.response.result"
	_inherit = 'mail.thread'

	invoice_id = fields.Many2one('account.move','Invoice')
	debit_id = fields.Many2one ('direct.debit')
	receipt_id = fields.Many2one('account.payment.group','Receipt')
	partner_id = fields.Many2one('res.partner','Partner')
	amount = fields.Float('Amount')
	state = fields.Many2one("direct.debit.response.result.code")


class DirectDebitResponseResultState(models.Model):
	_name = "direct.debit.response.result.code"
	_inherit = 'mail.thread'

	code = fields.Char("Codigo", size=4, required=True)
	name = fields.Char("Respuesta", size=128, required=True)

