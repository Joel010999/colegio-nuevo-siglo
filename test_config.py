import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_ns.settings')
django.setup()

from portal.models import ConfiguracionSistema
config = ConfiguracionSistema.get_config()
print(f"Default Password in DB: {config.password_default}")
