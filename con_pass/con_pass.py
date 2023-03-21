# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied
import random, string

import logging
_logger = logging.getLogger(__name__)
#from hikvisionapi import Client

class GeneralPass(models.Model):
    _name = "general.pass"
    _inherit = 'mail.thread'
    name = fields.Char("Clave desbloqueo", size=256)
    identification = fields.Char("Nombre", size=256, required=True)
    users_ids = fields.Many2many("general.pass.user")
    note = fields.Text("Notas")
    unlocked_pass = fields.Char("Unblock pass", size=12, readonly=True)

    state = fields.Selection ([
            ('bloqued','Bloqueado'),
            ('unbloqued','Desbloqueado'),
            ],default='unbloqued')
    
    @api.model
    def create(self, vals):
        if self.unlocked_pass == False:
            unlocked_pass = self.generate_pass()
            vals['unlocked_pass'] = unlocked_pass
        else:
            vals['unlocked_pass'] = self.unlocked_pass            
        vals['state'] = 'bloqued'
        rec = super(GeneralPass, self).create(vals)
        return rec

    def post_message(self):
        if self.name == self.unlocked_pass:
            message = "Claves desbloqueadas %s" %self.env.user.name
            self.state = 'unbloqued'
            self.message_post(body=message)
        else:
            raise AccessDenied(_("Clave de desbloqueo incorrecta."))

    def automated_bloqued(self):
        list_to_bloqued = self._get_list_bloqued()
        self._block_devices(list_to_bloqued)
        list_alarm_bloqued = self._get_list_bloqued_alarm()
        self._block_devices(list_alarm_bloqued)


    def _block_devices(self,list_to_bloqued):
        unlocked_pass = self.generate_pass()
        for item in list_to_bloqued:
            item.name = ''
            item.state = 'bloqued'
            item.unlocked_pass = unlocked_pass        

    def generate_pass(self):
        letters = string.hexdigits
        result_str = ''.join(random.choice(letters) for i in range(10))
        return result_str.strip().replace(" ","")

    def _get_list_bloqued(self):
        domain = self.search([
        ('state', 'in', ['unbloqued']),
        ])
        return domain

    def _get_list_bloqued_alarm(self):
        domain = self.env['alarm.central'].search([('state','in',['unbloqued'])])
        return domain

class GeneralPassUsers(models.Model):
    _name = "general.pass.user"
    name = fields.Char("Usuario", size=256)
    password = fields.Char("Password", size=256)   



