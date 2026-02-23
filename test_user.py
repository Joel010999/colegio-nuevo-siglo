import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_ns.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

u = User.objects.filter(username='2222').first()
if u:
    print(f"User {u.username} found.")
    print(f"Check password 'Colegio123': {u.check_password('Colegio123')}")
    print(f"Is active: {u.is_active}")
    print(f"Has profile: {hasattr(u, 'perfil')}")
    if hasattr(u, 'perfil'):
        print(f"Must change password: {u.perfil.must_change_password}")
else:
    print("User 2222 not found.")
