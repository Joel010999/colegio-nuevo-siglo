import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_ns.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

username = "Colegio73152"
password = "73152Admin"

print(f"Checking user: {username}")

try:
    user = User.objects.get(username=username)
    print(f"User exists: Yes")
    print(f"Is active: {user.is_active}")
    print(f"Check password result: {user.check_password(password)}")
    
    auth_user = authenticate(username=username, password=password)
    print(f"Authenticate result: {auth_user}")
    
    if hasattr(user, 'perfil'):
        print(f"Perfil role: {user.perfil.rol}")
    else:
        print("No profile found")

except User.DoesNotExist:
    print("User does not exist")
except Exception as e:
    print(f"Error: {e}")
