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
        'web',
    ],
    'data': [
        'views/report_layout.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': False
}
