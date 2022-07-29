# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time


class wizardRFQ(models.TransientModel):
    _name = "pq.wizard.rfq"
    _description = 'Wizard RFQ'

    def _get_domain(self):
        """
            Filter vendors used already for the same enquiry.
        """
        domain = []

        lead_id = self._context.get('lead_id', False)

        partners = self.env['res.partner'].search([('is_company', '=', True)])
        vendors = list(map(lambda x: x.id, partners))
        domain += [('id', 'in', vendors)]

        if lead_id:
            rfqs = self.env['purchase.order'].search([('lead_id', '=', lead_id)])
            vendors = list(map(lambda x: x.partner_id.id, rfqs))
            domain += [('id','not in',vendors)]
        return domain

    lead_id     = fields.Many2one('crm.lead', string='Enquiry')
    line_ids    = fields.One2many('pq.wizard.rfqlines', 'wiz_id', string='Product Details')
    # linem2m_ids = fields.Many2many('pq.wizard.rfqlines', string='Lines')
    partner_ids = fields.Many2many('res.partner', string='Supplier', domain=lambda self: self._get_domain())

    @api.model
    def default_get(self, fields):
        res = super(wizardRFQ, self).default_get(fields)
        context = dict(self._context or {})
        lead_obj = self.env['crm.lead']

        lead_id = context.get('active_id', False)
        res.update({
            'lead_id': lead_id,
        })
        return res

    def create_purchase_order(self, supplierIDs):
        purchase_order = self.env['purchase.order']
        for supplierID in supplierIDs:
            lines = []
            for pline in self.line_ids:
                lines.append((0, 0, {
                            'name': pline.name,
                            'manufacturer_name': pline.manufacturer_name,
                            # 'origin': pline.lead_id.enq_number,
                            'product_id': pline.product_id.id,
                            'product_qty': pline.product_uom_qty,
                            'product_uom': pline.product_uom.id,
                            'company_id': self.env.user.company_id.id,
                            'price_unit': 0,
                            'currency_id_inherit':pline.currency_id.id,
                            'target_price': pline.target_price,
                            'enqline_id': pline.enqln_id.id,
                            'lead_id': pline.lead_id.id,
                            'date_planned': self.lead_id.date_deadline or datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            }
                        ))
            # Create Purchase Order for each vendor
            purchase_order.create({
                'partner_id': supplierID,
                'lead_id': self.line_ids[0].lead_id.id,
                'po_type': 'rfq',
                'order_line': lines
            })


    
    def button_proceed(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)
        # After sales team submits enquiry, if PM proceeds with converting to RFQ without assigning to anyone then assigning the enquiry to him.
        if not res_pool.assign_id:
            res_pool.assign_id = self._uid
            res_pool.button_assign() # This function will update the stage to Assigned and send notification mail

        DefSupplierIds = list(map(lambda x: x.id, self.partner_ids))
        supplierIDs = []

        Lines = self.line_ids

        if not Lines:
            raise Warning(_("Please add Product Details to proceed further!!"))

        for ln in Lines:

            if not ln.partner_ids and not DefSupplierIds:
                raise Warning(_("Please map atleast one Supplier to create RFQ for the product [%s]")%(ln.product_id.name))


            supplierIDs = list(map(lambda x: x.id, ln.partner_ids))
            supplierIDs += DefSupplierIds
            supplierIDs = list(set(supplierIDs))

        self.create_purchase_order(supplierIDs)

            # ln._PQ_action_procurement_create(supplierIDs=supplierIDs)

        xml_id = 'purchase_rfq'
        result = self.env.ref('purchase.%s' % (xml_id)).read()[0]
        domain = eval(result['domain']) if result['domain'] else []
        domain.append(('lead_id', '=', self.lead_id.id))
        domain.append(('state','=', 'draft'))
        domain.append(('partner_id', 'in', supplierIDs))
        result['domain'] = domain
        return result


class wizardRFQLines(models.TransientModel):
    _name = "pq.wizard.rfqlines"
    _description = 'Wizard RFQ Lines'

    wiz_id    = fields.Many2one('pq.wizard.rfq', string='Wiz RFQ', ondelete='cascade')
    name      = fields.Text(string='Description', required=True)

    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    manufacturer_name = fields.Char('Manufacturer Name')
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom     = fields.Many2one('uom.uom', string='Unit of Measure')
    partner_ids     = fields.Many2many('res.partner', string='Supplier')
    enqln_id        = fields.Many2one('pq.enquiry.lines', string='EnquiryLine ID')
    lead_id         = fields.Many2one('crm.lead', string='Enquiry')

    has_targetprice = fields.Boolean('I have Target Price')
    target_price    = fields.Float('Targeted Price / Unit', help="Enter Target Price for a unit.")
    currency_id     = fields.Many2one('res.currency', 'Currency',
                    default=lambda self: self.env.user.company_id.currency_id)

    product_name = fields.Char('Product Name')
    product_description = fields.Text('Product Description')


    def _prepare_enquiryline_procurement(self, group_id=False):
        self.ensure_one()

        targetPrice = self.currency_id.compute(self.target_price, self.env.user.company_id.currency_id)

        return {
            'name'        : self.name,
            'origin'      : self.lead_id.enq_number,
            'product_id'  : self.product_id.id,
            'product_qty' : self.product_uom_qty,
            'product_uom' : self.product_uom.id,
            'company_id'  : self.env.user.company_id.id,
            'target_price': targetPrice,
            'enqline_id'  : self.enqln_id.id,
            'lead_id'  : self.lead_id.id,
        }


    
    def _PQ_action_procurement_create(self, supplierIDs=[]):
        # Replicated from Sale

        # """
        # Create procurements based on quantity ordered. If the quantity is increased, new
        # procurements are created. If the quantity is decreased, no automated action is taken.
        # """

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        new_procs = self.env['purchase.order'] #Empty recordset

        for line in self:
            vals = line._prepare_enquiryline_procurement()

            vals['product_qty'] = line.product_uom_qty
            vals['partner_ids'] = [(6, 0, supplierIDs)]
            new_proc = self.env["purchase.order"].create(vals)
            new_procs += new_proc
        new_procs.run()
        return new_procs

    
    def button_edit(self):
        'button edit'


class ProductCompare(models.TransientModel):
    _name = "pq.wiz.rfq.productcompare"
    _description = 'Wizard RFQ products compare'

    lead_id     = fields.Many2one('crm.lead', string='Enquiry', domain="[('state', '=', 'done')]", required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    line_ids    = fields.One2many('pq.wiz.rfq.productcompare.lines', 'wiz_id', string='Lines')


    
    def button_proceed(self):
        self.ensure_one()
        cr = self._cr

        cr.execute("delete from pq_wiz_rfq_productcompare_lines where create_uid = %s"%(self._uid))

        poln_obj = self.env['purchase.order.line']
        wizln_obj = self.env['pq.wiz.rfq.productcompare.lines']

        cr.execute("""
                    select l.id
                    from purchase_order po
                    inner join purchase_order_line l on po.id = l.order_id
                    where po.lead_id = %s and l.currency_id_inherit = %s
                  """%(self.lead_id.id,self.currency_id.id))

        lnids = map(lambda x: x[0], cr.fetchall())
        polnIDs = poln_obj.browse(lnids)

        for ln in polnIDs:
            # vals = ln.copy_data()
            vals = {}
            vals.update({
                'wiz_id'     : self.id,
                'rfqline_id' : ln.id,
                'currency_id': self.currency_id.id,
                'price_subtotal': ln.price_subtotal,
                'price_total'   : ln.price_total,
                'target_price': ln.target_price,
                'order_id': ln.order_id.id,
                'lead_id': ln.order_id.lead_id.id,
                'partner_id': ln.partner_id.id,
                'product_id': ln.product_id.id,
                'name': ln.product_id.name,
                'company_id': ln.company_id.id,
                'enqln_qty': ln.enqline_id.product_uom_qty,
                'product_qty': ln.product_qty,
                'interval': ln.interval,
                'price_unit': ln.price_unit,
                })
            print("Price",ln.price_subtotal)
            print("Target Price",ln.target_price)

            wizln_obj.create(vals)

        xml_id = 'action_rfqcomparelines_form'
        result = self.env.ref('pantaq.%s' % (xml_id)).read()[0]
        result['domain'] = [('wiz_id', '=', self.id)]
        result['name'] = 'NAME ***'
        return result


class ProductCompareLines(models.TransientModel):
    _name = "pq.wiz.rfq.productcompare.lines"
    _description = 'Wizard RFQ products compare'


    @api.depends('product_qty', 'price_unit', 'currency_id')
    def _compute_amount(self):
        for line in self:
            ToCurrency = line.currency_id
            now = time.strftime('%Y-%m-%d')
            ctx = {'date' : now}

            line.update({
                # 'org_price_unit1': 55,
                'price_unit1'    : line.rfq_currency_id.with_context(ctx).compute(line.price_unit, ToCurrency),
                'price_total1'   : line.rfq_currency_id.with_context(ctx).compute(line.price_total, ToCurrency),
                'price_subtotal1': line.rfq_currency_id.with_context(ctx).compute(line.price_subtotal, ToCurrency),
                # 'target_price1': line.rfq_currency_id.with_context(ctx).compute(line.target_price, ToCurrency),

            })


    wiz_id    = fields.Many2one('pq.wiz.rfq.productcompare', string='Wiz', ondelete='cascade')
    name      = fields.Text(string='Product Description', readonly=True)
    product_qty = fields.Float(string='RFQ Qty', digits=dp.get_precision('Product Unit of Measure'), readonly=True,group_operator=False)
    partner_id  = fields.Many2one(relation='res.partner', related='order_id.partner_id', string='Vendor', store=True, readonly=True)

    order_id    = fields.Many2one('purchase.order', string='RFQ Reference', readonly=True)
    rfqline_id  = fields.Many2one('purchase.order.line', string='RFQ Line Reference', readonly=True)
    enqline_id  = fields.Many2one('pq.enquiry.lines', string='Enquiry Lines', readonly=True)
    lead_id     = fields.Many2one(related='enqline_id.lead_id', relation='crm.lead', string='Enquiry', readonly=True)
    enqln_qty   = fields.Float(related='enqline_id.product_uom_qty', digits=dp.get_precision('Product Unit of Measure'), string='Requested Qty', readonly=True)

    product_id  = fields.Many2one('product.product', string='Product', readonly=True)
    product_uom = fields.Many2one('uom.uom', string='Product Unit of Measure', readonly=True)

    rfq_status   = fields.Selection([('approved', 'Approved'),('rejected', 'Rejected')], string="Status", readonly=True)
    company_id   = fields.Many2one(relation='res.company', related='order_id.company_id', string='Company', readonly=True)

    # org_price_unit = fields.Float('Original Unit Price', readonly=True)

    price_unit   = fields.Float(string='Final Unit Price', readonly=True,group_operator=False)
    price_subtotal  = fields.Float(string='Subtotal', readonly=True,group_operator=False)
    price_total = fields.Float(string='Total', readonly=True,group_operator=False)
    rfq_currency_id = fields.Many2one(relation='res.currency', related='order_id.currency_id', string='Currency', readonly=True)

    # org_price_unit1 = fields.Float(compute='_compute_amount', string='Original Unit Price', readonly=True)
    target_price  = fields.Float(string='Target Price',group_operator=False)
    price_unit1   = fields.Float(compute='_compute_amount', string='Final Unit Price', readonly=True, store=True,group_operator=False)
    price_subtotal1 = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True,
                                      help="Subtotal (without Tax)",group_operator=False)
    price_total1 = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True,
                                   help="Total (with Tax)",group_operator=False)
    currency_id  = fields.Many2one('res.currency', string='Currency', readonly=True)
    interval = fields.Integer(string="Lead Time",group_operator=False)
    rule_type = fields.Selection([('days', 'Day(s)'), ('weeks', 'Week(s)'), ('months', 'Month(s)')], string="Lead Time Rule", default='days')
    sequence = fields.Integer(string="Sequence", readonly=True, invisible=True)

    
    def button_toggle_approve(self):
        if not self.product_id:
            raise Warning(_("Please map a Product to proceed !!"))
        self.write({'rfq_status' : 'approved'})
        return self.rfqline_id.write({'rfq_status' : 'approved'})

    
    def button_toggle_reject(self):
        self.write({'rfq_status' : 'rejected'})
        return self.rfqline_id.write({'rfq_status' : 'rejected'})

    
    def action_process_RFQLines(self):

        context = self._context
        rfq_obj = self.env['purchase.order.line']

        active_id = context.get('active_id', False)
        actrec = self.browse(active_id)

        if not actrec.wiz_id: return True

        apprLn = []

        for ln in actrec.wiz_id.line_ids:
            if ln.rfq_status == 'approved':
                apprLn.append(ln.rfqline_id.id)

        rfqLns = rfq_obj.browse(apprLn)
        return rfqLns.action_create_InternalQtn4lines()

class AskRevision(models.TransientModel):
    _name = "pq.wiz.ask.revision"
    _description = 'Ask for revision'

    note = fields.Html('Note')


    
    def button_proceed(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)

        Partners = map(lambda x: x.partner_id.id, res_pool.lead_id.team_proc_id.member_ids)

        for case in self:
            body_html = "<div><b>%(title)s</b></div>%(note)s" % {
                'title': _('Asked for Revision'),
                'note': case.note or '',
            }
            res_pool.message_post(body_html,
                                  partner_ids= [(4, pid) for pid in Partners])
        return True


class CancelEnquiry(models.TransientModel):
    _name = "pq.wiz.cancel.enquiry"
    _description = 'Cancel Enquiry'

    lost_reason = fields.Many2one('crm.lost.reason', string='Reason for Cancellation', required=True, index=True)

    
    def button_cancel(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)

        res_pool.lost_reason = self.lost_reason # updates the lost reason in enquiry

        res_pool.button_cancel()

        return True

class RequestCancelEnquiry(models.TransientModel):
    _name = "pq.wiz.request.cancel.enquiry"
    _description = 'Request for Cancellation of Enquiry'

    lost_reason = fields.Many2one('crm.lost.reason', string='Reason for Cancellation', required=True, index=True)

    
    def button_request_cancel(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)

        res_pool.lost_reason = self.lost_reason # updates the lost reason in enquiry
        res_pool.cancellation_requested_by = self._uid # updates the person requested for cancellation

        res_pool._send_mail_notify(action='request_cancel')

        return True

class ApproveCancelEnquiry(models.TransientModel):
    _name = "pq.wiz.approve.cancel.enquiry"
    _description = 'Approve Cancellation Request for Enquiry'

    notify_sales = fields.Boolean(string='Notify Sales Team member(s)', default=True, help="Enable this check box to send mail to sales team members - SM and SE if requested for cancellation")
    notify_procurement = fields.Boolean(string='Notify Procurement Team member(s)', default=True, help="Enable this check box to send mail to procurement team members - PE if works on it")

    
    def button_approve_cancel(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)

        res_pool.notify_sales = self.notify_sales # updates the notify_sales in enquiry
        res_pool.notify_procurement = self.notify_procurement # updates the notify_procurement in enquiry

        res_pool.button_approve_cancel()

        return True


class AssignEnquiry(models.TransientModel):
    _name = "pq.wiz.assign.enquiry"
    _description = 'Assign Enquiry'

    def _get_domain(self):
        currently_assigned_to = self._context.get('currently_assigned_to', False)
        if not currently_assigned_to:
            return [('sale_team_id', '=', self.env.user.sale_team_id.id)]
        else:
            return [('sale_team_id', '=', self.env.user.sale_team_id.id),('id', '!=', currently_assigned_to)]

    assign_id  = fields.Many2one('res.users', string='Assign To', required=True, domain=lambda self: self._get_domain())

    
    def button_assign(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)

        res_pool.assign_id = self.assign_id # updates the assign_id in enquiry

        res_pool.button_assign()

        return True

class TransferEnquiry(models.TransientModel):
    _name = "pq.wiz.transfer.enquiry"
    _description = 'Transfer Enquiry'

    def _get_domain(self):
        return [('category','=', 'procurement'), ('id', '!=', self.env.user.sale_team_id.id)]

    team_proc_id = fields.Many2one('crm.team', string='Transfer To', required=True, domain=lambda self: self._get_domain())

    
    def button_transfer(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)

        res_pool.transferred_to = self.team_proc_id.user_id.id # updates the procurement team manager to whom the enquiry is transferred.

        res_pool._send_mail_notify(action='request_transfer')

        return True

class AcceptTransferredEnquiry(models.TransientModel):
    _name = "pq.wiz.accept.transferred.enquiry"
    _description = 'Accept Transferred Enquiry'

    assign_id  = fields.Many2one('res.users', string='Assign To', required=True, domain=lambda self: [('sale_team_id', '=', self.env.user.sale_team_id.id)])

    
    def button_accept_and_assign(self):
        context = dict(self._context)

        res_model = context.get('active_model', '')
        res_id = context.get('active_id', False)

        if not res_model or not res_id:
            return False

        res_pool = self.env[res_model].browse(res_id)

        res_pool._send_mail_notify(action='accept_transfer')
        res_pool.transferred_to = False# updates the transferred_to with False in enquiry, so this will make sure the enquiry transfer request has been accepted.
        res_pool.assign_id = self.assign_id.id# assigns enquiry to PE/PM selected from the wizard.
        res_pool._send_mail_notify(action='assign')

        return True