from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Autenticación
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('primer-login/', views.primer_login_view, name='primer_login'),
    
    # Portal Padres
    path('portal/', views.portal_padre, name='portal_padre'),
    path('portal/pagar/<int:deuda_id>/', views.enviar_comprobante, name='enviar_comprobante'),
    path('portal/recibo/<int:pago_id>/', views.ver_recibo, name='ver_recibo'),
    
    # Consulta pública (sin login)
    path('consulta/', views.consulta_publica, name='consulta_publica'),
    
    # Panel Administrativo
    path('admin-panel/', views.admin_deudas, name='admin_dashboard'),
    path('admin-panel/cobro/', views.admin_cobro, name='admin_cobro'),
    path('admin-panel/deudas/', views.admin_deudas, name='admin_deudas'),
    path('admin-panel/pagos/', views.admin_pagos, name='admin_pagos'),
    path('admin-panel/verificar/<int:pago_id>/', views.admin_verificar_pago, name='admin_verificar_pago'),
    path('admin-panel/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin-panel/usuarios/crear/', views.admin_crear_alumno, name='admin_crear_alumno'),
    path('admin-panel/reset-password/<int:usuario_id>/', views.admin_reset_password, name='admin_reset_password'),
    path('admin-panel/forzar-cambio-password/<int:usuario_id>/', views.admin_force_password_change, name='admin_force_password_change'),
    path('admin-panel/avisos/', views.admin_avisos, name='admin_avisos'),
    path('admin-panel/avisos/enviar-masivo/', views.admin_enviar_avisos_masivos, name='admin_enviar_avisos_masivos'),
    path('admin-panel/avisos/enviar-individual/', views.admin_enviar_aviso_individual, name='admin_enviar_aviso_individual'),
    path('admin-panel/archivos/', views.admin_archivos, name='admin_archivos'),
    path('admin-panel/importar/', views.admin_importar, name='admin_importar'),
    path('admin-panel/exportar/', views.admin_exportar, name='admin_exportar'),
    path('admin-panel/config/', views.admin_config, name='admin_config'),
    path('admin-panel/auditoria/', views.admin_auditoria, name='admin_auditoria'),

    # Test de email
    path('admin-panel/test-email/', views.test_email_batch, name='test_email_batch'),
]
