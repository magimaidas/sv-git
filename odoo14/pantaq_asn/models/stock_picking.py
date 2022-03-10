from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, UserError, ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    # state = fields.Selection([
    #     ('draft', 'New'), ('cancel', 'Cancelled'),
    #     ('waiting', 'Waiting Another Move'),
    #     ('confirmed', 'Waiting Availability'),
    #     ('partially_available', 'Partially Available'),
    #     ('assigned', 'Available'),
    #     ('done', 'Done')], string='Status',
    #     copy=False, default='draft', index=True, readonly=True,
    #     help="* New: When the stock move is created and not yet confirmed.\n"
    #          "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
    #          "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to be manufactured...\n"
    #          "* Available: When products are reserved, it is set to \'Available\'.\n"
    #          "* Done: When the shipment is processed, the state is \'Done\'.")

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
            result.sudo().action_validate()
            result.update({
                'state':'done'
            })
            self.scrapped = True
        else:
            raise ValidationError('Done quantity is 0, unable to move to scrap!')

    def button_return(self):

        # result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        # # override the context to get rid of the default filtering on operation type
        # result['context'] = {'default_partner_id': self.partner_id.id, 'default_origin': self.name,
        #                      'default_picking_type_id': self.picking_type_id.id}
        # pick_ids = self.mapped('picking_ids')
        # # choose the view_mode accordingly
        # if not pick_ids or len(pick_ids) > 1:
        #     result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        # elif len(pick_ids) == 1:
        #     res = self.env.ref('stock.view_picking_form', False)
        #     form_view = [(res and res.id or False, 'form')]
        #     if 'views' in result:
        #         result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
        #     else:
        #         result['views'] = form_view
        #     result['res_id'] = pick_ids.id
        # print(result)
        if self and not self.scrapped and self.quantity_done > 0:
            picking = self.env['stock.return.picking']
            result = self._action_done()
            res = self.picking_id.create_returns()
            print(res)
        else:
            raise ValidationError("Can't return scrapped items (or) Check if done quantity > 0")
