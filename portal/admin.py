from django.contrib import admin
from .models import Alumno, ConceptoDeuda, RegistroDeuda


class RegistroDeudaInline(admin.TabularInline):
    model = RegistroDeuda
    extra = 0
    readonly_fields = ['concepto', 'monto', 'estado']
    can_delete = False


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ['documento', 'apellido', 'nombres', 'curso_completo', 'saldo_moroso']
    list_filter = ['nivel', 'curso', 'division']
    search_fields = ['documento', 'apellido', 'nombres', 'padre_dni', 'madre_dni', 'tutor_dni']
    readonly_fields = ['saldo_moroso']
    inlines = [RegistroDeudaInline]
    
    fieldsets = (
        ('Datos del Alumno', {
            'fields': ('documento', 'apellido', 'nombres', 'fecha_nacimiento', 'sexo')
        }),
        ('Escolaridad', {
            'fields': ('nivel', 'curso', 'division')
        }),
        ('Contacto Alumno', {
            'fields': ('direccion', 'telefono1', 'telefono2', 'email', 'barrio'),
            'classes': ('collapse',)
        }),
        ('Padre', {
            'fields': ('padre_nombre', 'padre_dni', 'padre_direccion', 'padre_telefono1', 'padre_email'),
            'classes': ('collapse',)
        }),
        ('Madre', {
            'fields': ('madre_nombre', 'madre_dni', 'madre_direccion', 'madre_telefono1', 'madre_email'),
            'classes': ('collapse',)
        }),
        ('Tutor', {
            'fields': ('tutor_nombre', 'tutor_dni', 'tutor_direccion', 'tutor_telefono1', 'tutor_email'),
            'classes': ('collapse',)
        }),
        ('Estado de Cuenta', {
            'fields': ('saldo_moroso', 'recargo', 'familia')
        }),
    )


@admin.register(ConceptoDeuda)
class ConceptoDeudaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'orden']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'codigo']


@admin.register(RegistroDeuda)
class RegistroDeudaAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'concepto', 'monto', 'estado', 'fecha_pago']
    list_filter = ['estado', 'concepto']
    search_fields = ['alumno__apellido', 'alumno__nombres', 'alumno__documento']
    raw_id_fields = ['alumno']
