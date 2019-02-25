from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class Partner(models.Model):
    _inherit = 'res.partner'

    def _compute_need_action(self):
        overdue_only = 'action' == 'all'
        ids = []
        partners = self.env['res.partner'].get_partners_in_need_of_action(overdue_only=overdue_only)
        for partner in partners:
            ids.append(partner.id)
            partner.need_action = True
        partner2 = self.env['res.partner'].search([('id', 'not in', ids), ('customer', '=', True)])
        for partner in partner2:
            partner.need_action = False

    wizard_print = fields.Boolean('Print/Email from a wizard')
    need_action = fields.Boolean(compute='_compute_need_action', string='Need action')

    def print_statement(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference\
                                           ('customer_statement', 'print_statement_form_custom')

        return {
            'name':"Customer Statement",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'customer.statement',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    @api.multi
    def button_view_statement(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.client',
            'tag': 'account_report_followup',
            'name': self.name,
            'context': {'model': 'account.followup.report'},
            'options': {'partner_id': self.id},
        }

    @api.multi
    def button_send_followup_emails(self):
        is_one = len(self) == 1

        for record in self:
            try:
                self.env['account.followup.report'].send_email({
                    'partner_id': record.id,
                })
            except:
                if is_one:
                    raise
