# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval


class Stage(models.Model):
    _inherit = 'crm.stage'

    stage_type = fields.Selection([('new', 'New'), ('assigned', 'Assigned'), ('rfq_sent', 'RFQ Sent'), ('io_created', 'IntOrder Created'), ('quote_sent', 'Customer Quote Sent')],
                                  string='Stage Type', help='Set this to action automatically')


    def get_StageID(self, domain=''):
        res = self.search([('stage_type','=', domain)], order='sequence desc')
        return res and res[0] or False


class Lead(models.Model):
    _inherit = ['crm.lead']
    _order = "priority desc,enq_number desc,date_action_last,id desc"
    _rec_name = 'enq_number' #need to check as it's not working. Currently implemented with name_get()


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):

        if view_type == 'tree':
            view_id = self.env.ref('pantaq.view_crm_enquiry_tree').id

        elif view_type == 'form':
            view_id = self.env.ref('pantaq.view_crm_enquiry_form').id

        return super(Lead, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    
    @api.depends('purchase_ids')
    def _get_count_records(self):
        nbr = inbr1 = inbr2 = 0
        for order in self.purchase_ids:
            if order.state in ('draft', 'sent') and order.po_type == 'rfq':
                nbr += 1

        for order in self.intorder_ids:
            inbr1 += 1
            if order.state in ('submit', 'done'):
                inbr2 += 1

        self.rfq_count = nbr
        self.intord1_count = inbr1
        self.intord2_count = inbr2

    
    @api.depends('transferred_to')
    def _update_transferred_to_me(self):
        """
        This method helps to find out whether the enquiry is assigned to the logged in PM or not.
        If the enquiry is assigned to logged in PM then workflow buttons are shown based on that
        """
        if self.transferred_to and self.transferred_to.id == self._uid:
            self.transferred_to_me = True
        else:
            self.transferred_to_me = False


    def _get_msgDomain(self):
        """
            Filter Audit Log/Message Log
            to be hide Customer related record from Purchase User.

        """
        domain = [('model', '=', self._name)]

        PurchaseGrp = self.user_has_groups('purchase.group_purchase_user')
        SalesGrp = self.user_has_groups('sales_team.group_sale_salesman')

        if PurchaseGrp and not SalesGrp:
            domain += ['|', ('is_purchasegroup','=', True), ('force_display','=',True)]

        return domain

    # Overridden:
    message_ids = fields.One2many('mail.message', 'res_id', string='Messages',
                    domain=_get_msgDomain,
                    auto_join=True)
    name = fields.Char('Opportunity', required=True, index=False)
    planned_revenue = fields.Float('Expected Revenue', track_visibility='none')
    date_deadline = fields.Date('Expected Closing', help="Estimate of the date on which the opportunity will be won.", required=True)

    # New:
    enq_number = fields.Char(string='Enquiry Number', readonly = True, index=True, copy=False, default=lambda self: _('New'))
    enquiry_lines = fields.One2many('pq.enquiry.lines', 'lead_id', string='Lines', copy=True)
    date_created = fields.Date(string='Generated Date', required=True, readonly=True, index=True, copy=False,
                               default=fields.Datetime.now().date())
    date_received = fields.Date(string='Received Date', required=True, index=True, copy=False,
                                default=fields.Datetime.now().date(), readonly=True,
                                states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Submitted'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    team_proc_id = fields.Many2one('crm.team', string='Procurement Team', ondelete='set null',
                           index=True, track_visibility='onchange',
                           help='When sending mails, the default email address is taken from the procurement team.')

    purchase_ids = fields.One2many('purchase.order', 'lead_id', string='Purchase Orders')
    rfq_count  = fields.Integer(compute='_get_count_records', string="Number of RFQs", readonly=True)
    assign_id  = fields.Many2one('res.users', string='Assigned To', index=True, track_visibility='onchange', domain=lambda self: [('sale_team_id', '=', self.env.user.sale_team_id.id)])

    intorder_ids = fields.One2many('internal.order', 'lead_id', string='Internal Orders')
    intord1_count = fields.Integer(compute='_get_count_records', string="Number of IO", readonly=True)
    intord2_count = fields.Integer(compute='_get_count_records', string="Number of IO - Confirmed", readonly=True)

    hide_from_executives = fields.Boolean(string='Hide from executives', help="Enable this check box to hide this enquiry from procurement executives users role")
    cancellation_requested_by  = fields.Many2one('res.users', string='Cancellation Requested By', track_visibility='onchange') #this stores the person requested cancellation, usually SM/SE
    notify_sales = fields.Boolean(string='Notify Sales Team')# When approving cancellation request, this boolean is given as an optional whether to notify sales team or not
    notify_procurement = fields.Boolean(string='Notify Procurement Team')# When approving cancellation request, this boolean is given as an optional whether to notify procurement team or not
    transferred_to = fields.Many2one('res.users', string='Transferred To')# When a PM requests for transfer, the PM to whom the enquiry is transferred is stored here.
    transferred_to_me = fields.Boolean('Transferred To Me', compute='_update_transferred_to_me')# This contains the value TRUE if logged in PM is equal to transferred to

    companies = fields.Selection(selection='_get_companies', string='Company', required=True, default=lambda self: self.env.user.company_id.code)
    sales_manager = fields.Boolean('Sales Manager', compute='_compute_sales_manager')

    _sql_constraints = [
        ('number_uniq', 'unique(enq_number)', 'Enquiry Number must be unique!'),
    ]


    def name_get(self):
        result = []
        for enquiry in self:
            name = enquiry.enq_number
            result.append((enquiry.id, name))
        return result


    def button_create_InternalQtn(self):
        """
            Creates Internal Quotation for the Approved Lines (this code works only for the active screen)
        """
        # xml_id = 'action_rfqcomparelines_form'
        # result = self.env.ref('pantaq_old.%s' % (xml_id)).read()[0]
        # result['domain'] = [('lead_id', '=', self.id), ('rfq_status', '=', 'approved')]
        # result['name'] = 'Approved Items'
        # result['target'] = 'new'
        # return result
        # Above code is working but not as per the requirement

        self.ensure_one()
        purchase_id = self.env['purchase.order'].search([('lead_id','=',self.id)])
        internal_quote_id = self.env['internal.order']
        vals=[]
        io_id = self.env['internal.order'].search([('lead_id','=',self.id),('state','=','draft')])
        io_count=0
        # can write query and optimize - need to be done

        for line in io_id:
            io_count = io_count+1
            if io_count >= 1:
                raise Warning(_("Internal Quotation is already created. Kindly check it !!")) 


        if purchase_id:
            for line in purchase_id:
                if line.state =='qtn_received':
                    for lines in line.order_line:
                        if lines.rfq_status == 'approved':
                            vals.append([0,0,{
                                    'product_id' : lines.product_id.id,
                                    'product_description' : lines.name,
                                    'name':lines.name,
                                    'product_uom_qty' : lines.product_qty,
                                    'order_id':lines.order_id.id,
                                    'product_uom' : lines.product_uom.id,
                                    # 'taxes_id' : ([(6,0,lines.product_id.supplier_taxes_id.ids)]),
                                    # 'date_planned' : str(datetime.now()),
                                    'price_unit' : lines.price_unit,
                                    'company_id' : lines.company_id.id,
                                    'price_cost':lines.price_unit,
                                    'rfqline_id':line.id,
                                    'hs_code':lines.product_id.hs_code
                                    }])
                else:
                    if line.state == 'draft':
                        raise Warning(_("RFQ is still in 'Draft'. Kindly update the response status for the RFQ '%s'!!")%(line.name)) 
                    if line.state == 'sent':
                        raise Warning(_("Kindly update the response status for the RFQ '%s'!!")%(line.name)) 
            internal_quote_id.create({
                        'lead_id' : self.id,
                        'state':'draft',
                        # self.company_id.id changed to => line.company_id.id
                        'company_id' :line.company_id.id,
                        'order_line':vals,
                        'partner_id':self.partner_id.id,
                        # 'due_date' : self.date_deadline,
                        'user_id' : self.assign_id.id      
                        })
        else:
            raise Warning(_("RFQ not found. Kindly convert the Enquiry to RFQ !!"))         

        return internal_quote_id
                        



    
    def _compute_sales_manager(self):
        #This method returns True if the currently logged in user has Sales Manager access group.
        for enq in self:
            enq.sales_manager = self.env.user.has_group('sales_team.group_sale_manager')

    
    @api.constrains('date_deadline')
    def _check_date_deadline(self):
        """
        Prevents the user to select past date
        """
        date_deadline = self.date_deadline
        date_today = fields.Date.context_today(self)
        if date_deadline < date_today:
            raise ValidationError(_('Expected Closing date cannot be past.'))

    
    @api.constrains('date_received')
    def _check_date_received(self):
        """
        Prevents the user to select future date
        """
        date_received = self.date_received
        date_today = fields.Date.context_today(self)
        if date_received > date_today:
            raise ValidationError(_('Received Date cannot be future.'))

    # Overridden to remove the stage "New" for PE users in kanban view
    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', stages.ids): add columns that should be present
        # - OR ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', '=', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        team_id = self._context.get('default_team_id')
        if team_id:
            search_domain = ['|', ('id', 'in', stages.ids), '|', ('team_id', '=', False), ('team_id', '=', team_id)]
        else:
            search_domain = ['|', ('id', 'in', stages.ids), ('team_id', '=', False)]
        PurchaseMgr = self.user_has_groups('purchase.group_purchase_manager')
        SalesGrp = self.user_has_groups('sales_team.group_sale_salesman')
        if not SalesGrp and not PurchaseMgr:
            search_domain += [('id', '!=', self.env.ref('crm.stage_lead1').id)]

        # perform search
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.model
    def _get_companies(self):
        selection = []
        companies = self.env['res.company'].search([])
        if companies:
            selection = [(company.code, company.name) for company in companies]
        selection += [('ALL', 'All Companies')]
        return selection

    @api.onchange('companies')
    def onchange_companies(self):
        if self.companies and self.companies != 'ALL':
            self.company_id = self.env['res.company'].search([('name', '=', self.companies)]).id
        else:
            self.company_id = False

    # @api.model
    # def default_get(self, fields):
    #     rec = super(Lead, self).default_get(fields)
    #     rec.update({
    #         'type': 'opportunity',
    #                })
    #     return rec
    #
    # #Overridden:
    # @api.v8
    # def _notification_get_recipient_groups(self, message, recipients):
    #     res = super(crm_lead, self)._notification_get_recipient_groups(message, recipients)
    #     res['group_sale_salesman'] = []
    #     return res


    
    def button_submit(self):
        """
            Confirm & Submit the Enquiry to Procurement Team
        """
        self.ensure_one()

        for case in self:
            vals = {'state': 'done'}
            if not case.partner_id:
                partner = case._create_lead_partner()
                if partner:
                    vals.update({'partner_id': partner.id})

            if not case.enquiry_lines:
                raise Warning(_("Please add a Product Details to proceed !!"))

            case.write(vals)
            case._send_mail_notify(action='submit')
        return True

    
    def button_assign(self):
        self.ensure_one()

        self._send_mail_notify(action='assign')

        StageID = self.env.ref('pantaq.pq_stage_lead2').read()
        StageID = StageID and StageID[0] or {}

        return self.write({'stage_id': StageID.get('id', False)})

    
    def button_cancel(self):
        self.ensure_one()

        self._send_mail_notify(action='cancel')

        StageID = self.env.ref('pantaq_old.pq_stage_lead9').read()
        StageID = StageID and StageID[0] or {}

        return self.write({'state':'cancel', 'stage_id': StageID.get('id', False)})

    
    def button_approve_cancel(self):
        self.ensure_one()

        self._send_mail_notify(action='approve_cancel')

        StageID = self.env.ref('pantaq_old.pq_stage_lead9').read()
        StageID = StageID and StageID[0] or {}

        return self.write({'state':'cancel', 'stage_id': StageID.get('id', False)})

    
    def button_draft(self):

        StageID = self.env.ref('crm.stage_lead1').read()
        StageID = StageID and StageID[0] or {}

        return self.write({'state':'draft', 'stage_id': StageID.get('id', False)})

    def accept_enquiry_transfer_request(self):
        self._send_mail_notify(action='accept_transfer')
        self.transferred_to = False# updates the transferred_to with False in enquiry, so this will make sure the enquiry transfer request has been accepted.
        self.assign_id = self._uid# assign to the PM accepted the transfer request.
        self._send_mail_notify(action='assign')
        return True

    def reject_enquiry_transfer_request(self):
        self._send_mail_notify(action='reject_transfer')
        self.transferred_to = False # so the enquiry won't be available for other PMs except the PM works on it.

        xml_id = 'action_crm_lead_submitted_to_purchase_team'
        result = self.env.ref('pantaq.%s' % (xml_id)).read()[0]
        return result

    
    def button_convert_rfq(self):
        context = dict(self._context)
        self.ensure_one()

        wizid = False
        wiz_obj = self.env['pq.wizard.rfq']
        wizln_obj = self.env['pq.wizard.rfqlines']

        lead_id = self.id

        vals = {'lead_id': lead_id}
        wizid = wiz_obj.create(vals)
        wizid = wizid.id

        self._cr.execute("delete from pq_wizard_rfqlines")

        for ln in self.enquiry_lines:
            lnvals = ln.copy_data()
            lnvals = lnvals and lnvals[0] or {}

            name = ln.name
            if ln.product_id:
                product = ln.product_id
                if product.description_purchase:
                    name += '\n' + product.description_purchase

            lnvals['name'] = name

            lnvals['enqln_id'] = ln.id
            lnvals['lead_id'] = lead_id
            lnvals['wiz_id'] = wizid
            # if lnvals['product_name'] or not lnvals['product_name']:
            #     del lnvals['product_name']

            wizln_obj.create(lnvals)

        xml_id = 'action_enq2rfq_form'
        result = self.env.ref('pantaq.%s' % (xml_id)).read()[0]
        domain = [('id', '=', wizid)]
        result['domain'] = domain
        return result

    
    def _send_mail_notify(self, action='submit'):
        self.ensure_one()

        if not self.team_id.member_ids:
            raise Warning(_("Please map users for the Sales Team [%s] !!"%self.team_id.name))

        proc_teams = self.env['crm.team'].sudo().search([('category', '=', 'procurement')])
        if not proc_teams:
            raise Warning(_("Please create some Procurement Team to be notified on submission of Enquiry."))

        # SalesPartners = list(map(lambda x: x.partner_id.id, self.team_id.member_ids))
        ProcPartners = list(map(lambda x: x.user_id.partner_id.id, proc_teams))
        NotifyPartners = []

        MsgBody = ''
        force_send = True

        if action == 'submit':
            # Notification of the submitted enquiry to Procurement Managers
            template = self.env.ref('pantaq.email_enquiry_submit')
            email_values = {'recipient_ids': [(4, pid) for pid in ProcPartners]}
            template.send_mail(self.id, force_send=force_send, email_values=email_values)

            # Acknowledgement of enquiry submission to Sales Executive/Sales Manager
            template = self.env.ref('pantaq.email_enquiry_submit_acknowledgement')
            email_values = {'recipient_ids': [(4, self.env.user.partner_id.id)]}
            template.send_mail(self.id, force_send=force_send, email_values=email_values)

            MsgBody = 'Enquiry has been Submitted.'
            NotifyPartners = list(ProcPartners)

        elif action == 'cancel' or action == 'approve_cancel':
            recipient_ids = []
            if action == 'cancel':
                recipient_ids = [(4, self.user_id.partner_id.id)]
                if self.user_id != self.user_id.sale_team_id.user_id: # If the enquiry is raised by SE, then his SM also will receive an email
                    recipient_ids += [(4, self.user_id.sale_team_id.user_id.partner_id.id)]
            else:
                # This block is called when PM approves cancellation request
                if self.notify_sales:
                    recipient_ids = [(4, self.cancellation_requested_by.partner_id.id)]
                    # if cancellation requested by SE, then his SM also gets notified
                    if self.cancellation_requested_by != self.cancellation_requested_by.sale_team_id.user_id:
                        recipient_ids += [(4, self.cancellation_requested_by.sale_team_id.user_id.partner_id.id)]
                if self.notify_procurement:
                    # if the enquiry is assigned to PE, then he is notified
                    if self.assign_id != self.assign_id.sale_team_id.user_id:
                        recipient_ids += [(4, self.assign_id.partner_id.id)]

            if recipient_ids:
                template = self.env.ref('pantaq_old.email_enquiry_cancelled')
                email_values = {'recipient_ids': recipient_ids}
                template.send_mail(self.id, force_send=force_send, email_values=email_values)

            MsgBody = 'Enquiry has been Cancelled.'
            NotifyPartners = [self.user_id.partner_id.id]

        elif action == 'request_cancel':
            template = self.env.ref('pantaq_old.email_enquiry_cancellation_request')
            email_values = {'recipient_ids': [(4, self.assign_id.sale_team_id.user_id.partner_id.id)]} # The Procurement team manager picked the enquiry will receive an email
            template.send_mail(self.id, force_send=force_send, email_values=email_values)

            MsgBody = 'Enquiry has been requested for Cancellation.'
            NotifyPartners = [self.assign_id.sale_team_id.user_id.partner_id.id]

        elif action == 'assign':
            template = self.env.ref('pantaq.email_enquiry_assigned')
            email_values = {'recipient_ids': [(4, self.assign_id.partner_id.id)]} # The Procurement team person assigned with the enquiry will receive an email
            template.send_mail(self.id, force_send=force_send, email_values=email_values)

            MsgBody = 'Enquiry has been Assigned.'
            NotifyPartners = [self.assign_id.partner_id.id]

        elif action == 'request_transfer':
            template = self.env.ref('pantaq_old.email_enquiry_transfer_request')
            email_values = {'recipient_ids': [(4, self.transferred_to.partner_id.id)]} # The other Procurement manager to whom the enquiry has been transferred will receive an email.
            template.send_mail(self.id, force_send=force_send, email_values=email_values)

            MsgBody = 'Enquiry has been requested to transfer.'
            NotifyPartners = [self.transferred_to.partner_id.id]

        elif action == 'accept_transfer':
            # Mail to PM requested for transfer
            template = self.env.ref('pantaq_old.email_enquiry_transfer_request_accepted')
            if self.assign_id.sale_team_id.user_id.partner_id.id:
                email_values = {'recipient_ids': [(4, self.assign_id.sale_team_id.user_id.partner_id.id)]}
                template.send_mail(self.id, force_send=force_send, email_values=email_values)
            else:
                raise Warning(_("Partner Email ID is not set! Try again, once set."))
            # Mail to PE already working on this enquiry (only if PE is assigned to this enquiry)
            if self.assign_id != self.assign_id.sale_team_id.user_id:
                template = self.env.ref('pantaq_old.email_enquiry_transferred')
                email_values = {'recipient_ids': [(4, self.assign_id.partner_id.id)]}
                template.send_mail(self.id, force_send=force_send, email_values=email_values)

            MsgBody = 'Enquiry transfer request has been accepted.'
            NotifyPartners = [self.assign_id.sale_team_id.user_id.partner_id.id]

        elif action == 'reject_transfer':
            # Mail to PM requested for transfer
            template = self.env.ref('pantaq_old.email_enquiry_transfer_request_rejected')
            email_values = {'recipient_ids': [(4, self.assign_id.sale_team_id.user_id.partner_id.id)]}
            template.send_mail(self.id, force_send=True, email_values=email_values)

            MsgBody = 'Enquiry transfer request has been rejected.'
            NotifyPartners = [self.assign_id.sale_team_id.user_id.partner_id.id]

        return self._notify_by_chat(MsgBody, NotifyPartners)


    
    def _notify_by_chat(self, message='', Partners=[]):
        return self.env['mail.message'].create({
            'model': self._name,
            'res_id': self.id or False,
            'body': message,
            'partner_ids': [(4, pid) for pid in Partners],
            # 'needaction_partner_ids': [(4, pid) for pid in Partners],
            'force_display': True,
        })

    @api.model
    def create(self, vals):

        if vals.get('enq_number', 'New') == 'New':
            vals['enq_number'] = self.env['ir.sequence'].next_by_code('crm.lead') or 'New'
            return super(Lead, self).create(vals)
        else:
            return
    
    def _check_Stages(self, vals):
        self.ensure_one()

        Stage = self.env['crm.stage'].browse(vals.get('stage_id', False))

        flag = False
        msg = "Enquiry cannot be marked as '%s'"%(Stage.name)

        if Stage.stage_type == 'rfq_sent' and self.rfq_count == 0:
            flag = True
            msg += ", without the creation of RFQs."

        elif Stage.stage_type == 'io_created' and self.intord1_count == 0:
            flag = True
            msg += ", without receiving any Quotation from Suppliers."

        elif Stage.stage_type == 'quote_sent' and self.sale_number == 0:
            flag = True
            msg += ", without creation of Customer Quotations."

        if flag:
            raise Warning(_(msg))

        return True

    # 
    # def write(self, vals):
    #     cr, context = self._cr, self._context
    #     sysCall = context.get('sysCall', False)
    #
    #     if 'stage_id' in vals and not sysCall:
    #         self._check_Stages(vals)
    #     return super(Lead, self).write(vals)

class EnquiryLines(models.Model):
    _name = 'pq.enquiry.lines'
    _description = 'Enquiry Lines'



    lead_id = fields.Many2one('crm.lead', string='Enquiry', required=True, ondelete='cascade', index=True, copy=False)
    name    = fields.Text(string='Description', required=True)

    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict')
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    product_uom_qty_total = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    product_name = fields.Char('Product Name')
    manufacturer_name = fields.Char('Manufacturer Name')
    product_description = fields.Text('Product Description')
    # procurement_ids = fields.One2many('procurement.order', 'enqline_id', string='Procurements')

    has_targetprice = fields.Boolean('I have Target Price')
    target_price    = fields.Float('Target Price', help="Enter Target Price for a unit.")
    currency_id     = fields.Many2one('res.currency', 'Currency', help="Select Currency for the Target Price",
                    default=lambda self: self.env.user.company_id.currency_id)
    partner_ids = fields.Many2many('res.partner', string='Suppliers', domain=[('is_company', '=', True)])


    
    @api.depends('product_uom', 'product_uom_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty_total = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty_total = line.product_uom_qty

    # 
    @api.onchange('product_id')
    def onchange_product(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        # domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        vals['product_uom'] = self.product_id.product_tmpl_id.uom_id

        product = self.product_id
        # With price then bring pricelist of product same as sale

        name = product.name_get()[0][1]

        if product.product_description:
            name += "\n" + product.product_description # Appends product's description

        if product.description_sale:
            name += '\n' + product.description_sale # Appends sale description

        vals['name'] = name
        vals['manufacturer_name'] = self.product_id.name
        vals['product_description'] = self.product_id.product_description

        self.update(vals)
        # return {'domain': domain}

class Team(models.Model):
    _inherit = ['crm.team']

    #Overridden
    user_id = fields.Many2one('res.users', string='Team Leader', required=True)
    #New
    category = fields.Selection([
        ('sales', 'Sales'),
        ('procurement', 'Procurement'),
        ], string='Team Category', required=True, copy=False, index=True, track_visibility='onchange', default='sales')