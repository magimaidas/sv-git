from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # @api.depends('rfq_status','state')
    @api.onchange('rfq_status','state')
    def onchange_rfq_status(self):

        print("Check order status")

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rfq_ref = fields.Many2one('purchase.order', string="RFQ Reference", readonly=True)
    po_ref = fields.Many2one('purchase.order', string="PO Reference", readonly=True)
    is_shipment = fields.Boolean(
        string='Shipment', default=True, store=True, copy=False)

    shipments_lines = fields.One2many(
        'purchase.order.shipment', 'purchase_id', string='', copy=False)
    shipments_count = fields.Integer(compute="_compute_shipments", string='Shipment Count', copy=False, default=0,
                                     store=True)

    @api.depends('order_line.rfq_status', 'order_line.state','order_line')
    def onchange_rfq_status(self):
        print("Check order status")

    @api.onchange('is_shipment')
    def _onchange_is_shipment(self):
        if len(self.shipments_lines) > 0 and self.is_shipment == False:
            raise UserError(
                msg=_("This Purchase Already Order Contains Shipments Records"),
                title=_("Shipments Co Exists")
            )

    def _create_shipment_lines_context(self, shipping_ids):

        lines = []
        for line in self.order_line:
            shipment_line_qty = shipping_ids.filtered(lambda l: l.state in ['confirm']).mapped(
                'shipment_lines').filtered(lambda r: r.product_id.id == line.product_id.id).mapped('shipment_qty_received')
            residual_qty = line.product_qty - \
                line.qty_received - sum(shipment_line_qty)
            if residual_qty > 0 and line.product_qty > 0:
                lines.append((
                    0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'qty_received': line.qty_received,
                        'remaining_qty': residual_qty
                    }
                ))
            else:
                continue
        return lines

    def action_open_shipments(self):

        shipping_ids = self.mapped('shipments_lines')
        domain = "[('id','in',%s)]" % (shipping_ids.ids)
        context = {
            'default_purchase_id': self.id,
        }
        result = {
            'name': _("Advance Shipping Note"),
            'view_id': False,
            'res_model': 'purchase.order.shipment',
            'type': 'ir.actions.act_window',
        }
        if len(shipping_ids) == 1:
            result.update({'view_mode':'form','view_type': 'form','res_id': shipping_ids.id})
        if len(shipping_ids) > 1:
            result.update({'view_mode':'tree,form','view_type': 'form','domain': domain,'context': context,'res_ids':shipping_ids.ids})
        if not shipping_ids:
            result.update({'view_mode': 'form', 'view_type': 'form','domain': domain, 'context': context})
        return result

    @api.depends('shipments_lines')
    def _compute_shipments(self):
        for order in self:
            shipments = order.mapped('shipments_lines')
            order.shipments_count = len(shipments)
