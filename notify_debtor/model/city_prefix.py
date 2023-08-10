# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied
import random, string

import logging
_logger = logging.getLogger(__name__)

class CityPrefix(models.Model):
	_name = "city.prefix"
	name = fields.Char("Nombre", size=256, required=True)
	prefix = fields.Char("Prefijo", size=6, required=True)
