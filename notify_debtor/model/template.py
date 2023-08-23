# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied

import logging
_logger = logging.getLogger(__name__)

class NotifyDebtorTemplate(models.Model):
	_name = "notify.debtor.template"
	name = fields.Char("Nombre", size=256, required=True)
	text = fields.Text("Texto",required=True)


