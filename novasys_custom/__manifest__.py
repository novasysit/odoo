# See LICENSE file for full copyright and licensing details.

{
    'name': 'NOVASYS Customisations',
    'version': '12.0.1.0.0',
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
        'views/res_partner_view.xml',
        'views/web_layout.xml',
    ],
    'installable': True,
    'auto_install': False
}
