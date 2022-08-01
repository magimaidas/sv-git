from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    asn_ids = fields.One2many('purchase.asn', 'reference', string='ASN ids',
                              states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    asn_count = fields.Integer(compute='_compute_asn', string='ASN count', default=0, store=True)
    asn_done = fields.Boolean(string='ASN Done?', default=False, compute='_compute_asn_done', store=True)
    rfq_ref = fields.Many2one('purchase.order', string="RFQ Reference")
    po_ref = fields.Many2one('purchase.order', string="PO Reference")

    @api.depends('asn_count')
    def _compute_asn_done(self):
        flag = True
        for line in self.order_line:
            if line.product_qty != line.asn_qty:
                flag = False
        if flag:
            self.asn_done = True

    def button_confirm(self):
        for order in self:
            if self.po_type == 'rfq':
                if order.state not in ['draft', 'sent', 'qtn_received', 'rfq_revised']:
                    continue
                if order.po_type == 'rfq':
                    new_order = order.copy()
                    lines = new_order.order_line.filtered(lambda l: l.rfq_status == 'approved')
                    lines_remove = OrderedSet()
                    for line in order.order_line:
                        if line.rfq_status == 'rejected':
                            lines_remove.add(line.id)
                    res = self.env['purchase.order.line'].browse(lines_remove).sudo().unlink()
                    new_order.update({
                        'state': 'done',
                        'po_ref': order.id,
                    })
                    order.rfq_ref = new_order.id
                    order.po_type = 'purchase'
                    order.name = self.env['ir.sequence'].next_by_code('purchase.order') or '/'
    
                order._add_supplier_to_product()
                # Deal with double validation process
                if order._approval_allowed():
                    order.button_approve()
                else:
                    order.write({'state': 'to approve'})
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])
            else:
                super(PurchaseOrder, self).button_confirm()
        return True

    def create_asn(self):
        return {
            'name': _('Create ASN'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('pantaq_asn.pq_view_purchase_asn_form').id,
            'res_model': 'purchase.asn',
            'context': {'default_reference': self.id},
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def _compute_asn(self):
        for order in self:
            asn_obj = self.env['purchase.asn'].search([('reference', '=', order.id)])
            order.asn_count = len(asn_obj)

    def action_view_asn(self):
        """ This function returns an action that display existing ASNs of given purchase order.
        """

        result = self.env["ir.actions.actions"]._for_xml_id('pantaq_asn.action_asn_tree')
        asn_obj = self.env['purchase.asn'].search([('reference', '=', self.name)])
        if len(asn_obj) == 1:
            res = self.env.ref('pantaq_asn.pq_view_purchase_asn_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view
            result['view_id'] = res.id
            result['res_id'] = asn_obj.id
        else:
            result['domain'] = "[('id','in',%s)]" % (asn_obj.ids)
        return result

    def button_approve(self, force=False):
        self = self.filtered(lambda order: order._approval_allowed())
        self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    # def action_view_picking(self):
    #     if self.asn_count == 0:
    #         raise ValidationError("No ASN found to receive product. First create ASN then proceed!")
    #     else:
    #         return super(PurchaseOrder, self).action_view_picking()

    def inspect_asn(self):

        print("Inspecting ASN")
        pick_ids = self.mapped('picking_id')
        if not pick_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
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
            self.picking_id = result.id
            self.reference.sudo().update({
                'picking_ids': result,
                'picking_count': self.reference.picking_count + 1,
            })

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
                # move_res = move._action_confirm()
                # move_assign =  move_res._action_assign()
                # conf = result.sudo().action_confirm()
                # assign = conf.sudo()._action_assign()
            # self.reference.sudo().update({
            #     'picking_ids': ((0, 0, result.id)),
            # })
        if self:
            result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
            # override the context to get rid of the default filtering on operation type
            result['context'] = {'default_partner_id': self.reference.partner_id.id,
                                 'default_origin': self.reference.name,
                                 'default_picking_type_id': self.reference.picking_type_id.id}
            pick_ids = self.mapped('picking_id')
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
            return result
        # else:


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    asn_qty = fields.Integer(string="ASN Qty", default=0, invisible=True)

