from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_shipment = fields.Boolean(
        string='Shipment', default=True, store=True, copy=False)

    shipments_lines = fields.One2many(
        'purchase.order.shipment', 'purchase_id', string='', copy=False)
    shipments_count = fields.Integer(compute="_compute_shipments", string='Shipment Count', copy=False, default=0,
                                     store=True)

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
        return {
            'name': _("Advance Shipping Note"),
            'view_mode': 'tree,form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'purchase.order.shipment',
            'type': 'ir.actions.act_window',
            'domain': domain,
            'context': context
        }

    @api.depends('shipments_lines')
    def _compute_shipments(self):
        for order in self:
            shipments = order.mapped('shipments_lines')
            order.shipments_count = len(shipments)
