import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_ns.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

u = User.objects.filter(username='2222').first()
if u:
    u.set_password('Colegio123')
    u.save()
    
    # Also ensure must_change_password is true since it's their first login
    if hasattr(u, 'perfil'):
        u.perfil.must_change_password = True
        u.perfil.save()
    
    print("Contraseña reseteada con éxito a 'Colegio123'")
else:
    print("Usuario no encontrado")
