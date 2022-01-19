# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _

class AccountInvoice(models.Model):
    _inherit = ["account.move"]

    # Overridde user_id field if needed
    '''user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user, copy=False)'''

    # New:
    lead_id    = fields.Many2one('crm.lead', string='Enquiry', ondelete='restrict')
    intorder_id = fields.Many2one('internal.order', string='Internal Order', ondelete='restrict')
    remarks = fields.Text(string="Remarks")
    id_xero = fields.Char('ID Reference of Xero', copy=False)


class InvoiceLine(models.Model):
    _inherit = 'account.move.line'

    id_xero = fields.Char('ID Reference of Xero', copy=False)