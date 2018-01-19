**gitmanager** can checkout course repositories and update them.
It provides a hook URL, that can be configured in remote git repository,
for automatic updates when push to the selected branch is made.

This module is by default disabled and may be activated in `local_settings.py`
`ADD_APPS = ['gitmanager']`

The cron script expects directories and programs to be exactly as
presented in the installation instructions.
