from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    asn_ids = fields.One2many('purchase.asn', 'reference', string='ASN ids',
                              states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    asn_count = fields.Integer(compute='_compute_asn', string='ASN count', default=0, store=True)
    asn_done = fields.Boolean(string='ASN Done?', default=False, compute='_compute_asn_done',store=True)

    @api.depends('asn_count')
    def _compute_asn_done(self):
        flag = True
        for line in self.order_line:
            if line.product_qty != line.asn_qty:
                flag = False
        if flag:
            self.asn_done = True

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
        if len(asn_obj)==1:
            res = self.env.ref('pantaq_asn.pq_view_purchase_asn_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view
            result['view_id'] = res.id
            result['res_id'] = asn_obj.id
        else:
            result['domain'] = "[('id','in',%s)]" % (asn_obj.ids)
        return result

    # def button_confirm(self):
    #     for order in self:
    #         order.update({
    #             'state': 'purchase'
    #         })

    def button_approve(self, force=False):
        self = self.filtered(lambda order: order._approval_allowed())
        self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    def action_view_picking(self):
        if self.asn_count == 0:
            raise ValidationError("No ASN found to receive product. First create ASN then proceed!")
        else:
            return super(PurchaseOrder, self).action_view_picking()

    def inspect_asn(self):
        print("Inspecting")

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    asn_qty = fields.Integer(string="ASN Qty", default=0, invisible=True)

    # def _prepare_stock_moves(self, picking):
    #     res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
    #     if self.order_id.asn_ids:
    #         res.update(('product_id', self.order_id.asn_ids) for k, v in d.items() if v == "value2")
    #
    #     print(res)
