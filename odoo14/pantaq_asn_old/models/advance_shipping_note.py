# -*- coding: utf-8 -*-

from odoo import models, fields, api


class pantaq_asn(models.Model):
    _name = 'purchase.asn.line'
    _description = 'ASN Product details'

    @api.model
    def _default_get_po_id(self):
        data = self.env['purchase.asn'].search([('id', '=', self._context.get('active_id'))])
        return data

    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    desc = fields.Char(string='Description')
    quantity = fields.Integer(string='Quantity')
    purchase_id = fields.Many2one('purchase.asn', default=_default_get_po_id, index=True, required=True,
                                  ondelete='cascade')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('scrap', 'Scrap'), ('return', 'Return')],
                             string='Status',
                             required=True, readonly=True, default='draft')
    returned_qty = fields.Integer(string='Returned', default=0,readonly=True,compute='_compute_qty',copy=False,
                                   store=True)
    scrapped_qty = fields.Integer(string='Scrapped', default=0,readonly=True,compute='_compute_qty',copy=False,
                                   store=True)
    done_qty = fields.Integer(string='Done', default=0,readonly=True,compute='_compute_qty',copy=False,
                                   store=True)

    def _compute_qty(self):
        for self in self:
            picks = self.purchase_id.reference.mapped('picking_ids')
            if picks:
                for pick in picks:
                    if pick.is_return_picking:
                        for product_id in pick.product_id:
                            if self.product_id.id == product_id.id:
                                self.returned_qty = pick.move_line_ids.qty_done
                    if pick.has_scrap_move:
                        for product_id in pick.product_id:
                            if self.product_id.id == product_id.id:
                                for line in pick.move_line_ids:
                                    self.scrapped_qty = line.qty_done
            print("Hi ",self)
            self.returned_qty = 0
            self.scrapped_qty = 0
            self.done_qty = 0

    def button_approve(self):
        if self:
            self.state = 'done'

    def button_scrap(self):
        if self:
            self.state = 'scrap'
            scrap = self.env['stock.scrap']
            vals = {}
            vals['product_id'] = self.product_id.id
            vals['scrap_qty'] = self.quantity
            vals['origin'] = self.purchase_id.name
            vals['company_id'] = self.env.user.company_id.id
            vals['date_done'] = fields.Datetime.now()
            vals['product_uom_id'] = self.product_id.uom_id.id
            scrap.create(vals)

    def button_return(self):
        if self:
            self.state = 'return'

    def action_asn_show_details(self):

        self.ensure_one()
        view = self.env.ref('stock.view_stock_move_operations')
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
                show_lots_m2o=sm_obj.has_tracking != 'none' and (
                        sm_obj.picking_type_id.use_existing_lots or sm_obj.state == 'done' or sm_obj.origin_returned_move_id.id),
                # able to create lots, whatever the value of ` use_create_lots`.
                show_lots_text=sm_obj.has_tracking != 'none' and sm_obj.picking_type_id.use_create_lots and not sm_obj.picking_type_id.use_existing_lots and sm_obj.state != 'done' and not sm_obj.origin_returned_move_id.id,
                show_source_location=sm_obj.picking_type_id.code != 'incoming',
                show_destination_location=sm_obj.picking_type_id.code != 'outgoing',
                show_package=not sm_obj.location_id.usage == 'supplier',
                show_reserved_quantity=sm_obj.state != 'done' and not sm_obj.picking_id.immediate_transfer and sm_obj.picking_type_id.code != 'incoming'
            ),
        }


class pantaq_asn(models.Model):
    _name = 'purchase.asn'
    _description = 'Advance shipping note'

    name = fields.Char(string='ASN Number')
    location = fields.Many2one('stock.location', string='Location', ondelete='restrict')
    asn_date = fields.Date(string='ASN Date', required=True, index=True, copy=False,
                           default=fields.Datetime.now().date())
    carrier = fields.Many2one('delivery.carrier', string='Carrier')
    arrival_date = fields.Date(string='Arrival Date', required=True, index=True, copy=False,
                               default=fields.Datetime.now().date())

    reference = fields.Many2one('purchase.order', string='Reference', ondelete='restrict', readonly=True,
                                invisible=True)
    order_line = fields.One2many('purchase.asn.line', 'purchase_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    state = fields.Selection([('draft', 'New'), ('inspection', 'Under Inspection'), ('done', 'Done')], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    picking_count = fields.Integer(compute='_compute_picking', string='Picking count', default=0, store=True)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False,
                                   store=True)

    def action_view_picking(self):
        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_partner_id': self.reference.partner_id.id, 'default_origin': self.reference.name, 'default_picking_type_id': self.reference.picking_type_id.id}
        pick_ids = self.mapped('picking_ids')
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,view) for state,view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result


    @api.depends('picking_ids')
    def _compute_picking(self):
        for order in self.reference:
            pickings = order.order_line.mapped('move_ids.picking_id')
            order.picking_ids = pickings
            order.picking_count = len(pickings)

    def inspect_asn(self):
        pick_ids = self.reference.mapped('picking_ids')
        active_picks = pick_ids.filtered(lambda p: p.state not in ('cancel')).filtered(lambda p: p.picking_type_code not in ('outgoing'))
        if not active_picks:
            picking = self.env['stock.picking']
            result = picking.create({
                'origin': self.reference.name,
                'picking_type_id': self.reference.picking_type_id.id,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': self.reference.picking_type_id.warehouse_id.id,
                'partner_id': self.reference.partner_id.id,
                'company_id': self.env.user.company_id.id,
                'move_type': 'direct',
                'state': 'assigned'
            })
            # self.sudo().update({
            #     'picking_ids' : (0,0,result.id)
            # })
            self.reference.sudo().update({
                'picking_ids': [(4,result.id)],
                'picking_count': self.reference.picking_count + 1,
            })
            self.reference._compute_picking()

            for item in self.reference.order_line:
                product_ref = self.env['product.product'].search([('id', '=', item.product_id.id)])
                move = self.env['stock.move'].create({
                    'name': product_ref.name,
                    'product_id': product_ref.id,
                    'product_uom_qty': item.product_qty,
                    'product_uom': product_ref.uom_id.id,
                    'picking_id': result.id,
                    'location_id': self.env.ref('stock.stock_location_suppliers').id,
                    'location_dest_id': self.reference.picking_type_id.warehouse_id.id,
                    'procure_method': 'make_to_order',
                    'origin': self.reference.name,
                    'state': 'draft',
                })

                sml = self.env['stock.move.line'].create({
                    'move_id': move.id,
                    # 'lot_id': self.lot_id.id,
                    # 'qty_done': item.product_qty,
                    'product_id': product_ref.id,
                    'product_uom_id': product_ref.uom_id.id,
                    'location_id': self.env.ref('stock.stock_location_suppliers').id,
                    'location_dest_id': self.reference.picking_type_id.warehouse_id.id,
                })

            self.reference._compute_picking()

        if self:
            result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
           # override the context to get rid of the default filtering on operation type
            result['context'] = {'default_partner_id': self.reference.partner_id.id,
                                 'default_origin': self.reference.name,
                                 'default_picking_type_id': self.reference.picking_type_id.id}
            pick_ids = self.reference.mapped('picking_ids')
                # choose the view_mode accordingly
            if not pick_ids or len(pick_ids) > 1:
                result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
            elif len(pick_ids) == 1:
                res = self.env.ref('stock.view_picking_form', False)
                form_view = [(res and res.id or False, 'form')]
                if 'views' in result:
                    result['views'] = form_view + [(state, view) for state, view in result['views'] if
                                                   view != 'form']
                else:
                    result['views'] = form_view
                result['res_id'] = pick_ids.id
                result['target'] = 'current'
            return

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['state'] = 'inspection'
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
            if self:
                ref_val = ref.update({
                    'asn_ids': (0, 0, self.id)
                })
            pol = self.env['purchase.order.line'].search([('order_id', '=', self._context.get('active_id'))])
            for ol in vals['order_line']:
                for line in pol:
                    if line.product_id.id == ol[2]['product_id']:
                        line.update({
                            'asn_qty': line.asn_qty + ol[2]['quantity'],
                        })
            ref.asn_count += 1
            move_lines = []
            for item in vals['order_line']:
                line_item = {}
                product_ref = self.env['product.product'].search([('id', '=', item[2]['product_id'])])
                line_item['name'] = product_ref.name,
                line_item['product_id'] = product_ref.id,
                line_item['product_uom_qty'] = item[2]['quantity'],
                line_item['product_uom'] = product_ref.uom_id.id,
                line_item['location_id'] = self.env.ref('stock.stock_location_suppliers').id,
                line_item['location_dest_id'] = ref.picking_type_id.warehouse_id.id,
                line_item['picking_type_id'] = ref.picking_type_id.id
                move_lines.append((0, 0, line_item))
            return super(pantaq_asn, self).create(vals)
        else:
            return


    @api.onchange('reference')
    def _value_orderline(self):
        order_line = self.env['purchase.asn.line']
        lines = [(5, 0, 0)]
        for line in self.reference.order_line:
            product = line.product_id
            desc = line.name
            qty = line.product_qty - line.asn_qty
            purchase_id = order_line._default_get_po_id()
            vals = {}
            vals['product_id'] = product
            vals['desc'] = desc
            vals['quantity'] = qty
            vals['purchase_id'] = self.reference.id
            lines.append((0, 0, vals))
        self.order_line = lines


class pantaq_asn_inspection(models.Model):
    _name = 'purchase.asn.inspection'
    _description = 'ASN Inspection'
