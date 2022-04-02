from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError



class StockMove(models.Model):
    _inherit = "stock.move"

    def button_approve(self):
        self._action_done()

    def button_scrap(self):
        if self and not self.scrapped and self.quantity_done > 0:
            scrap = self.env['stock.scrap']
            vals = {}
            vals['product_id'] = self.product_id.id
            vals['scrap_qty'] = self.quantity_done
            vals['origin'] = self.origin
            vals['company_id'] = self.company_id.id
            vals['date_done'] = fields.Datetime.now()
            vals['product_uom_id'] = self.product_uom.id
            result = scrap.create(vals)
            res = result.sudo().action_validate()
            res.update({
                'state':'done'
            })
            self.scrapped = True
        else:
            raise ValidationError('Done quantity is 0, unable to move to scrap!')

    def button_return(self):
        if self and not self.scrapped and self.quantity_done > 0:
            picking = self.env['stock.return.picking']
            result = self._action_done()
            res = self.picking_id.move_ids_without_package.create_returns()
            print(res)
        else:
            raise ValidationError("Can't return scrapped items (or) Check if done quantity > 0")

class Picking(models.Model):
    _inherit = "stock.picking"

    # set domain for teacher to filter the selected teachers according to the class value
    @api.onchange('product_id')
    def set_domain_for_lot(self):
        move_lines = self.mapped('move_line_ids')
        lot_ids = move_lines.mapped('lot_id')
        res = {}
        ctx = self.env.context
        res['domain'] = {'lot_id': [('id', 'in', lot_ids.ids)]}
        return res

    def button_scrap(self):
        self.ensure_one()
        move_lines = self.mapped('move_line_ids')
        lot_ids = move_lines.mapped('lot_id')

        view = self.env.ref('stock.stock_scrap_form_view2')
        products = self.env['product.product']
        lots = self.env['stock.production.lot']
        for move in self.move_lines:
            if move.state not in ('draft', 'cancel') and move.product_id.type in ('product', 'consu'):
                products |= move.product_id

        for move in self.move_lines:
            if move.state not in ('draft', 'cancel') and move.product_id.type in ('product', 'consu'):
                products |= move.product_id
        return {
            'name': _('Scrap'),
            'view_mode': 'form',
            'res_model': 'stock.scrap',
            'view_id': view.id,
            'views': [(view.id, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('lot_id', 'in', lot_ids.ids)],
            'context': {'default_picking_id': self.id, 'product_ids': products.ids,'lot_id.ids':lot_ids.ids,'default_company_id': self.company_id.id},
            'target': 'new',
        }

class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'


    # lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial',related='picking_id.move_line_ids.lot_id', store=False, readonly=False)

    def create_returns(self):
        res = super(ReturnPicking, self).create_returns()
        return res

    @api.onchange('lot_id')
    def set_context(self):
        print("Hi")


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if self.move_id:
            result['lot_id'] = self.move_id.lot_ids.ids
        return result

    @api.model
    def default_set(self, fields):
        result = super().default_set(fields)
        if self.move_id:
            result['lot_id'] = self.move_id.lot_ids.ids
        return result

    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial', related='move_id.move_line_ids.lot_id',store=False, readonly=False)

    @api.depends('lot_id')
    def set_context(self):
        print("Hi")