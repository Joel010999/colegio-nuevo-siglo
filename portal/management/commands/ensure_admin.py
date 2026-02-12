import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from portal.models import PerfilUsuario

class Command(BaseCommand):
    help = 'Ensures the admin user Colegio73152 exists with correct credentials'

    def handle(self, *args, **options):
        User = get_user_model()
        username = "Colegio73152"
        password = "73152Admin"
        email = "admin@colegionuevosiglo.com"

        self.stdout.write(f"Checking admin user {username}...")

        try:
            user, created = User.objects.get_or_create(username=username, defaults={'email': email})
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"User {username} created."))
            else:
                self.stdout.write(f"User {username} already exists.")

            # Always ensure credentials and permissions
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write("Password and permissions updated.")

            # Ensure profile
            if hasattr(user, 'perfil'):
                user.perfil.rol = 'admin'
                user.perfil.must_change_password = False
                user.perfil.save()
                self.stdout.write("Existing profile updated.")
            else:
                PerfilUsuario.objects.create(
                    usuario=user, 
                    rol='admin', 
                    dni=99999999,
                    must_change_password=False
                )
                self.stdout.write(self.style.SUCCESS("New admin profile created."))
            
            self.stdout.write(self.style.SUCCESS(f"Successfully ensured admin user {username}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error ensuring admin user: {e}"))
