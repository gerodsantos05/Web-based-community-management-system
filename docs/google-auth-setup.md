# Restoring Google sign-in

This project uses Django Allauth for Google sign-in, not Firebase Authentication.
The `DoesNotExist` error at `/accounts/google/login/` occurs when Django's
`SITE_ID` does not point to the site associated with the Google `SocialApp`.

The production database has the Google `SocialApp` attached to Site ID `2`
(`happynessproject.pythonanywhere.com`), while Site ID `1` is `example.com`.
Keep the local development default at `1`; set the production site ID in the
PythonAnywhere WSGI configuration, before `get_wsgi_application()`:

```python
import os

os.environ["SITE_ID"] = "2"
```

Save the WSGI file, reload the PythonAnywhere web app, and test:

```text
https://happynessproject.pythonanywhere.com/accounts/google/login/
```

The production database already contains the Google OAuth client and associates
it with Site ID `2`. Do not add a second Google `SocialApp` or replace OAuth
credentials as part of this fix. The Google OAuth client's authorized redirect
URI is already configured as:

```text
https://happynessproject.pythonanywhere.com/accounts/google/login/callback/
```
