from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    image_attach = fields.Image('Attachment', help='Picture of product during scrap', copy=False, attachment=True, max_width=1024, max_height=1024)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(StockScrap, self)._onchange_product_id()
        if self.tracking == 'lot':
            move_lines = self.picking_id.mapped('move_line_ids')
            lot_ids = move_lines.mapped('lot_id')
            # Das modified here
            lot_ids = lot_ids.filtered(lambda m: m.product_qty != 0)
            domain = {'lot_id': [('id', 'in', lot_ids.ids)]}
            return {'domain': domain}

    @api.onchange('scrap_qty')
    def _onchange_scrap_qty(self):
        if self.scrap_qty > 1:
            raise UserError(
                _("Scrap Quantity can not be more than 1. To move more than 1 Quantity, do again!")
            )

