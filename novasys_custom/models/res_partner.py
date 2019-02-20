from odoo import _, api, fields, models
import logging

_logger = logging.getLogger(__name__)

class res_partner(models.Model):
    _inherit = 'res.partner'

    id_number = fields.Char(string='ID Number')
