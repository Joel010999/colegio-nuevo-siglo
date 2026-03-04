"""
nuke_db.py — Hard reset de la base de datos.
Borra todos los Alumnos (cascada: deudas, pagos) y usuarios no-admin.
Preserva superusers y staff (el admin).
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_ns.settings')
django.setup()

from django.contrib.auth.models import User
from portal.models import Alumno, RegistroDeuda, ConceptoDeuda, Pago, PerfilUsuario

print("=" * 50)
print("HARD RESET - Base de Datos")
print("=" * 50)

# Conteo previo
print(f"\n--- ANTES ---")
print(f"Alumnos:        {Alumno.objects.count()}")
print(f"Deudas:         {RegistroDeuda.objects.count()}")
print(f"Pagos:          {Pago.objects.count()}")
print(f"Conceptos:      {ConceptoDeuda.objects.count()}")
print(f"Usuarios total: {User.objects.count()}")
print(f"Perfiles:       {PerfilUsuario.objects.count()}")

# 1. Borrar todos los alumnos (cascada: deudas y pagos)
deleted_alumnos = Alumno.objects.all().delete()
print(f"\n>>> Alumnos eliminados (cascada): {deleted_alumnos}")

# 2. Borrar usuarios no-admin (y sus perfiles en cascada)
deleted_users = User.objects.filter(is_superuser=False, is_staff=False).delete()
print(f">>> Usuarios no-admin eliminados: {deleted_users}")

# Conteo posterior
print(f"\n--- DESPUES ---")
print(f"Alumnos:        {Alumno.objects.count()}")
print(f"Deudas:         {RegistroDeuda.objects.count()}")
print(f"Pagos:          {Pago.objects.count()}")
print(f"Conceptos:      {ConceptoDeuda.objects.count()}")
print(f"Usuarios total: {User.objects.count()}")
print(f"Perfiles:       {PerfilUsuario.objects.count()}")

# Verificar admin vivo
admins = User.objects.filter(is_superuser=True)
print(f"\n--- ADMIN VIVO ---")
for a in admins:
    print(f"  ✓ {a.username} (superuser={a.is_superuser}, staff={a.is_staff})")

print(f"\n{'=' * 50}")
print("HARD RESET COMPLETADO")
print(f"{'=' * 50}")
