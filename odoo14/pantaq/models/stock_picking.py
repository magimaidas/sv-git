from odoo import api, exceptions, fields, models, _


class StockPicking(models.Model):
    _inherit = ["stock.picking"]

    move_type = fields.Selection([
        ('third_party', 'Seller to Customer'),
        ('direct', 'Partial'),
        ('one', 'All at once')], string='Delivery Type', default='third_party',
        required=True)

    def button_validate(self):
        if self.move_type == 'third_party':
            self.state = 'done'
            return super(StockPicking, self).button_validate()
        else:
            return super(StockPicking, self).button_validate()
