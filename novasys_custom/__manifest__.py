{
    'name': 'NOVASYS Customisations',
    'version': '11.0.1.0.0',
    'category': 'Custom',
    'license': 'AGPL-3',
    'author': 'SystemWorks.',
    'website': 'http://www.systemworks.co.za',
    'summary': 'Customisations for NOVASYS',
    'depends': [
        'base',
        'product',
        'purchase',
        'sale',
        'stock',
        'web',
    ],
    'data': [
        'views/product_template_views.xml',
        'views/report_layout.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': False
}
