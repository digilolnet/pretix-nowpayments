NOWPayments
==========================

This is a plugin for `pretix`_.

NOWPayments payment plugin.

Development setup
-----------------

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository.

3. Activate the virtual environment you use for pretix development.

4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.

To check code style rules, you need these packages installed::

    pip install flake8 isort black docformatter

To check your plugin for rule violations, run::

    docformatter --check -r .
    black --check .
    isort -c .
    flake8 .

You can auto-fix some of these issues by running::

    docformatter -r .
    isort .
    black .

To automatically check for these issues before you commit, you can run ``.install-hooks``.


License
-------


Copyright 2023 İrem Kuyucu at `Digilol`_.

Released under the terms of the GNU Affero General Public License version 3.

Would you like to have a custom Pretix plugin? Reach us at `Digilol`_.

.. _Digilol: https://digilol.net
.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
