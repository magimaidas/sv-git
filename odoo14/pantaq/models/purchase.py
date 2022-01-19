# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends('order_line.product_id')
    def check_product_availability(self):
        for line in self:
            count = 0
            for lines in line.order_line:
                if not lines.product_id:
                    count=count+1
                    line.update({
                        'check_products': True
                        })
                if count == 0:
                    line.update({
                        'check_products': False
                        })


    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):

        def get_view_id(name):
            view = self.env['ir.ui.view'].search([('name', '=', name)], limit=1)
            if not view:
                return False
            return view.id

        context = dict(self._context)
        po_type = context.get('po_type', 'purchase')

        if view_type == 'form' and po_type == 'rfq':
            view_id = get_view_id('view_pq_rfq_form')

        if view_type == 'tree' and po_type == 'rfq':
            view_id = get_view_id('view_pq_rfq_tree')

        res = super(PurchaseOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type != 'search' and self.env.uid != SUPERUSER_ID and po_type == 'purchase':
            # Check if user is in group that allow creation, updation & deletion
            has_my_group = self.env.user.has_group('purchase.group_purchase_manager')
            if not has_my_group:
                root = etree.fromstring(res['arch'])
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)

        return res

    # Overridden:
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('qtn_received', 'Response Received'),
        ('rfq_revised', 'RFQ Revised')
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')


    # New:
    po_type = fields.Selection([('rfq', 'RFQ'),('purchase', 'Purchase Order')], string='Order Type', default='purchase')
    remarks = fields.Text(string="Remarks")
    lead_id = fields.Many2one('crm.lead', string='Enquiry', index=True)
    backorder_id = fields.Many2one('purchase.order', string='BackOrder', index=True, help="Original RFQ mapped against each revised RFQs")

    irattachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments',
        domain=lambda self: [('res_model', '=', self._name)])
    quotes_attachment_ids = fields.Many2many('ir.attachment', string='Quotations')
    terms_condition_id = fields.Many2one('terms.condition',string="Terms & Condition")
    check_products = fields.Boolean(string="check whether product is there in line",compute="check_product_availability",track_visibility='onchange')

    def action_set_date_planned(self):
        print("action_set_date_planned --- Dummy action")


    @api.model
    def _prepare_IntQuotation(self, rfq):
        """ Prepare the dict of values to create the new Internal Order from the RFQ.
        """
        values = {}

        for field in ['currency_id', 'company_id', 'lead_id']:
            if rfq._fields[field].type == 'many2one':
                values[field] = rfq[field].id
            else:
                values[field] = rfq[field] or False

        values.update({
            'name' : 'New',
            # 'note' : self.notes,
            'partner_id': self.lead_id.sudo().partner_id.id #used sudo() as PE doesn't have read access to Enquiries that aren't assigned.
        })

        return values

    
    def print_quotation(self):
        # self.write({'state': "sent"})
        return self.env.ref('purchase.report_purchase_quotation').report_action(self)

    
    def button_create_InternalQtn(self):
        """
            Creates Internal Quotation for the Approved Lines
        """
        context = dict(self._context)
        cache = {}
        IntOrds = []

        CallBy = context.get('callby', '')
        selectedLns = context.get('selectedRfqLines', [])

        intord_obj = self.env['internal.order']

        for case in self:
            io = False
            approvedLines = []
            EnquiryRec = case.lead_id
            EnqLnNew = {}

            for rol in case.order_line:
                if CallBy == 'rfqProd' and rol.id not in selectedLns:
                    continue
                elif rol.rfq_status != 'approved':
                    continue

                approvedLines.append(rol.id)
                EnqLnNew.update({rol.enqline_id.id: rol.product_id.name})

            if not approvedLines:
                raise Warning(_("Please approve a product to proceed !!"))

            domain = (
                    ('state', '=', 'draft'),
                    ('lead_id', '=', EnquiryRec.id),
                    )

            if domain in cache:
                io = cache[domain]
            else:
                io = intord_obj.search([dom for dom in domain], order='id desc', limit=1)
                io = io[0] if io else False
                cache[domain] = io

            # iqRevise = False
            if not io:
                # Check: IQ Revision:
                # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                domain = (
                        ('state', '=', 'submit'),
                        ('lead_id', '=', EnquiryRec.id),
                        )

                io = intord_obj.search([dom for dom in domain], order='id desc', limit=1)
                if io:
                    io = io[0]
                    iqRevise = True
                    cache[domain] = io

                # if iqRevise:
                #     ctx = context.copy()
                #     ctx['callby'] = 'RFQ'
                #     io = io.with_context(ctx).action_revised()
                #     cache[domain] = io
                #
                # else:
                vals = self._prepare_IntQuotation(case)
                io = intord_obj.create(vals)
                cache[domain] = io

            IntOrds.append(io.id)
            for ln in io.order_line:
                EnqLnID = ln.enqline_id.id

                # Check: IQ is already been created from this Product.
                if EnqLnID in EnqLnNew.keys():# and not iqRevise:
                    raise Warning(_("Internal Quotation has been created for this Product [%s] \n"
                                    "Please refer the Quotation: %s")%(EnqLnNew[EnqLnID], io.name))

            # if not iqRevise:
            approvedLines = self.env['purchase.order.line'].browse(approvedLines)
            order_line = approvedLines._prepare_RFQlines_IQlines(io)
            io.write({'order_line': order_line})

        if CallBy == 'rfqProd':
            return io.id

        xml_id = 'action_internal_quotations'
        result = self.env.ref('pantaq.%s' % (xml_id)).read()[0]
        domain = eval(result['domain'])
        domain.append(('id', 'in', IntOrds))
        result['domain'] = domain
        return result

    
    def button_rfq_done(self):
        return self.write({'state':'qtn_received'})


    
    def button_mark_Sent(self):
        " Mark as RFQ/PO Mail Sent manually"
        return self.write({'state':'sent'})

    
    def button_modify_rfq(self):
        """
        Creates a New RFQ and allows to modify
        """

        case, cr = self, self._cr
        vals = case.copy_data()
        vals = vals and vals[0] or {}

        cr.execute("select count(id) from purchase_order where po_type = 'rfq' and \
                    backorder_id is not null and lead_id = %s and partner_id = %s"%(case.lead_id.id, case.partner_id.id))
        ExistRec = cr.fetchone()
        Cnt = (ExistRec and ExistRec[0] or 0) + 1

        name = str(case.name).split(' - ')
        name = name and name[0] or case.name
        rfqNum = str(name) + " - R" + str(Cnt)
        vals.update({'backorder_id': case.id,
                     'name': rfqNum,
                     'origin': case.origin,
                     })

        newRFQ = self.create(vals)
        self.write({'state': 'rfq_revised'})

        message = _("This RFQ has been revised to: <a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>") % (newRFQ.id, newRFQ.name)
        self.message_post(body=message)

        message = _("This RFQ has been created from: <a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>") % (self.id, self.name)
        newRFQ.message_post(body=message)

        xml_id = 'purchase_rfq'
        result = self.env.ref('purchase.%s' % (xml_id)).read()[0]
        domain = eval(result['domain']) if result['domain'] else []
        domain.append(('id', '=', newRFQ.id))
        result['domain'] = domain
        return result

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            po_type = vals.get('po_type', '')

            if po_type == 'rfq':
                vals['name'] = self.env['ir.sequence'].next_by_code('rfq.order') or '/'
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order') or '/'

        r = super(PurchaseOrder, self).create(vals)
        print("r.po_type :", r.po_type)
        return r

    
    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        context = dict(self._context)

        if vals.get('state', '') == 'sent':

            for case in self:
                StageID = self.env['crm.stage'].get_StageID('rfq_sent')

                ctx = context.copy()
                ctx.update({'sysCall': True})

                if case.po_type == 'rfq' and StageID:
                    case.lead_id.with_context(ctx).write({'stage_id': StageID.id})
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Overridden:
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)]
                                 , change_default=True, required=False)
    product_uom = fields.Many2one('uom.uom', string='Product Unit of Measure', required=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('qtn_received', 'Qtn Received')
        ], related='order_id.state', string='Status', readonly=True, index=True, default='draft')


    # New:
    rfq_status   = fields.Selection([('approved', 'Approved'),('rejected', 'Rejected')], string="Status")
    enqline_id   = fields.Many2one('pq.enquiry.lines', string='Enquiry Lines', ondelete='restrict')
    target_currency_id = fields.Many2one(related='enqline_id.currency_id', relation='res.currency', store=True, string='Target.Price Currency', readonly=True)
    target_price = fields.Float(related='enqline_id.target_price', string='Target Price', store=True, readonly=False, digits=dp.get_precision('Product Price'))
    lead_id      = fields.Many2one(related='enqline_id.lead_id', relation='crm.lead', store=True, string='Enquiry')
    po_type      = fields.Selection([('rfq', 'RFQ'),('purchase', 'Purchase Order')],
                                    related='order_id.po_type', string='Order Type')
    partner_id = fields.Many2one(related='order_id.partner_id', relation='res.partner', store=True, string='Vendor')
    org_price_unit = fields.Float('Original Unit Price', digits=dp.get_precision('Product Price'), default=0.0, required=True)
    hs_code = fields.Char(string='HS Code')
    manufacturer_name = fields.Char(string='Manufacturer Name')
    interval = fields.Integer(string="Lead Time")
    rule_type = fields.Selection([('days', 'Day(s)'), ('weeks', 'Week(s)'), ('months', 'Month(s)')], string="Lead Time Rule", default='days')
    currency_id_inherit = fields.Many2one('res.currency',string='Currency')
    currency_id = fields.Many2one('res.currency',related='currency_id_inherit',string='Currency')


    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.manufacturer_name = self.product_id.name

    @api.onchange('org_price_unit')
    def onchange_originalPrice(self):
        context = dict(self._context)
        self.price_unit = self.org_price_unit

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        '''
        removed below 2 lines from a standard function
        '''
        # self.price_unit = self.product_qty = 0.0
        # self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        # result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        self._compute_tax_id()

        self._suggest_quantity()
        self._onchange_quantity()

        return result

    def _suggest_quantity(self):
        # used the standard function to remove the auto suggesting quamtities

        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        seller_min_qty = self.product_id.seller_ids\
            .filtered(lambda r: r.name == self.order_id.partner_id and (not r.product_id or r.product_id == self.product_id))\
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
            self.product_uom = seller_min_qty[0].product_uom
        # else:
        #     self.product_qty = 1.0

    # Overridden
    
    @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty = line.product_qty

    
    def button_toggle_approve(self):
        self.ensure_one()

        if not self.product_id:
            raise Warning(_("Please map a Product to proceed !!"))

        elif not self.org_price_unit:
            raise Warning(_("Please enter the Original Unit price to proceed further!!"))

        return self.write({'rfq_status' : 'approved'})

    
    def button_toggle_reject(self):
        return self.write({'rfq_status' : 'rejected'})

    
    def _prepare_RFQlines_IQlines(self, io):
        lines = []

        for rl in self:
            vals = {}

            EnqQty = rl.enqline_id.product_uom_qty or 1
            RfqQty = rl.product_qty or 1

            if rl.order_id and rl.order_id.partner_id.taxin_cost:
                price = rl.price_total
            else:
                price = rl.price_unit

            price_cost = rl.order_id.currency_id.round((price / RfqQty) * EnqQty)

            for field in ['name', 'product_id', 'product_uom']:
                if rl._fields[field].type == 'many2one':
                    vals[field] = rl[field].id
                else:
                    vals[field] = rl[field] or False

            vals.update({
                'product_uom_qty': EnqQty,
                'rfqline_id' : rl.id,
                'price_unit' : price_cost,
                'price_cost' : price_cost,
                'hs_code'    : rl.hs_code,
            })
            lines.append(vals)

        return map(lambda x:(0,0,x), lines)

    
    def action_create_InternalQtn4lines(self):

        EnqLinesGprd, RfqGrp = {}, {}
        PrevEnquiry = False
        purchase_obj = self.env['purchase.order']

        for idx, case in enumerate(self):
            Enquiry = case.order_id and case.order_id.lead_id or False

            if not Enquiry: continue

            if idx == 0:
                PrevEnquiry = Enquiry.id

            if PrevEnquiry != Enquiry.id:
                raise Warning(_("Please select products belonging to same Enquiry !!"))

            key = (case.enqline_id, Enquiry.id)
            if key not in EnqLinesGprd:
                EnqLinesGprd[key] = {'rfqline': case.id, 'rfq': case.order_id, 'rfqno': case.order_id.name}
            else:
                raise Warning(_("Product '%s' has been selected already, "
                                "from RFQ [%s] !!")%(case.name, EnqLinesGprd.get(key, {}).get('rfqno', '')))


            for k, v in EnqLinesGprd.items():
                key = v.get('rfq', False)
                rfqline = v.get('rfqline', False)

                if not key in RfqGrp:
                    RfqGrp[key] = [rfqline]
                else:
                    RfqGrp[key].append(rfqline)


        IntOrds = []
        for k, v in RfqGrp.items():
            ioID = k.with_context({'selectedRfqLines': v, 'callby': 'rfqProd'}).button_create_InternalQtn()
            IntOrds.append(ioID)

        IntOrds = list(set(IntOrds))

        xml_id = 'action_internal_quotations'
        result = self.env.ref('pantaq.%s' % (xml_id)).read()[0]
        domain = eval(result['domain'])
        domain.append(('id', 'in', IntOrds))
        result['domain'] = domain
        return result