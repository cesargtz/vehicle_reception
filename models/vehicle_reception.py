# -*- coding: utf-8 -*-

from odoo import api, fields, models


class VehicleReception(models.AbstractModel):
    _name = 'vehicle.reception'

    contract_id = fields.Many2one('purchase.order', 'Contrato')
    auxiliary_contract = fields.Many2one('purchase.order', 'Contrato auxiliar', related="contract_id.auxiliary_contract")
    #contract_type = fields.Selection(readonly=True, related="contract_id.contract_type")
    partner_id = fields.Many2one('res.partner', 'Vendedor', readonly=True, related="contract_id.partner_id")
    street2 = fields.Char('Dirección', readonly=True, related='partner_id.street2')
    contract_state = fields.Selection('Estatus de Contrato', readonly=True, related="contract_id.state")
    active = fields.Boolean(default=True, string="Activo")

    hired = fields.Float('Contratado', compute="_compute_hired", readonly=True, store=False)
    delivered = fields.Float('Entregado', compute="_compute_delivered", readonly=True, store=False)
    pending = fields.Float('Pendiente', compute="_compute_pending", readonly=True, store=False)

    product_id = fields.Many2one('product.product', 'Producto', compute="_compute_product_id", readonly=True, store=False)
    location_id = fields.Many2one('stock.location', 'Ubicación')

    damaged_location = fields.Many2one('stock.location', 'Ubicación Dañado')

    owner_id = fields.Many2one('res.partner', 'Propietario',  help="Propietario", readonly=True, states={'analysis': [('readonly', False)]})

    contract_type = fields.Selection([
        ('axc', 'Spot'),
        ('pf', 'Precio Fijo'),
        ('pm', 'Precio Minimo'),
        ('pd', 'Precio Despues'),
        ('pb', 'Precio Base'),
        ('surplus', 'Excedente'),
        ('na', 'No aplica'),
    ], 'Tipo de contrato', readonly=True, compute="_compute_contract_type", store=True)


    @api.one
    @api.depends('contract_id')
    def _compute_contract_type(self):
        self.contract_type = self.contract_id.contract_type

    @api.one
    @api.depends('contract_id')
    def _compute_hired(self):
        self.hired = sum(line.product_qty for line in self.contract_id.order_line)

    @api.one
    @api.depends('contract_id')
    def _compute_delivered(self):
        self.delivered = 0

    @api.one
    @api.depends('contract_id')
    def _compute_pending(self):
        self.pending = self.hired - self.delivered

    @api.one
    @api.depends('contract_id')
    def _compute_product_id(self):
        product_id = False
        for line in self.contract_id.order_line:
            product_id = line.product_id
            break
        self.product_id = product_id

    @api.multi
    def fun_transfer(self):
        #if self.contract_id.shipped:
        #    return
        self.stock_picking_id = self.env['stock.picking'].search([('origin', '=', self.contract_id.name), ('state', '=', 'assigned')], order='date', limit=1)
        if self.stock_picking_id:
            picking = [self.stock_picking_id.id]
            pending_ma = 1000*sum(move.product_uom_qty for move in self.stock_picking_id.move_lines)
	    for move in self.stock_picking_id.move_lines:
                move.location_dest_id = self.location_id
            # if pending_ma >= self.clean_kilos:
                self._do_enter_transfer_details(picking, self.stock_picking_id, self.clean_kilos, self.location_id)
            # else:
            #     self._do_enter_transfer_details(picking, self.stock_picking_id, pending_ma, self.location_id)
            #     self.contract_id.auxiliary_contract = self.env['purchase.order'].create({'partner_id': self.contract_id.partner_id.id,
            #                                                                              'picking_type_id': self.contract_id.picking_type_id.id,
            #                                                                              #'pricelist_id': self.contract_id.pricelist_id.id
            #                                                                              })
            #     self.contract_id.auxiliary_contract.contract_type = 'surplus'
            #     self.contract_id.auxiliary_contract.order_line = self.env['purchase.order.line'].create({
            #         'order_id': self.auxiliary_contract.id,
            #         'product_id': self.contract_id.order_line[0].product_id.id,
            #         'name': self.contract_id.order_line[0].name,
            #         'date_planned': self.contract_id.order_line[0].date_planned,
            #         'company_id': self.contract_id.order_line[0].company_id.id,
            #         'product_qty': (self.clean_kilos - pending_ma)/1000,
            #         'price_unit': self.contract_id.order_line[0].price_unit,
            #         'product_uom': self.contract_id.order_line[0].product_uom.id,
            #     })

    @api.multi
    def fun_ship(self):
        stock_picking_id_cancel = self.env['stock.picking'].search([('origin', '=', self.contract_id.name), ('state', '=', 'assigned')], order='date', limit=1)
        if stock_picking_id_cancel:
            stock_picking_id_cancel.action_cancel()

    @api.multi
    def _do_enter_transfer_details(self, picking_id, picking, clean_kilos, location_id):
        context = dict(self._context or {})
        context.update({
            'active_model': self._name,
            'active_ids': picking_id,
            'active_id': len(picking_id) and picking_id[0] or False
        })
        created_id = self.env['stock.backorder.confirmation'].with_context(context).create({'picking_id': len(picking_id) and picking_id[0] or False})
        if self.owner_id.id:
            picking.write({'owner_id': self.owner_id.id})
            picking.action_assign_owner()
        if not picking.pack_operation_product_ids:
            picking.do_prepare_partial()
        for op in picking.pack_operation_product_ids:
            op.write({'qty_done':clean_kilos/1000, "location_dest_id": self.location_id.id})
        created_id.process()
