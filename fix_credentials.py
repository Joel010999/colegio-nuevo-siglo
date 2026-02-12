import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_ns.settings')
django.setup()

from django.contrib.auth import get_user_model
from portal.models import PerfilUsuario

User = get_user_model()
db_path = settings.DATABASES['default']['NAME']
print(f"Target Database: {db_path}")

username = "Colegio73152"
password = "73152Admin"

# Clean up any existing users with same name (case-insensitive)
existing = User.objects.filter(username__iexact=username)
print(f"Found {existing.count()} existing user(s) matching '{username}'.")
for u in existing:
    print(f"Deleting user ID {u.id} ({u.username})")
    u.delete()

print("Creating new superuser...")
# Create superuser cleanly
user = User.objects.create_user(username=username, email="admin@colegionuevosiglo.com", password=password)
user.is_active = True
user.is_staff = True
user.is_superuser = True
user.save()

print("Configuring profile...")
# Configure profile
if hasattr(user, 'perfil'):
    user.perfil.rol = 'admin'
    user.perfil.must_change_password = False
    user.perfil.save()
else:
    PerfilUsuario.objects.create(
        usuario=user, 
        rol='admin', 
        dni=99999999,
        must_change_password=False
    )

# Final Verification
user.refresh_from_db()
print("\n--- FINAL VERIFICATION ---")
print(f"Username: {user.username}")
is_valid = user.check_password(password)
print(f"Password '{password}' Valid: {is_valid}")
print(f"Is Active: {user.is_active}")
print(f"Is Superuser: {user.is_superuser}")
print(f"Profile Role: {user.perfil.rol}")

if is_valid and user.is_active:
    print("\nSUCCESS: User created and verified.")
else:
    print("\nFAILURE: Verification failed.")
