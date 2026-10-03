from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver','localhost','127.0.0.1']
from django.contrib.auth import get_user_model
User = get_user_model()
superuser = User.objects.filter(is_superuser=True).first()
print('superuser', bool(superuser))
from django.test import Client
c = Client()
if superuser:
    c.force_login(superuser)
r = c.get('/admin-dashboard/', HTTP_HOST='testserver')
print('status', r.status_code)
text = r.content.decode('utf-8', errors='replace')
import re
m = re.search(r'<aside[^>]*id=["\']dashboard-sidebar["\'][^>]*>', text)
print('dashboard-sidebar-tag:', m.group(0) if m else None)
print('data-mobile-open in HTML count:', text.count('data-mobile-open'))
if m:
    idx = text.find(m.group(0))
    print('snippet after tag:\n', text[idx:idx+800])
else:
    print('sidebar not found in rendered HTML')
