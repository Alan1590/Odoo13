# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError,AccessDenied
import random, string

import logging
_logger = logging.getLogger(__name__)
#from hikvisionapi import Client

class AlarmCentral(models.Model):
    _name = "alarm.central"
    _inherit = 'mail.thread'
    name = fields.Char("Clave desbloqueo", size=256)
    partner_id = fields.Many2one("res.partner","Cliente")
    contract_id = fields.Many2one("contract.contract","Contract")
    product_id = fields.Many2one("product.product","Product")
    panel_id = fields.Char("Panel id", size=8)
    serial_central = fields.Char("SN Central",size=128)
    firmware_version = fields.Char("Firmware version", size=128)
    installer_code = fields.Char("Codigo instalador",size=128)
    site_id = fields.Char("Id del sitio", size=256)
    email = fields.Char("Email", size=256)
    pc_pass = fields.Char("Pc Pass", size=8)
    hik_installer_code = fields.Char("Cod. Instalador",size=64)
    hik_cod_admin = fields.Char("Cod. Administrador",size=64)
    hik_cod_mant = fields.Char("Cod. Mantenimiento", size=64)
    hik_cod_operador = fields.Char("Cod. Operador", size=64)
    comunicator_ids = fields.Many2many("alarms.comunicator")
    unlocked_pass = fields.Char("Unblock pass", size=12, readonly=True)
    state = fields.Selection ([
            ('bloqued','Bloqueado'),
            ('unbloqued','Desbloqueado'),
            ],default='unbloqued')

#    def get_version(self):
#        cam = Client('http://192.168.0.2', 'admin', 'admin')
#        response = cam.System.deviceInfo(method='get')
#        raise Warning(response)

    @api.onchange('contract_id')
    def _onchange_contract(self):
        if self.contract_id:
            partner_id = self.contract_id.partner_id
            self.partner_id = partner_id

    
    @api.model
    def create(self, vals):
        if self.unlocked_pass == False:
            unlocked_pass = self.generate_pass()
            vals['unlocked_pass'] = unlocked_pass
        else:
            vals['unlocked_pass'] = self.unlocked_pass          
        vals['state'] = 'bloqued'
        rec = super(AlarmCentral, self).create(vals)

        return rec

    def write(self, vals): 
        res = super(AlarmCentral, self).write(vals)

        return res

    def generate_pass(self):
        letters = string.hexdigits
        result_str = ''.join(random.choice(letters) for i in range(10))
        return result_str.strip().replace(" ","")

    def post_message(self):
        if self.name == self.unlocked_pass:
            message = "Claves desbloqueadas %s" %self.env.user.name
            self.state = 'unbloqued'
            self.message_post(body=message)
        else:
            raise AccessDenied(_("Clave de desbloqueo incorrecta."))

class AlarmsComunicators(models.Model): 
    _name = "alarms.comunicator"
    com_model = fields.Many2one("alarm.comunicators.model","Tipo comunicador")
    com_serial = fields.Char("Serial", size=128)
    com_password = fields.Char("Password", size=128) 


class AlarmsComunicatorsModel(models.Model):
    _name = "alarm.comunicators.model"
    name = fields.Char("Nombre", size=16)

class AlarmHikvisionModel(models.Model):
    _name = "alarm.hikvision.model"


    



