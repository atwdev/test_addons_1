{
    "name": "Instalatur Hebat Base",
    "version": "1.0",
    "summary": "Instalatur Hebat Base",
    "author": "Instalatur Hebat",
    "depends": ["contacts", "sale_management", "purchase", "project"],
    "data": [
        'security/ir.model.access.csv',

        'data/dashboard_data.xml',

        'views/dashboard.xml',
        'views/purchase_order.xml',
        'views/res_partner.xml',
    ],
    "installable": True,
}
