from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    attachment = fields.Image('Attachment', help='Picture of product during return', store=True,copy=False, attachment=True, max_width=1024, max_height=1024)


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        res = super(ReturnPicking, self).create_returns()
        pick = self.env[res['res_model']].browse(res['res_id'])
        return res


class StockPickingInherit(models.Model):
    _inherit = "stock.picking"

    def write(self, vals):
        res = super(StockPickingInherit, self).write(vals)
        for rec in self:
            if rec.state == 'done' and rec.fetch_done_qty:
                for line_id in rec.approved_shipments_ids.shipment_lines:
                    for move in rec.move_ids_without_package:
                        if move.product_id == line_id.product_id:
                            line_id.sudo().write({'qty_received':move.quantity_done, 'remaining_qty':line_id.shipment_qty_received-move.quantity_done})
                rec.approved_shipments_ids.sudo().write({'state': 'done'})
        return res

    show_shipments = fields.Boolean(string='', compute='compute_shipments_bool_domain', copy=False, required=True)
    attachment = fields.Image('Attachment', help='Picture of product during return', copy=False, attachment=True, max_width=1024, max_height=1024)

    def compute_shipments_bool_domain(self):
        for rec in self:
            valid_po_obj = self.env['purchase.order'].sudo().search(
                [('name', '=', self.origin), ('is_shipment', '=', True), ])
            rec.show_shipments = True if valid_po_obj else False

    
    fetch_done_qty = fields.Boolean(string='Fetch Qty from Shipments', default=True, copy=False)
    shipments_ids = fields.Many2one('purchase.order.shipment', string='Shipments', copy=False)
    approved_shipments_ids = fields.Many2many('purchase.order.shipment', compute='compute_approved_shipments')
    show_details = fields.Boolean(related='picking_type_id.show_operations')
    show_reserved = fields.Boolean(related='picking_type_id.show_reserved')


    @api.depends("show_shipments")
    def compute_approved_shipments(self):        
        for rec in self:
            domain_ids = []
            if rec.show_shipments:
                domain_ids = self.env['purchase.order'].search(
                    [('name', '=', rec.origin), ('is_shipment', '=', True), ]).shipments_lines.filtered(
                    lambda r: r.state == 'confirm').ids
            rec.approved_shipments_ids = [(6, 0, domain_ids)]

    # def button_validate(self):
    #     res = super(StockPickingInherit, self).button_validate()
    #     if 'INT' in self.name:
    #         self.ensure_one()
    #         shipments_ids = self.approved_shipments_ids.sudo().filtered(lambda r: r.state == 'confirm')
    #         if not shipments_ids:
    #             raise UserError(_("Shipments field is empty. Please add Shipments and then try again."))
    #
    #         if self.move_line_ids_without_package:
    #             self.update_done_qty(self.move_line_ids_without_package, shipments_ids)
    #             return
    #         else:
    #             raise UserError(_("Please Use Detailed Operation in Operation Type"))
    #
    #         if self.state == 'done':
    #             raise UserError(_("Quantity Done can not be fetched in this state"))
    #
    #         if not (self.move_line_ids_without_package):  # or self.move_ids_without_package
    #             raise UserError(_("No Operation for Stock Move Exists"))
    #
    #         if not self.picking_type_id.show_operations:
    #             raise UserError(_("Please Use Detailed Operation in Operation Type"))
    #     else:
    #         return res

    @api.depends('move_ids_without_package')
    def fetch_qty_done(self):
        self.ensure_one()
        shipments_ids = self.shipments_ids.sudo().filtered(lambda r: r.state == 'confirm')
        if not shipments_ids:
            raise UserError(_("Shipments field is empty. Please add Shipments and then try again."))
        
        if self.state == 'done':
            raise UserError(_("Quantity Done can not be fetched in this state"))          
        
        if not (self.move_line_ids_without_package):#or self.move_ids_without_package
            raise UserError(_("No Operation for Stock Move Exists"))

        if not self.picking_type_id.show_operations:
            raise UserError(_("Please Use Detailed Operation in Operation Type"))
          
        if self.move_line_ids_without_package:
            self.update_done_qty(self.move_line_ids_without_package, shipments_ids)
            return
        else:
            raise UserError(_("Please Use Detailed Operation in Operation Type"))


    
    def update_done_qty(self,move_lines,shipment):
        self.ensure_one()
        move_lines.write({'qty_done':0})
        mv_lines_stack = []

        

        def update_move_lines(move_line,shipment_line):
            processed_mv_lines = []
            if move_line.product_id.tracking == 'serial':
                for i in range(int(shipment_line.shipment_qty_received)):#for i in range(int(shipment_line.shipment_qty_received))
                    move_line[i].qty_done = 1
                    processed_mv_lines.append(move_line[i].id)
            else:
                move_line[0].qty_done = shipment_line[0].shipment_qty_received
                processed_mv_lines.append(move_line[0].id)

            return processed_mv_lines
        
        for shipment_lines in shipment.mapped('shipment_lines'):
            mv_lines = move_lines.filtered(lambda r: (r.product_id.id == shipment_lines.product_id.id and r.id not in mv_lines_stack))
            mv_lines_stack += update_move_lines(mv_lines,shipment_lines)
           

      
        
