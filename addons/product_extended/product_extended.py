##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenERP S.A. (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from openerp.osv import fields
from openerp.osv import osv


class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'


    def compute_price(self, cr, uid, ids, recursive=False, test=False, real_time_accounting = False, context=None):
        '''
        Will return test dict when the test = False
        Multiple ids at once?
        testdict is used to inform the user about the changes to be made
        '''
        testdict = {}
        for prod_id in ids:
            bom_obj = self.pool.get('mrp.bom')
            bom_ids = bom_obj.search(cr, uid, [('bom_id', '=', False), ('product_id','=', prod_id), ('bom_lines', '!=', False)], context=context)
            if bom_ids:
                bom_id = bom_ids[0]
                # In recursive mode, it will first compute the prices of child boms
                if recursive:
                    #Search the products that are components of this bom of prod_id
                    boms = bom_obj.search(cr, uid, [('bom_id', '=', bom_id)], context=context)
                    #Call compute_price on these subproducts
                    prod_set = set([x.product_id.id for x in bom_obj.browse(cr, uid, boms, context=context)])
                    res = self.compute_price(cr, uid, list(prod_set), recursive=recursive, test=test, real_time_accounting = real_time_accounting, context=context)
                    if test: 
                        testdict.update(res)
                #Use calc price to calculate and put the price on the product of the BoM if necessary
                price = self._calc_price(cr, uid, bom_obj.browse(cr, uid, bom_id, context=context), test=test, real_time_accounting = real_time_accounting, context=context)
                if test:
                    testdict.update({prod_id : price})
        if test:
            return testdict
        else:
            return True


    def _calc_price(self, cr, uid, bom, test = False, real_time_accounting=False, context=None):
        if context is None:
            context={}
        price = 0
        uom_obj = self.pool.get("product.uom")
        if bom.bom_lines:
            for sbom in bom.bom_lines:
                my_qty = sbom.bom_lines and 1.0 or sbom.product_qty
                price += uom_obj._compute_price(cr, uid, sbom.product_id.uom_id.id, sbom.product_id.standard_price, sbom.product_uom.id) * my_qty

        if bom.routing_id:
            for wline in bom.routing_id.workcenter_lines:
                wc = wline.workcenter_id
                cycle = wline.cycle_nbr
                hour = (wc.time_start + wc.time_stop + cycle * wc.time_cycle) *  (wc.time_efficiency or 1.0)
                price += wc.costs_cycle * cycle + wc.costs_hour * hour
                price = self.pool.get('product.uom')._compute_price(cr,uid,bom.product_uom.id, price, bom.product_id.uom_id.id)
        
        #Convert on product UoM quantities
        if price > 0:
            price = uom_obj._compute_price(cr, uid, bom.product_uom.id, price / bom.product_qty, bom.product_id.uom_id.id)
            product = self.pool.get("product.product").browse(cr, uid, bom.product_id.id, context=context)
        if not test:
            if (product.valuation != "real_time" or not real_time_accounting):
                self.write(cr, uid, [bom.product_id.id], {'standard_price' : price}, context=context)
            else:
                #Call wizard function here
                wizard_obj = self.pool.get("stock.change.standard.price")
                ctx = context.copy()
                ctx.update({'active_id': bom.product_id.id})
                wiz_id = wizard_obj.create(cr, uid, {'new_price': price}, context=ctx)
                wizard_obj.change_price(cr, uid, [wiz_id], context=ctx)
        return price

product_product()

class product_bom(osv.osv):
    _inherit = 'mrp.bom'
            
    _columns = {
        'standard_price': fields.related('product_id','standard_price',type="float",relation="product.product",string="Standard Price",store=False)
    }

product_bom()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

