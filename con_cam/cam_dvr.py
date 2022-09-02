# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied
import random, string

import logging
_logger = logging.getLogger(__name__)
#from hikvisionapi import Client

class Dvr(models.Model):
    _name = "dvr.dvr"
    _inherit = 'mail.thread'
    name = fields.Char("Clave desbloqueo", size=256)
    partner_id = fields.Many2one("res.partner","Cliente")
    firmware_version = fields.Char("Firmware version", size=128)
    ipv4_number = fields.Char("IpV4", size=512)
    port_number = fields.Char("Port")
    ezviz_data = fields.Many2many("dvr.ezviz",track_visibility='onchange')
    list_user = fields.Many2many("dvr.list.user",track_visibility='onchange')
    contract_id = fields.Many2one("contract.contract","Contract")
    product_id = fields.Many2one("product.product","Product",track_visibility='onchange')
    unlocked_pass = fields.Char("Unblock pass", size=12, readonly=True)

    state = fields.Selection ([
            ('bloqued','Bloqueado'),
            ('unbloqued','Desbloqueado'),
            ],default='unbloqued')

#    def get_version(self):
#        cam = Client('http://192.168.0.2', 'admin', 'admin')
#        response = cam.System.deviceInfo(method='get')
#        raise Warning(response)

    
    @api.model
    def create(self, vals):
        if self.unlocked_pass == False:
            unlocked_pass = self.generate_pass()
            vals['unlocked_pass'] = unlocked_pass
        else:
            vals['unlocked_pass'] = self.unlocked_pass            
        vals['state'] = 'bloqued'
        rec = super(Dvr, self).create(vals)
        return rec

    def write(self, vals): 
        res = super(Dvr, self).write(vals)
        return res

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

class DvrUsers(models.Model): 
    _name = "dvr.list.user"
    name_user_dvr = fields.Char("User", size=128)
    pass_user_dvr = fields.Char("Password", size=128) 


class DvrEzviz(models.Model):
    _name = "dvr.ezviz"
    name = fields.Char("Serial number", size=16)
    email_ezviz = fields.Char("Email", size=256)   
    pass_ezviz = fields.Char("Verification code", size=256)



