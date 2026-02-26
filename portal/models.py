from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class ConceptoDeuda(models.Model):
    """
    Traduce códigos de concepto a nombres legibles.
    Ejemplo: código="0" -> nombre="Matrícula"
    """
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    orden = models.IntegerField(default=0, help_text="Orden para mostrar en la vista")

    class Meta:
        ordering = ['orden', 'codigo']
        verbose_name = "Concepto de Deuda"
        verbose_name_plural = "Conceptos de Deuda"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Alumno(models.Model):
    """
    Modelo principal de alumnos.
    Almacena datos del alumno y de sus responsables (padre, madre, tutor).
    """
    # Datos del alumno
    documento = models.BigIntegerField(primary_key=True, verbose_name="DNI Alumno")
    apellido = models.CharField(max_length=100)
    nombres = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, blank=True)
    nivel = models.CharField(max_length=10, blank=True, verbose_name="Nivel (I5/P/S)")
    curso = models.CharField(max_length=10, blank=True)
    division = models.CharField(max_length=10, blank=True)
    
    # Dirección y contacto del alumno
    direccion = models.CharField(max_length=200, blank=True)
    telefono1 = models.CharField(max_length=50, blank=True)
    telefono2 = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    barrio = models.CharField(max_length=100, blank=True)
    
    # Datos del Padre
    padre_nombre = models.CharField(max_length=150, blank=True, verbose_name="Nombre del Padre")
    padre_dni = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="DNI Padre")
    padre_direccion = models.CharField(max_length=200, blank=True)
    padre_telefono1 = models.CharField(max_length=50, blank=True)
    padre_telefono2 = models.CharField(max_length=50, blank=True)
    padre_email = models.EmailField(blank=True)
    
    # Datos de la Madre
    madre_nombre = models.CharField(max_length=150, blank=True, verbose_name="Nombre de la Madre")
    madre_dni = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="DNI Madre")
    madre_direccion = models.CharField(max_length=200, blank=True)
    madre_telefono1 = models.CharField(max_length=50, blank=True)
    madre_telefono2 = models.CharField(max_length=50, blank=True)
    madre_email = models.EmailField(blank=True)
    
    # Datos del Tutor
    tutor_nombre = models.CharField(max_length=150, blank=True, verbose_name="Nombre del Tutor")
    tutor_dni = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="DNI Tutor")
    tutor_direccion = models.CharField(max_length=200, blank=True)
    tutor_telefono1 = models.CharField(max_length=50, blank=True)
    tutor_telefono2 = models.CharField(max_length=50, blank=True)
    tutor_email = models.EmailField(blank=True)
    
    # Otros
    familia = models.IntegerField(default=0, help_text="ID de grupo familiar")
    recargo = models.BooleanField(default=False)
    saldo_moroso = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                                        verbose_name="Saldo Total Adeudado")

    class Meta:
        ordering = ['apellido', 'nombres']
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"

    def __str__(self):
        return f"{self.apellido}, {self.nombres} (DNI: {self.documento})"
    
    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombres}"
    
    @property
    def curso_completo(self):
        """Devuelve curso formateado, ej: 'P-3°A' o 'S-4°B'"""
        if self.nivel and self.curso and self.division:
            return f"{self.nivel}-{self.curso}°{self.division}"
        elif self.curso and self.division:
            return f"{self.curso}°{self.division}"
        return self.curso or ""


class RegistroDeuda(models.Model):
    """
    Registro individual de deuda.
    Un alumno puede tener múltiples deudas (cuotas, matrícula, materiales, etc.)
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('comprobante_enviado', 'Comprobante Enviado'),
        ('pago_verificado', 'Pago Verificado'),
        ('pagado', 'Pagado'),
        ('parcial', 'Pago Parcial'),
        ('no_corresponde', 'No Corresponde'),
    ]
    
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='deudas')
    concepto = models.ForeignKey(ConceptoDeuda, on_delete=models.PROTECT, related_name='registros')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    periodo = models.CharField(max_length=20, blank=True, help_text="Ej: 2024-03")
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_pago = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['concepto__orden', 'concepto__codigo']
        verbose_name = "Registro de Deuda"
        verbose_name_plural = "Registros de Deuda"

    def __str__(self):
        return f"{self.alumno.apellido} - {self.concepto.nombre}: ${self.monto}"
    
    @property
    def esta_pendiente(self):
        return self.estado in ['pendiente', 'comprobante_enviado']


# ==================== NUEVOS MODELOS ====================

class PerfilUsuario(models.Model):
    """
    Extiende el modelo User de Django con campos específicos del sistema.
    """
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('padre', 'Padre/Responsable'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    dni = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="DNI")
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='padre')
    must_change_password = models.BooleanField(default=True, verbose_name="Debe cambiar contraseña")
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"{self.usuario.username} ({self.get_rol_display()})"
    
    @property
    def es_admin(self):
        return self.rol == 'admin'


class Pago(models.Model):
    """
    Registro de pagos con comprobantes.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Verificación'),
        ('verificado', 'Pago Verificado'),
        ('rechazado', 'Rechazado'),
    ]
    
    def comprobante_path(instance, filename):
        ext = filename.split('.')[-1]
        return f'comprobantes/{instance.numero_operacion}.{ext}'
    
    numero_operacion = models.CharField(max_length=50, unique=True, editable=False)
    deuda = models.ForeignKey(RegistroDeuda, on_delete=models.CASCADE, related_name='pagos')
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2)
    comprobante = models.ImageField(upload_to='comprobantes/', blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    # Fechas
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    
    # Usuario que envió el pago
    usuario_responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pagos_enviados')
    usuario_verificador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_verificados')
    
    observaciones = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha_envio']
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
    
    def save(self, *args, **kwargs):
        if not self.numero_operacion:
            now = timezone.now()
            self.numero_operacion = f"OP-{now.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_operacion} - ${self.monto_pagado}"
    
    def verificar(self, usuario):
        """Marca el pago como verificado y actualiza la deuda asociada."""
        self.estado = 'verificado'
        self.fecha_verificacion = timezone.now()
        self.usuario_verificador = usuario
        self.save()
        
        # Actualizar estado de la deuda
        self.deuda.estado = 'pago_verificado'
        self.deuda.fecha_pago = timezone.now().date()
        self.deuda.save()


class ConfiguracionSistema(models.Model):
    """
    Configuración global del sistema (singleton).
    """
    alias_transferencia = models.CharField(max_length=100, default='colegio.nuevosiglo')
    cbu = models.CharField(max_length=22, default='0000000000000000000000')
    password_default = models.CharField(max_length=50, default='Colegio123')
    
    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuración del Sistema"
    
    def save(self, *args, **kwargs):
        # Singleton pattern - solo puede haber un registro
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config
    
    def __str__(self):
        return "Configuración del Sistema"


class RegistroAuditoria(models.Model):
    """
    Log de auditoría para rastrear acciones importantes.
    """
    ACCION_CHOICES = [
        ('LOGIN', 'Inicio de Sesión'),
        ('LOGOUT', 'Cierre de Sesión'),
        ('PASSWORD_CHANGED', 'Cambio de Contraseña'),
        ('PAYMENT_SUBMITTED', 'Pago Enviado'),
        ('PAYMENT_VERIFIED', 'Pago Verificado'),
        ('IMPORT', 'Importación de Datos'),
        ('EXPORT', 'Exportación de Datos'),
        ('CONFIG_UPDATE', 'Actualización de Configuración'),
        ('USER_CREATED', 'Usuario Creado'),
        ('PASSWORD_RESET', 'Contraseña Reseteada'),
        ('EMAIL_SENT', 'Email Enviado'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50, choices=ACCION_CHOICES)
    detalles = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
    
    def __str__(self):
        return f"{self.timestamp} - {self.get_accion_display()} - {self.usuario}"
    
    @classmethod
    def log(cls, usuario, accion, detalles='', request=None):
        ip = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
        
        return cls.objects.create(
            usuario=usuario,
            accion=accion,
            detalles=detalles,
            ip_address=ip
        )
