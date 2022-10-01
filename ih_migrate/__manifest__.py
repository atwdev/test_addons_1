# -*- coding: utf-8 -*-

{
    'name': 'Instalatur Hebat Migrate',
    'summary': 'Instalatur Hebat Migrate',
    'version': '1.0',
    'author': 'Chairiman',
    'license': 'GPL-3',
    'depends': ['ih_base', 'l10n_id'],
    'data': [
        'security/ir.model.access.csv',

        'data/company_data.xml',
        'data/partner_data.xml',
        'data/product_data.xml',

        'wizard/ih_import_wizard_views.xml',
    ],
    'installable': True,

}
