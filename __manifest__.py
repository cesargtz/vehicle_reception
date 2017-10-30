# -*- coding: utf-8 -*-

{
    'name': 'Recepción de Vehiculos',
    'version': '10.0',
    'author': 'QX UNIT DE MÉXICO SA DE CV',
    'website': 'http://www.qxunit.com.mx',
    'depends': ['purchase_contract_type', 'vehicle', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/vehicle_reception.xml',
    ]
}
