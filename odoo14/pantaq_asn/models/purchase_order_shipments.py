from odoo import api, fields, exceptions, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class PurchaseOrderShipment(models.Model):
    _name = "purchase.order.shipment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Purchase Order Shipments"
    _order = 'id desc'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Transfered'),
        ('cancel', 'Cancelled')
    ], string='State', readonly=True, index=True, copy=False, default='draft', tracking=True)

    name = fields.Char('Shipment Reference', required=True, index=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True,
                                 related='purchase_id.company_id',)
    shipment_lines = fields.One2many('purchase.order.shipment.line', 'shipment_id', string='Shipment Lines', copy=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=True,
                                  domain=[('state', '=', 'purchase')])
    partner_id = fields.Many2one('res.partner', related='purchase_id.partner_id', string='Partner', readonly=True,
                                 store=True)

    date_order = fields.Datetime('Order Date', related='purchase_id.date_order', required=True, index=True,
                                 copy=False, )
    date_approve = fields.Datetime('Order Confirmation Date', related='purchase_id.date_approve', readonly=1,
                                   index=True, copy=False)
    scheduled_arrival = fields.Datetime(string='')
    shipment_date = fields.Datetime(string='')
    container_no = fields.Char(string='Container #', copy=False, )
    forwarder_no = fields.Char(string='Forwarder #', copy=False, )

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        if self.shipment_lines:
            raise UserError(
                _(
                    "Shipment Already Contains Lines Values. Please remove lines and select Purchase Order again "
                )
            )
        if self.purchase_id:
            shipment_lines = self.purchase_id._create_shipment_lines_context(self.purchase_id.shipments_lines)
            self.shipment_lines = shipment_lines

    def button_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})

    def button_confirm(self):
        self.ensure_one()
        for line in self.shipment_lines:
            if line.shipment_qty_received < 1:
                raise UserError(
                    _(
                        "You cannot confirm shipment if Shipped qty is 0"
                    )
                )
        self.write({'state': 'confirm'})

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'purchase.order.shipment') or '/'

        return super(PurchaseOrderShipment, self).create(vals)

    def unlink(self):
        for lines in self:
            if lines.state not in ['draft', 'cancel']:
                raise UserError(
                    _(
                        "You cannot delete a Shipment once confirmed"
                    )
                )
        return super(PurchaseOrderShipment, self).unlink()


class PurchaseOrderShipmentLine(models.Model):
    _name = 'purchase.order.shipment.line'

    shipment_id = fields.Many2one('purchase.order.shipment', string='Order Reference', index=True, required=True,
                                  ondelete='cascade')

    product_id = fields.Many2one('product.product', string='Product', change_default=True)
    product_uom = fields.Many2one('uom.uom', related='product_id.uom_id', string='Unit of Measure', )

    product_qty = fields.Float(string='Requested Qty', digits='Product Unit of Measure', required=True)
    qty_received = fields.Float(string='Received Qty')
    remaining_qty = fields.Float(string='Remaining Shipped Qty')
    
    
    shipment_qty_received = fields.Float(string='Shipped Qty')

    @api.depends('shipment_id.purchase_id.picking_ids.move_line_ids_without_package.qty_done')
    def update_qty_received(self):
        print("I am here")

    @api.onchange('shipment_qty_received')
    @api.constrains("remaining_qty", "shipment_qty_received")
    def constrains_shipment_qty_received(self):
        for record in self:
            if record.shipment_qty_received < record.remaining_qty:
                raise exceptions.ValidationError(_("Remaining Qty Cannot be greater than Shipment Qty .\n Product [%s]")
                 % (record.product_id.name))
