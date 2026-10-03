from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
import re

class Command(BaseCommand):
    help = 'Inspect rendered admin dashboard sidebar'

    def handle(self, *args, **options):
        # Allow testserver host
        settings.ALLOWED_HOSTS = getattr(settings, 'ALLOWED_HOSTS', []) + ['testserver','localhost','127.0.0.1']
        User = get_user_model()
        superuser = User.objects.filter(is_superuser=True).first()
        self.stdout.write('superuser: %s' % bool(superuser))
        c = Client()
        if superuser:
            c.force_login(superuser)
        r = c.get('/admin-dashboard/', HTTP_HOST='testserver')
        self.stdout.write('status: %s' % r.status_code)
        text = r.content.decode('utf-8', errors='replace')
        m = re.search(r'<aside[^>]*id=["\']dashboard-sidebar["\'][^>]*>', text)
        self.stdout.write('dashboard-sidebar-tag: %s' % (m.group(0) if m else None))
        self.stdout.write('data-mobile-open in HTML count: %s' % text.count('data-mobile-open'))
        if m:
            idx = text.find(m.group(0))
            snippet = text[idx:idx+800]
            self.stdout.write('snippet after tag:\n%s' % snippet)
        else:
            self.stdout.write('sidebar not found in rendered HTML')
