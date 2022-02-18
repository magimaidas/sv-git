# -*- coding: utf-8 -*-

from odoo import models, fields, api

class pantaq_wrf(models.Model):
    _name = 'purchase.asn.line'
    _description = 'ASN Product details'

    @api.model
    def _default_get_po_id(self):
        data = self.env['purchase.asn'].search([('id', '=', self._context.get('active_id'))])
        return data

    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    desc = fields.Char(string='Description')
    quantity = fields.Integer(string='Quantity')
    purchase_id = fields.Many2one('purchase.asn',default=_default_get_po_id,index=True, required=True, ondelete='cascade')
    lot = fields.Many2one('stock_production_lot', string='LOT/Serial', ondelete='restrict', readonly=True)

    def action_asn_show_details(self):
        """ Returns an action that will open a form view (in a popup) allowing to work on all the
        move lines of a particular move. This form view is used when "show operations" is not
        checked on the picking type.
        """
        self.ensure_one()

        # picking_type_id = self.picking_type_id or self.picking_id.picking_type_id

        # If "show suggestions" is not checked on the picking type, we have to filter out the
        # reserved move lines. We do this by displaying `move_line_nosuggest_ids`. We use
        # different views to display one field or another so that the webclient doesn't have to
        # fetch both.
        # if picking_type_id.show_reserved:
        #     view = self.env.ref('stock.view_stock_move_operations')
        # else:
        view = self.env.ref('stock.view_stock_move_nosuggest_operations')
        sm_obj = self.env['stock.move']
        return {
            'name': ('Detailed Operations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(
                self.env.context,
                show_owner=sm_obj.picking_type_id.code != 'incoming',
                show_lots_m2o=sm_obj.has_tracking != 'none' and (sm_obj.picking_type_id.use_existing_lots or sm_obj.state == 'done' or sm_obj.origin_returned_move_id.id),  # able to create lots, whatever the value of ` use_create_lots`.
                show_lots_text=sm_obj.has_tracking != 'none' and sm_obj.picking_type_id.use_create_lots and not sm_obj.picking_type_id.use_existing_lots and sm_obj.state != 'done' and not sm_obj.origin_returned_move_id.id,
                show_source_location=sm_obj.picking_type_id.code != 'incoming',
                show_destination_location=sm_obj.picking_type_id.code != 'outgoing',
                show_package=not sm_obj.location_id.usage == 'supplier',
                show_reserved_quantity=sm_obj.state != 'done' and not sm_obj.picking_id.immediate_transfer and sm_obj.picking_type_id.code != 'incoming'
            ),
        }
class pantaq_wrf(models.Model):
    _name = 'purchase.asn'
    _description = 'Advance shipping note'

    name = fields.Char(string='ASN Number')
    location = fields.Many2one('stock.location', string='Location', ondelete='restrict')
    asn_date = fields.Date(string='ASN Date', required=True, index=True, copy=False,
                           default=fields.Datetime.now().date())
    carrier = fields.Many2one('delivery.carrier',string='Carrier')
    arrival_date = fields.Date(string='Arrival Date', required=True, index=True, copy=False,
                               default=fields.Datetime.now().date())


    reference = fields.Many2one('purchase.order', string='Reference', ondelete='restrict', readonly=True, invisible=True)
    order_line = fields.One2many('purchase.asn.line', 'purchase_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    state = fields.Selection([('draft', 'New'), ('done', 'Done')],string='state', default='draft', help='Set this to action automatically')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['state'] = 'done'
            print(vals['order_line'])
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.asn') or 'New'
            order_line = self.env['purchase.asn.line']
            lines = []
            for line in self.reference.order_line:
                product = line.product_id
                desc = line.name
                qty = line.product_qty - line.asn_qty
                purchase_id = order_line._default_get_po_id()
                vals = {}
                vals['product_id'] = product
                vals['desc'] = desc
                vals['quantity'] = qty
                vals['purchase_id'] = purchase_id
                lines.append((0, 0, vals))
            order_line.create(lines)

            ref = self.env['purchase.order'].search([('id', '=', self._context.get('active_id'))])
            pol = self.env['purchase.order.line'].search([('order_id','=',self._context.get('active_id'))])
            for ol in lines:
                for line in pol:
                    if line.product_id == ol.product_id:
                        line.update({
                            'asn_qty': line.asn_qty + ol.quantity,
                        })
            ref.asn_count += 1
            return super(pantaq_wrf, self).create(vals)
        else:
            return


    @api.onchange('reference')
    def _value_orderline(self):
        order_line = self.env['purchase.asn.line']
        lines = [(5,0,0)]
        for line in self.reference.order_line:
            product = line.product_id
            desc = line.name
            qty = line.product_qty - line.asn_qty
            purchase_id = order_line._default_get_po_id()
            vals= {}
            vals['product_id'] = product
            vals['desc'] = desc
            vals['quantity'] = qty
            vals['purchase_id'] = purchase_id
            lines.append((0,0,vals))
        self.order_line = lines

    # @api.model
    # def default_get(self, fields):
    #     res = super(pantaq_wrf, self).default_get(fields)
    #     res.update({
    #         'reference':
    #     })
