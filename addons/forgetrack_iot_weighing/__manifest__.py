{
    'name': 'ForgeTrack IoT Weighing',
    'version': '20.0.1.0.0',
    'category': 'Inventory/IoT',
    'summary': 'Integrasi Timbangan IoT Dengan Odoo',
    'author': 'Reza Aziz Simatupang',
    'depends': [
        'base',
        'purchase',
        'stock',
        'mrp',
        'account',
    ],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
