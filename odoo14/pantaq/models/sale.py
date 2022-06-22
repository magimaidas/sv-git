# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError



class SaleOrder(models.Model):
    _inherit = ['sale.order']


    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):

        def get_view_id(name):
            view = self.env['ir.ui.view'].search([('name', '=', name)], limit=1)
            if not view:
                return False
            return view.id

        context = dict(self._context)
        sale_type = context.get('sale_type', 'order')

        if view_type == 'form' and sale_type == 'quote':
            view_id = get_view_id('pq_view_cust_quote_form')
        else:
            view_id = get_view_id('view_order_form')

        return super(SaleOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    # Overridden:
    @api.depends('currency_id')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        print("********************* _amount_all2 ***************************")
        for order in self:
            amount_untaxed = amount_tax = 0.0
            IQamount_untaxed = IQamount_tax = IQamount_total = 0.0

            order_currency = order.currency_id
            ctx = {'date' : order.date_order}

            for line in order.order_line:
                # amount_untaxed += line.price_subtotal
                # amount_tax += line.price_tax

                print(" Currency **", line.currency_id.name, order_currency.name)
                amount_untaxed += line.currency_id.with_context(ctx).compute(line.price_subtotal, order_currency)
                amount_tax += line.currency_id.with_context(ctx).compute(line.price_tax, order_currency)
                print("amount_untaxed here :", line.price_subtotal, amount_untaxed)


            # amount_untaxed = order.pricelist_id.currency_id.round(amount_untaxed)
            # amount_tax   = order.pricelist_id.currency_id.round(amount_tax)
            amount_untaxed = order.currency_id.round(amount_untaxed)
            amount_tax   = order.currency_id.round(amount_tax)
            amount_total = amount_untaxed + amount_tax

            # print("order.intorder_id", order.intorder_id, order.lead_id)

            if order.intorder_id:
                intOrd = order.intorder_id
                # print "intOrd.currency_id ", intOrd.currency_id.name, order_currency.name
                IQamount_untaxed = intOrd.currency_id.with_context(ctx).compute(intOrd.amount_untaxed, order_currency)
                IQamount_taxs = intOrd.currency_id.with_context(ctx).compute(intOrd.amount_tax, order_currency)
                IQamount_total = IQamount_untaxed + IQamount_tax


                print("iq Currency ** ", intOrd.currency_id.name, order_currency)
                print("iq untaxAmt here :", intOrd.amount_untaxed, IQamount_untaxed)


            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax'  : amount_tax,
                'amount_total': amount_total,

                'amount_untaxed1': amount_untaxed,
                'amount_tax1'  : amount_tax,
                'amount_total1': amount_total,

                'iq_amount_untaxed': IQamount_untaxed,
                'iq_amount_tax'  : IQamount_tax,
                'iq_amount_total': IQamount_total,

                'pl_amount_untaxed': amount_untaxed - IQamount_untaxed,
                'pl_amount_tax'  : amount_tax - IQamount_tax,
                'pl_amount_total': amount_total - IQamount_total,
            })

    # Overridden:
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=False, required=True)
    user_id = fields.Many2one('res.users', string='Sales Person', index=True, track_visibility='onchange', default=lambda self: self.env.user)

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('revised', 'Revised'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='draft')

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always', multi='xyz')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always', multi='xyz')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always', multi='xyz')

    # New:
    lead_id    = fields.Many2one('crm.lead', string='Enquiry', ondelete='restrict')
    sale_type  = fields.Selection(selection=[('quote', 'Customer Quotation'), ('order', 'Sale Order')], string='Order Type',
                                  default='order')

    intorder_id = fields.Many2one('internal.order', string='Internal Order', ondelete='restrict')
    backorder_id = fields.Many2one('sale.order', string='BackOrder', index=True, help="Original CQ mapped against each revised CQs")

    amount_untaxed1 = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', multi="xyz")
    amount_tax1 = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', multi="xyz")
    amount_total1 = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', multi="xyz")

    iq_amount_untaxed = fields.Monetary(string='IQ Untaxed Amount', store=True, readonly=True, compute='_amount_all', multi="xyz")
    iq_amount_tax     = fields.Monetary(string='IQ Taxes', store=True, readonly=True, compute='_amount_all', multi="xyz")
    iq_amount_total   = fields.Monetary(string='IQ Total', store=True, readonly=True, compute='_amount_all', multi="xyz")

    pl_amount_untaxed = fields.Monetary(string='Profit/Loss Untaxed Amount', store=True, readonly=True, compute='_amount_all', multi="xyz")
    pl_amount_tax     = fields.Monetary(string='Profit/Loss Taxes', store=True, readonly=True, compute='_amount_all', multi="xyz")
    pl_amount_total   = fields.Monetary(string='Profit/Loss Total', store=True, readonly=True, compute='_amount_all', multi="xyz")

    created_by_role = fields.Selection([('manager','Manager'), ('executive','Executive')], string='Created by', help="Sales user role created the CQ/SO")

    @api.model
    def _generate_Sequence(self, vals):
        cr, context = self._cr, self._context

        refNo = ''

        Company = self.env.user.company_id
        CompCode = (Company.code or Company.name)[:2].upper()

        sale_type = vals.get('sale_type', '')
        if sale_type == 'quote': refNo += 'CQ-'
        else: refNo += 'SO-'

        refNo += CompCode + '-'
        cr.execute(""" select id from sale_order where name ilike '""" + str(refNo) + """%' and backorder_id is null
                     order by to_number(substr(name,(length('""" + str(refNo) + """')+1)),'9999999999')
                     desc limit 1
                 """)
        rec = cr.fetchone()
        if rec:
            case = self.sudo().browse(rec[0])
            auto_gen = case.name[len(refNo) : ]
            refNo = refNo + str(int(auto_gen) + 1).zfill(5)
        else:
            refNo = refNo + '00001'
        return refNo

    
    def print_quotation(self):
        self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})

        return self.env.ref('sale.action_report_saleorder')\
            .with_context(discard_logo_check=True).report_action(self)

    
    def action_confirm_quote(self):
        """
            Prepares & Creates Sale Order.
        """
        self.ensure_one()

        context = self._context
        SOids = []

        websiteQuote = context.get('websiteQuote', False)

        vals = self.copy_data()
        vals = vals and vals[0] or {}
        vals.update({'origin': self.name,
                     'sale_type': 'order',
                     })

        newRec = self.create(vals)
        SOids.append(newRec.id)

        print ("websiteQuote", websiteQuote)
        newRec.action_confirm()

        self.write({'state': 'done'})

        if websiteQuote:
            return True

        xml_id = 'action_orders'
        result = self.env.ref('sale.%s' % (xml_id)).read()[0]
        res = self.env.ref('sale.view_order_form', False)
        domain = eval(result['domain'])
        domain.append(('id', 'in', SOids))
        result['domain'] = domain
        result['context'] = {'sale_type': 'order'}

        return result

    
    def button_mark_Sent(self):
        " Mark as Qtn Mail Sent manually"
        return self.write({'state':'sent'})

    
    def action_revised(self):
        self.ensure_one()
        cr, context = self._cr, dict(self._context)

        CallBy = context.get('callby', '')

        vals = self.copy_data()
        vals = vals and vals[0] or {}

        self.write({'state': 'revised'})

        cr.execute("select count(id) from sale_order where \
                    backorder_id is not null and lead_id = %s"%(self.lead_id.id))
        ExistRec = cr.fetchone()
        Cnt = (ExistRec and ExistRec[0] or 0) + 1

        name = str(self.name).split(' - ')
        name = name and name[0] or self.name
        RefNum = str(name) + " - R" + str(Cnt)
        vals.update({'backorder_id': self.id,
                     'name'  : RefNum,
                     'origin': self.origin,
                     })

        newID = self.create(vals)

        if CallBy == 'auto':
            return newID

        domain = [('id', 'in', [newID.id])]

        xml_id = 'action_cust_quote'
        result = self.env.ref('pantaq.%s' % (xml_id)).read()[0]
        rec_domain = eval(result['domain'])
        rec_domain.append(('id', '=', newID.id))
        result['domain'] = rec_domain
        return result

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self._generate_Sequence(vals) or 'New'

        if self.user_has_groups('sales_team.group_sale_manager'):
            vals['created_by_role'] = 'manager'
        else:
            vals['created_by_role'] = 'executive'

        return super(SaleOrder, self).create(vals)

    
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        context = dict(self._context)

        if vals.get('state', '') == 'sent':

            for case in self:
                StageID = self.env['crm.stage'].get_StageID('quote_sent')

                if case.sale_type == 'quote' and StageID:
                    ctx = context.copy()
                    ctx.update({'sysCall': True})
                    case.lead_id.with_context(ctx).write({'stage_id': StageID.id})
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    @api.depends('product_uom_qty', 'discount_perc', 'discount', 'price_unit', 'tax_id', 'profit_perc', 'profit')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            line.onchange_onAmount()

    # Overridden:
    discount  = fields.Float(string='Discount', digits=dp.get_precision('Discount'), default=0.0)
    currency_id = fields.Many2one("res.currency", related=False, string="Currency", readonly=False,
                                  required=True, store=True, default=21)
    # TODO: remove default of currency

    # New:
    discount_perc = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    price_cost  = fields.Float(string='Cost', digits=dp.get_precision('Discount'), default=0.0)
    profit_perc = fields.Float(string='Profit (%)', digits=dp.get_precision('Discount'), default=0.0)
    profit      = fields.Float(string='Profit', digits=dp.get_precision('Discount'), default=0.0)
    enqline_id  = fields.Many2one('pq.enquiry.lines', string='Enquiry Lines', ondelete='restrict')
    target_currency_id = fields.Many2one(related='enqline_id.currency_id', relation='res.currency', store=True, string='Target.Price Currency', readonly=True)
    target_price = fields.Float(related='enqline_id.target_price', string='Target Cost', store=True, readonly=True, digits=dp.get_precision('Product Price'))
    manufacturer_name = fields.Char(related='product_id.default_code', string='Manufacturer Name')
    product_description = fields.Text(related='product_id.product_description', string='Product Description')


    
    @api.onchange('product_uom_qty', 'discount_perc', 'discount', 'price_unit', 'tax_id', 'profit', 'profit_perc', 'price_cost')
    def onchange_onAmount(self):
        vals = {}
        order = self.order_id
        price = self.price_cost

        profit   = self.profit
        discount = self.discount

        if self.profit_perc:
            profit = order.currency_id.round(price * ((self.profit_perc or 0.0) / 100.0))
            vals.update({'profit':profit})

        price += profit

        if price != self.price_unit:
            vals.update({'price_unit':price})

        if self.discount_perc:
            discount = order.currency_id.round(price * ((self.discount_perc or 0.0) / 100.0))
            vals.update({'discount':discount})

        price -= discount

        taxes = self.tax_id.compute_all(price, order.currency_id, self.product_uom_qty, product=self.product_id, partner=self.order_id.partner_id)
        vals.update({
            'price_tax': taxes['total_included'] - taxes['total_excluded'],
            'price_total': taxes['total_included'],
            'price_subtotal': taxes['total_excluded'],
        })
        self.update(vals)
        return {}

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            sale_orders._create_invoices()
        elif self.advance_payment_method == 'all':
            sale_orders._create_invoices(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(
                        _('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(
                        _("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id, order.partner_shipping_id).ids
                else:
                    tax_ids = taxes.ids
                context = {'lang': order.partner_id.lang}
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'analytic_tag_ids': analytic_tag_ids,
                    'tax_id': [(6, 0, tax_ids)],
                    'is_downpayment': True,
                })
                del context
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}
