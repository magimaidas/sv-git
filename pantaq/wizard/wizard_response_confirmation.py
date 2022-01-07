# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time


class wizardRfqProduct(models.TransientModel):
    _name = "pq.wizard.rfq.product"
    _description = 'Wizard Product Create Confirmation'

    @api.model
    def _default_get_po_id(self):
        data = self.env['purchase.order'].search([('id','=',self._context.get('active_id'))])
        return data

    purchase_id = fields.Many2one('purchase.order',default=_default_get_po_id)

    @api.multi
    def rfq_response_received(self):
        purchase_id = self.env['purchase.order'].search([('id','=',self.purchase_id.id)])
        if purchase_id:
            for line in purchase_id:
                line.update({
                    'state': 'qtn_received'
                    })



