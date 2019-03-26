from odoo import api, fields, models, _
import logging
import math
import json, time, datetime
from odoo.tools.misc import formatLang, format_date
from odoo.tools import append_content_to_html, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_previous_date(year, month):
    """Generator to continuously return the previous month and year."""
    while True:
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        yield datetime.date(year, month, 1)

def last_day_of_month(date):
    if date.month == 12:
        return date.replace(day=31)
    return date.replace(month=date.month+1, day=1) - datetime.timedelta(days=1)


class ReportOverdue(models.Model):
    _inherit = 'res.partner'

    wizard_print = fields.Boolean('Print/Email from a wizard')

    def _age_analysis_get(self, data, statement_date):

        #data.sorted(key=lambda r: r.date)
        values = {
            'current': 0,
            'previous_30': 0,
            'previous_60': 0,
            'previous_90': 0,
            'previous_120': 0,
        }

        today = datetime.datetime.strptime(str(statement_date), '%Y-%m-%d').date()
        dt = get_previous_date(today.year, today.month)

        start_current = datetime.date(today.year, today.month, 1)
        start_previous_30  = next(dt)
        start_previous_60  = next(dt)
        start_previous_90  = next(dt)
        start_previous_120 = next(dt)

        values.update({
            'current_s': start_current,
            'current_e': statement_date,
            'previous_30_s': start_previous_30,
            'previous_30_e': last_day_of_month(start_previous_30),
            'previous_60_s': start_previous_60,
            'previous_60_e': last_day_of_month(start_previous_60),
            'previous_90_s': start_previous_90,
            'previous_90_e': last_day_of_month(start_previous_90),
            'previous_120_s': 'Before',
            'previous_120_e': last_day_of_month(start_previous_120),
        })

        recon = {}
        for line in data:
            recon_id = line['full_reconcile_id']
            if recon_id and line['debit']:
                recon[recon_id] = line['date']

        def _get_period(tr_date):
            if tr_date:
                transaction_date = datetime.datetime.strptime(str(tr_date), '%Y-%m-%d').date()
                if transaction_date >= start_current and transaction_date <= today:
                    return 'current'
                elif transaction_date >= start_previous_30 and transaction_date < start_current:
                    return 'previous_30'
                elif transaction_date >= start_previous_60 and transaction_date < start_previous_30:
                    return 'previous_60'
                elif transaction_date >= start_previous_90 and transaction_date < start_previous_60:
                    return 'previous_90'
                elif transaction_date < start_previous_90:
                    return 'previous_120'
            else:
                return 'previous_120'
        debit = 0
        credit = 0
        for line in data[::-1]:
            date = " "
            if line.full_reconcile_id:
                dates = datetime.datetime.strptime(str(line.full_reconcile_id.create_date), '%Y-%m-%d %H:%M:%S').date()
                statement_date = datetime.datetime.strptime(str(statement_date), '%Y-%m-%d').date()
            if line.full_reconcile_id and dates < statement_date:
                continue
            orig_date = line['date']
            recon_id  = line['full_reconcile_id']
            if recon_id and line['credit']:
                tdate = recon.get(recon_id)
            else:
                tdate = line['date']
            period = _get_period(tdate)
            diff = values[period] + line['debit'] - line['credit']
            if diff < 0 and line['full_reconcile_id']:
                values[period] = 0
                period = _get_period(orig_date)
                values[period] += diff
            values[period] +=  line['debit'] - line['credit']

        return values

    def _lines_get2(self, partner, statement_date):
        moveline_obj = self.env['account.move.line']

        args = [('partner_id', '=', partner.id),
                    ('account_id.user_type_id.name', 'in', ['Receivable', 'Payable']
                    ),
                    ('move_id.state', '<>', 'draft'),
                    ('date', '<=', statement_date)
                    ]
        args2 = [('partner_id', '=', partner.id),
                    ('account_id.user_type_id.name', 'in', ['Receivable', 'Payable']),
                    ('move_id.state', '<>', 'draft')
                    ]

        movelines = moveline_obj.search(args)
        op_movelines =  moveline_obj.search(args2)
        total_paid = 0.0
        total_debit = 0.0
        total_credit = 0.0
        if op_movelines:
            for line in op_movelines:
                currency_id = line.currency_id
                total_debit = total_debit + line.debit
                total_credit = total_credit + line.credit
        op_balance = total_debit - total_credit
        return_lines = [{'debit':0.0,'credit':0.0, 'date':'','type':'Brought Foward','name':'Opening Balance','ref':'','date_maturity':'','account_id':False,'blocked':False,'doc_ref':'','cus_ref':'','com_ref':'','rec_ref':''}]
        for line in movelines:
            debit = 0
            credit = 0
            doc_ref = line.move_id.name
            if line.invoice_id:
                doc_ref = line.invoice_id.number

            line_type = '-'
            if line.journal_id.type == 'sale':
                line_type = 'Invoice'
            elif line.journal_id.type == 'bank':
                line_type = 'Payment'
                total_paid += line['debit'] +  line['credit']

            elif line.journal_id.type == 'sale_refund':
                line_type = 'Credit Note'
            else:
                line_type = line.journal_id.name
            debit = line.debit
            credit = line.credit

            new_line = {}
            new_line['debit'] = debit
            new_line['credit'] = credit
            new_line['date'] = line.date
            new_line['name'] = line.name
            new_line['ref'] = line.ref
            new_line['date_maturity'] = line.date_maturity
            new_line['account_id'] = line.account_id
            new_line['type'] = line_type
            new_line['doc_ref'] = doc_ref
            new_line['cus_ref'] = line.name
            new_line['com_ref'] = line.invoice_id.origin
            new_line['rec_ref'] = line.full_reconcile_id.name
            new_line['blocked'] = line.blocked
            return_lines.append(new_line)

        if (return_lines[0]['debit'] == return_lines[0]['credit']):
            return_lines[0]['debit'] = return_lines[0]['credit'] = 0.0
        elif (return_lines[0]['debit'] > return_lines[0]['credit']):
            return_lines[0]['debit']  = return_lines[0]['debit'] - return_lines[0]['credit']
            return_lines[0]['credit'] = 0.0
        else:
            return_lines[0]['credit']  = return_lines[0]['credit'] - return_lines[0]['debit']
            return_lines[0]['debit'] = 0.0
        balance = 0.0
        i = 0
        for line in return_lines:
            balance += line['debit'] - line['credit']
            line['balance'] = balance
            if i == 0:
                balance = balance + op_balance
                i = i + 1
        if (return_lines[0]['balance'] == 0.0):
            del return_lines[0]
        return return_lines, movelines, total_paid, op_balance


    def _lines_get(self, partner, statement_date,statement_start_date):
        moveline_obj = self.env['account.move.line']
        res = {x: [] for x in [partner.id]}
        args = [('partner_id', '=', partner.id),
                    ('account_id.user_type_id.name', 'in', ['Receivable', 'Payable']
                    ),
                    ('move_id.state', '<>', 'draft'),
                    ('date', '<=', statement_date),
                    ('date', '>=', statement_start_date)
                    ]
        args2 = [('partner_id', '=', partner.id),
                    ('account_id.user_type_id.name', 'in', ['Receivable', 'Payable']),
                    ('move_id.state', '<>', 'draft'),
                    ('date', '<', statement_start_date)
                    ]


        movelines = moveline_obj.search(args, order='date asc')
        op_movelines =  moveline_obj.search(args2, order='date asc')

        total_paid = 0.0
        total_debit = 0.0
        total_credit = 0.0
        for line in op_movelines:
            total_debit = total_debit + line.debit
            total_credit = total_credit + line.credit
        op_balance = total_debit - total_credit
        open_deb = 0.0
        open_cred = 0.0
        if op_balance < 0:
            open_cred = op_balance
        else:
            open_deb = op_balance
        return_lines = [{
            'debit':open_deb,
            'credit':open_cred,
            'date':'',
            'type':'Brought Foward',
            'name':'Opening Balance',
            'ref':'','date_maturity':'',
            'account_id':False,
            'blocked':False,
            'doc_ref':'',
            'cus_ref':'',
            'com_ref':'',
            'rec_ref':'',
            'balance': 0.0,
            'partner_id': partner.id,
            'currency_id':'',
            'move_id':''
       }]
        for line in movelines:
            if line.date <= statement_date and line.date >= statement_start_date:
                debit = 0
                credit = 0
                doc_ref = line.move_id.name
                if line.invoice_id:
                    doc_ref = line.invoice_id.number

                line_type = '-'
                if (line.journal_id.type == 'sale'):
                    line_type = 'Invoice'
                elif (line.journal_id.type == 'bank'):
                    line_type = 'Payment'
                    total_paid += line['debit'] +  line['credit']
                elif (line.journal_id.type == 'sale_refund'):
                    line_type = 'Credit Note'
                else:
                    line_type = line.journal_id.name

                debit = line.debit
                credit = line.credit
                new_line = {}
                new_line['debit'] = debit
                new_line['partner_id'] = line.partner_id.id
                new_line['credit'] = credit
                new_line['date'] = line.date
                new_line['name'] = line.name
                new_line['ref'] = line.ref
                new_line['date_maturity'] = line.date_maturity
                new_line['account_id'] = line.account_id.id
                new_line['type'] = line_type
                new_line['doc_ref'] = doc_ref
                new_line['cus_ref'] = line.name
                new_line['com_ref'] = line.invoice_id.origin
                new_line['rec_ref'] = line.full_reconcile_id.name
                new_line['blocked'] = line.blocked
                new_line['currency_id'] = line.currency_id
                new_line['move_id'] = line.move_id.name

                return_lines.append(new_line)
        if len(return_lines) > 0:
            if (return_lines[0]['debit'] == return_lines[0]['credit']):
                return_lines[0]['debit'] = return_lines[0]['credit'] = 0.0
            elif (return_lines[0]['debit'] > return_lines[0]['credit']):
                return_lines[0]['debit']  = return_lines[0]['debit'] - return_lines[0]['credit']
                return_lines[0]['credit'] = 0.0
            else:
                return_lines[0]['credit']  = return_lines[0]['credit'] - return_lines[0]['debit']
                return_lines[0]['debit'] = 0.0

        balance = 0.0
        i = 0
        for line in return_lines:
            balance += line['debit'] - line['credit']
            line['balance'] = balance
            if i == 0:
                balance = balance
                i = i + 1
        if len(return_lines) > 0:
            if (return_lines[0]['balance'] == 0.0):
                del return_lines[0]
        for row in return_lines:
            res[row.pop('partner_id')].append(row)
        return res, movelines, total_paid, op_balance

    @api.multi
    def get_report_values(self, docids, data=None):
        docids =[docids]
        partner_obj = self.env['res.partner']
        invoice_obj = self.env['account.invoice']
        active_id = self._context.get('active_id')
        lines_to_display = []
        statement_obj = self.env['customer.statement']
        statements = statement_obj.search([])
        end_date = fields.Date.today()
        start_date = fields.Date.today()
        if len(statements) > 1:
            statements = statements[len(statements) - 1]
        totals = {}
        if statements:
            start_date = statements.start_date
            end_date = statements.end_date
        lines_to_display = []
        age_analysis = {}
        company_currency = self.env.user.company_id.currency_id
        for partner_id in docids:
            partner = partner_obj.search([('id', '=', partner_id)])
            if not partner.wizard_print:
                end_date = fields.Date.today()
                invoices = invoice_obj.search([('partner_id', '=', partner.id), ('state', '=', 'open')], order='date asc')
                if invoices:
                    invoice = invoices[len(statements) - 1]
                    start_date = invoice.date_invoice
            lines, movelines, total_paid, op_balance = self._lines_get(partner, end_date, start_date)

            a = self._lines_get2(partner, end_date)
            lines2 = a[0]
            all_lines2 = a[1]
            total_paid2 = a[2]
            currency_id2 = a[3]
            age_analysis = []
            age_analysis.append(self._age_analysis_get(all_lines2, end_date))
            for line_tmp in lines[partner_id]:
                line = line_tmp.copy()
                if line['debit'] and line['currency_id']:
                    line['debit'] = line['amount_currency']
                if line['credit'] and line['currency_id']:
                    line['credit'] = line['amount_currency']
                    line['mat'] = line['amount_currency']
                lines_to_display.append(line)

        return [
            start_date,
            end_date,
            lines_to_display,
            fields.date.today(),
            age_analysis,
            total_paid,
            op_balance
        ]

    @api.multi
    def set_wizard_print_false(self, partner):
        if partner:
            partner.wizard_print = False

class customer_statement_email(models.TransientModel):
    _name = 'customer.statement'

    partner_id = fields.Many2one('res.partner', 'Partner')
    end_date = fields.Date('End Date', required=True, help='The End date of the statement.')
    start_date = fields.Date(string='Start Date',
                                       required=True,
                                       help='The Start date of the statement.',
				       default=time.strftime('%Y-%m-01'))

    @api.multi
    def action_print(self):
        partner_obj = self.env['res.partner']
        active_ids = self._context.get('active_ids')
        partners = partner_obj.search([('id', 'in', active_ids)])
        for partner in partners:
            partner.wizard_print = True
        return self.env.ref('customer_statement_email.action_report_overdue_custom').report_action(partner)

    @api.multi
    def action_send(self):
        partner_obj = self.env['res.partner']
        statement_obj = self.env['account.followup.report']
        if self._context.get('active_ids'):
            partners = partner_obj.search([('id', 'in', self._context.get('active_ids'))])
            for partner in partners:
                partner.wizard_print = True
                statement_obj.send_email({'partner_id': partner.id})
                partner.wizard_print = False
        return True


class CustomerFollowupt(models.AbstractModel):
    _inherit = "account.followup.report"

    @api.model
    def send_email(self, options):

        partner = self.env['res.partner'].browse(options.get('partner_id'))
        email = self.env['res.partner'].browse(partner.address_get(['invoice'])['invoice']).email
        template = self.env.ref('customer_statement_email.email_sustomer_statements')
        template_obj = self.env['mail.template']
        mail_mail_obj = self.env['mail.mail']
        attachment_obj = self.env['ir.attachment']
        if email and email.strip():
            values = template.generate_email(partner.id)
            atta_id = ''
            for attachment in values.get('attachments', []):
                attachment_data = {
                    'name': partner.name + ' Customer Statement',
                    'datas_fname': partner.name + " Customer Statement.pdf",
                    'datas': attachment[1],
                    'res_model': 'res.partner',
                    'res_id': partner.id
                }
                atta_id = (attachment_obj.create(attachment_data).id)
            body_html = self.with_context(print_mode=True, mail=True, keep_summary=True).get_html(options)
            html_body = b'<style>table {display:none}</style>'
            body_html = html_body + body_html
            msg = _('Follow-up email sent to %s') % email
            msg += '<br>' + body_html.decode('utf-8')
            msg_id = partner.message_post(body=msg, subtype='account_reports.followup_logged_action')
            msg_id.write({'attachment_ids': [(6, 0, [atta_id])]})
            email = self.env['mail.mail'].with_context(default_mail_message_id=msg_id).create({
                'subject': _('%s Customer Statement') % (self.env.user.company_id.name) + ' - ' + partner.name,
                'body_html': append_content_to_html(body_html, self.env.user.signature or '', plaintext=False),
                'email_from': self.env.user.email or '',
                'email_to': email,
                'body': msg,
            })
            return True
        raise UserError(_('Could not send mail to partner because it does not have any email address defined'))

    @api.model
    def print_followups(self, records):
        partner_obj = self.env['res.partner']
        partners = partner_obj.search([('id', 'in', records.get('ids'))])
        return self.env.ref('customer_statement_email.action_report_overdue_custom').report_action(partners)

    def _get_default_summary(self, options):
        """
        Override
        Return the overdue message of the company as the summary of the report
        """
        partner = self.env['res.partner'].browse(options.get('partner_id'))
        lang = partner.lang or self.env.user.lang or 'en_US'
        return self.env.user.company_id.overdue_msg
