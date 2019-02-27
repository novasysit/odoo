{
    "name": "Standard Customer Statement Odoo 11",
    "version": "1.0",
    "depends": ["base", "account", "web", "account_reports_followup"],
    "author": "SystemWorks",
    "category": "Accounting",
    "description": "Customer statement.",
    "data": [
             'wizards/statement.xml',
             'views/partner_view.xml',
             'views/report_overdue.xml'
            ],
    "test": [],
    "installable": True,
    "active": False
}
