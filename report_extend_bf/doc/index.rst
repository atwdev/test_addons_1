
Install module in S.O. based Linux
----------------------------------

- Red Hat
- Debian
- Fedora
- Mandriva
- Ubuntu
- OpenSUSE
- Others linux distro.

Pre-Installation Requirements
------------------------------------

**Unoconv**: Convert files to any format that supports LibreOffice. Website: `Unoconv <http://dag.wiee.rs/home-made/unoconv/>`_ example install ubuntu O.S. 


	sudo apt-get install unoconv

**Install py3o.template with python 3 support**

**py3o.template**: An easy solution to design reports using LibreOffice, for basic templating (odt->odt and ods->ods only) 

	pip3 install py3o.template

Supported output format combinations (Template -> Output):

- odt -> odt (default)
- odt -> pdf
- odt -> doc
- odt -> docx
- odt -> pds
- rtf -> rtf


Install Google Fonts And Others Fonts - Example
----------------------------------------------------------

**Download desired fonts**

https://fonts.google.com/?selection.family=Open+Sans

**Install Google Fonts on Ubuntu**

	cd /usr/share/fonts

	sudo mkdir googlefonts

	cd googlefonts

	wget -O Open_Sans.zip https://fonts.google.com/download?family=Open%20Sans

	sudo unzip Open_Sans.zip

	sudo chmod -R --reference=/usr/share/fonts/opentype /usr/share/fonts/googlefonts

**Register fonts**

	sudo fc-cache -fv

**Check if font installed**

Example search OpenSans name file OpenSans-VariableFont_wdth,wght.ttf 

	sudo fc-match OpenSans

**Restart Service Odoo**

	sudo systemctl restart odoo.service

**Ref.**

https://gist.github.com/lightonphiri/5811226a1fba0b3df3be73ff2d5b351c#file-bash-install_google_fonts_on_ubuntu-md


Note
----
If the program unoconv default output will show in ODT format regardless of the output field you selected in the report is not installed.

- Fully Supports Odoo Version 15.0 Community

