from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
import csv
import re
from decimal import Decimal

from .models import (
    Alumno, RegistroDeuda, ConceptoDeuda, 
    PerfilUsuario, Pago, ConfiguracionSistema, RegistroAuditoria
)


# ==================== DECORADORES ====================

def admin_required(view_func):
    """Decorator que verifica si el usuario es administrador."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('portal:login')
        if not hasattr(request.user, 'perfil') or not request.user.perfil.es_admin:
            messages.error(request, 'No tiene permisos para acceder a esta sección.')
            return redirect('portal:portal_padre')
        return view_func(request, *args, **kwargs)
    return wrapper


def check_password_change(view_func):
    """Decorator que verifica si el usuario debe cambiar su contraseña."""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'perfil') and request.user.perfil.must_change_password:
                return redirect('portal:primer_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== AUTENTICACIÓN ====================

def login_view(request):
    """Vista de login."""
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil'):
            if request.user.perfil.must_change_password:
                return redirect('portal:primer_login')
            if request.user.perfil.es_admin:
                return redirect('portal:admin_dashboard')
        return redirect('portal:portal_padre')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            RegistroAuditoria.log(user, 'LOGIN', f'Inicio de sesión: {username}', request)
            
            # Verificar si debe cambiar contraseña
            if hasattr(user, 'perfil') and user.perfil.must_change_password:
                return redirect('portal:primer_login')
            
            # Redirigir según rol
            if hasattr(user, 'perfil') and user.perfil.es_admin:
                return redirect('portal:admin_dashboard')
            return redirect('portal:portal_padre')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'portal/login.html')


@login_required
def logout_view(request):
    """Vista de logout."""
    RegistroAuditoria.log(request.user, 'LOGOUT', 'Cierre de sesión', request)
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('portal:login')


@login_required
def primer_login_view(request):
    """Vista para cambio de contraseña obligatorio en primer ingreso."""
    if not hasattr(request.user, 'perfil') or not request.user.perfil.must_change_password:
        return redirect('portal:portal_padre')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validaciones
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            messages.error(request, 'Ingrese un email válido')
            return render(request, 'portal/primer_login.html')
        
        password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,20}$'
        if not re.match(password_regex, password):
            messages.error(request, 'La contraseña debe tener entre 8 y 20 caracteres, 1 mayúscula, 1 minúscula y 1 número')
            return render(request, 'portal/primer_login.html')
        
        if password != confirm_password:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'portal/primer_login.html')
        
        # Actualizar usuario
        request.user.email = email
        request.user.set_password(password)
        request.user.save()
        
        # Actualizar perfil
        if hasattr(request.user, 'perfil'):
            request.user.perfil.must_change_password = False
            request.user.perfil.save()
            
            # Actualizar email de alumnos vinculados a este DNI
            if request.user.perfil.dni:
                alumnos_vinculados = Alumno.objects.filter(
                    Q(padre_dni=request.user.perfil.dni) |
                    Q(madre_dni=request.user.perfil.dni) |
                    Q(tutor_dni=request.user.perfil.dni)
                )
                
                for alumno in alumnos_vinculados:
                    modificado = False
                    if alumno.padre_dni == request.user.perfil.dni:
                        alumno.padre_email = email
                        modificado = True
                    if alumno.madre_dni == request.user.perfil.dni:
                        alumno.madre_email = email
                        modificado = True
                    if alumno.tutor_dni == request.user.perfil.dni:
                        alumno.tutor_email = email
                        modificado = True
                    
                    # Si no estaba registrado como tutor explícitamente pero el DNI del alumno
                    # coincide con el DNI del usuario logueado (caso alumnos mayores)
                    if not modificado and alumno.documento == request.user.perfil.dni:
                        alumno.email = email
                        modificado = True
                        
                    if modificado:
                        alumno.save()
        
        RegistroAuditoria.log(request.user, 'PASSWORD_CHANGED', 'Primer ingreso completado', request)
        
        # Re-autenticar
        user = authenticate(request, username=request.user.username, password=password)
        if user:
            login(request, user)
        
        messages.success(request, 'Datos actualizados correctamente')
        return redirect('portal:portal_padre')
    
    return render(request, 'portal/primer_login.html')


# ==================== PORTAL PADRES ====================

@login_required
@check_password_change
def portal_padre(request):
    """Panel principal para padres/responsables."""
    config = ConfiguracionSistema.get_config()
    
    # Obtener DNI del usuario logueado
    dni = None
    if hasattr(request.user, 'perfil') and request.user.perfil.dni:
        dni = request.user.perfil.dni
    
    alumnos_data = []
    total_general = 0
    
    if dni:
        # Buscar alumnos por DNI de responsables
        alumnos = Alumno.objects.filter(
            Q(documento=dni) |
            Q(padre_dni=dni) |
            Q(madre_dni=dni) |
            Q(tutor_dni=dni)
        ).prefetch_related('deudas', 'deudas__concepto').distinct()
        
        for alumno in alumnos:
            deudas = alumno.deudas.exclude(estado='pago_verificado')
            total_alumno = deudas.filter(estado='pendiente').aggregate(total=Sum('monto'))['total'] or 0
            
            alumnos_data.append({
                'alumno': alumno,
                'deudas': alumno.deudas.all(),
                'total': total_alumno,
            })
            total_general += total_alumno
    
    context = {
        'config': config,
        'alumnos': alumnos_data,
        'total_adeudado': total_general,
        'usuario': request.user,
    }
    
    return render(request, 'portal/portal_padre.html', context)


@login_required
@check_password_change
def enviar_comprobante(request, deuda_id):
    """Vista para enviar comprobante de pago."""
    from django.urls import reverse
    
    deuda = get_object_or_404(RegistroDeuda, id=deuda_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        monto = request.POST.get('monto', '')
        comprobante = request.FILES.get('comprobante')
        
        if not comprobante:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Debe adjuntar un comprobante'})
            messages.error(request, 'Debe adjuntar un comprobante')
            return redirect('portal:portal_padre')
        
        try:
            monto_decimal = Decimal(monto)
        except:
            monto_decimal = deuda.monto
        
        # Crear registro de pago
        pago = Pago.objects.create(
            deuda=deuda,
            monto_pagado=monto_decimal,
            comprobante=comprobante,
            usuario_responsable=request.user
        )
        
        # Actualizar estado de la deuda
        deuda.estado = 'comprobante_enviado'
        deuda.save()
        
        RegistroAuditoria.log(
            request.user, 'PAYMENT_SUBMITTED', 
            f'Pago enviado: {pago.numero_operacion} - ${monto_decimal} - {deuda.concepto.nombre}',
            request
        )
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f'Comprobante enviado correctamente. Nº Operación: {pago.numero_operacion}',
                'recibo_url': reverse('portal:ver_recibo', args=[pago.id])
            })
        
        messages.success(request, f'Comprobante enviado correctamente. Nº Operación: {pago.numero_operacion}')
        return redirect('portal:ver_recibo', pago_id=pago.id)
    
    return redirect('portal:portal_padre')


@login_required
@check_password_change
def ver_recibo(request, pago_id):
    """Vista para ver el recibo provisorio."""
    pago = get_object_or_404(Pago, id=pago_id)
    
    context = {
        'pago': pago,
        'deuda': pago.deuda,
        'alumno': pago.deuda.alumno,
    }
    
    return render(request, 'portal/recibo.html', context)


# ==================== PANEL ADMINISTRATIVO ====================

@login_required
@admin_required
def admin_dashboard(request):
    """Dashboard administrativo con estadísticas."""
    deudas_count = RegistroDeuda.objects.count()
    pagos_pendientes = Pago.objects.filter(estado='pendiente').count()
    pagos_verificados = Pago.objects.filter(estado='verificado').count()
    total_recaudado = Pago.objects.filter(estado='verificado').aggregate(
        total=Sum('monto_pagado'))['total'] or 0
    
    # Pagos recientes pendientes de verificación
    pagos_recientes = Pago.objects.filter(estado='pendiente').order_by('-fecha_envio')[:5]
    
    context = {
        'deudas_count': deudas_count,
        'pagos_pendientes': pagos_pendientes,
        'pagos_verificados': pagos_verificados,
        'total_recaudado': total_recaudado,
        'pagos_recientes': pagos_recientes,
        'active_tab': 'dashboard',
    }
    
    return render(request, 'portal/admin/dashboard.html', context)


@login_required
@admin_required
def admin_deudas(request):
    """Lista de deudas con filtros y estadísticas."""
    deudas = RegistroDeuda.objects.select_related('alumno', 'concepto').exclude(monto=0).order_by('-id')
    
    # Estadísticas para el dashboard
    deudas_count = RegistroDeuda.objects.exclude(monto=0).count()
    pagos_pendientes = Pago.objects.filter(estado='pendiente').count()
    pagos_verificados = Pago.objects.filter(estado='verificado').count()
    total_recaudado = Pago.objects.filter(estado='verificado').aggregate(
        total=Sum('monto_pagado'))['total'] or 0
    
    # Filtros
    nivel_filter = request.GET.get('nivel', '')
    curso_filter = request.GET.get('curso', '')
    division_filter = request.GET.get('division', '')
    estado_filter = request.GET.get('estado', '')
    dni_filter = request.GET.get('dni', '').strip()
    
    if nivel_filter:
        deudas = deudas.filter(alumno__nivel=nivel_filter)
    if curso_filter:
        deudas = deudas.filter(alumno__curso=curso_filter)
    if division_filter:
        deudas = deudas.filter(alumno__division=division_filter)
    if estado_filter:
        deudas = deudas.filter(estado=estado_filter)
    if dni_filter:
        deudas = deudas.filter(alumno__documento__icontains=dni_filter)
    
    # Obtener opciones para los filtros
    # Niveles
    niveles_map = {'I4': 'Inicial 4', 'I5': 'Inicial 5', 'P': 'Primario', 'S': 'Secundario'}
    niveles_db = set(Alumno.objects.values_list('nivel', flat=True).distinct())
    niveles_ordenados = ['I4', 'I5', 'P', 'S'] + sorted([n for n in niveles_db if n and n not in niveles_map])
    niveles = [{'val': n, 'label': niveles_map.get(n, n), 'selected': n == nivel_filter} for n in niveles_ordenados]
    
    # Cursos
    cursos_db = Alumno.objects.values_list('curso', flat=True).distinct().order_by('curso')
    cursos_map = {'1': '1ro', '2': '2do', '3': '3ro', '4': '4to', '5': '5to', '6': '6to'}
    cursos = [{'val': c, 'label': cursos_map.get(c, c), 'selected': c == curso_filter} for c in cursos_db if c]
    
    # Divisiones
    divisiones_db = Alumno.objects.values_list('division', flat=True).distinct().order_by('division')
    divisiones = [{'val': d, 'label': f"División {d}", 'selected': d == division_filter} for d in divisiones_db if d]
    
    # Estados
    estados_options = [
        ('pendiente', 'Pendiente'),
        ('comprobante_enviado', 'Comprobante Enviado'),
        ('pago_verificado', 'Pago Verificado'),
    ]
    estados = [{'val': k, 'label': v, 'selected': k == estado_filter} for k, v in estados_options]

    paginator = Paginator(deudas, 50)
    page = request.GET.get('page', 1)
    deudas_page = paginator.get_page(page)
    
    context = {
        'deudas': deudas_page,
        'niveles': niveles,
        'cursos': cursos,
        'divisiones': divisiones,
        'estados': estados,
        'nivel_filter': nivel_filter,
        'curso_filter': curso_filter,
        'division_filter': division_filter,
        'estado_filter': estado_filter,
        'dni_filter': dni_filter,
        'active_tab': 'deudas',
        # Estadísticas
        'deudas_count': deudas_count,
        'pagos_pendientes': pagos_pendientes,
        'pagos_verificados': pagos_verificados,
        'total_recaudado': total_recaudado,
    }
    
    return render(request, 'portal/admin/deudas_final.html', context)


@login_required
@admin_required
def admin_pagos(request):
    """Lista de pagos con opción de verificar."""
    pagos = Pago.objects.select_related('deuda', 'deuda__alumno', 'usuario_responsable').all()
    
    # Estadísticas para el dashboard
    deudas_count = RegistroDeuda.objects.count()
    pagos_pendientes = Pago.objects.filter(estado='pendiente').count()
    pagos_verificados = Pago.objects.filter(estado='verificado').count()
    total_recaudado = Pago.objects.filter(estado='verificado').aggregate(
        total=Sum('monto_pagado'))['total'] or 0
    
    estado_filter = request.GET.get('estado', '')
    if estado_filter:
        pagos = pagos.filter(estado=estado_filter)
    
    paginator = Paginator(pagos, 50)
    page = request.GET.get('page', 1)
    pagos_page = paginator.get_page(page)
    
    context = {
        'pagos': pagos_page,
        'estado_filter': estado_filter,
        'active_tab': 'pagos',
        # Estadísticas
        'deudas_count': deudas_count,
        'pagos_pendientes': pagos_pendientes,
        'pagos_verificados': pagos_verificados,
        'total_recaudado': total_recaudado,
    }
    
    return render(request, 'portal/admin/pagos_fixed.html', context)


@login_required
@admin_required
def admin_verificar_pago(request, pago_id):
    """Verificar un pago."""
    pago = get_object_or_404(Pago, id=pago_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion', 'verificar')
        
        if accion == 'verificar':
            pago.verificar(request.user)
            RegistroAuditoria.log(
                request.user, 'PAYMENT_VERIFIED',
                f'Pago verificado: {pago.numero_operacion} - ${pago.monto_pagado}',
                request
            )
            messages.success(request, f'Pago {pago.numero_operacion} verificado correctamente')
        elif accion == 'rechazar':
            pago.estado = 'rechazado'
            pago.save()
            pago.deuda.estado = 'pendiente'
            pago.deuda.save()
            messages.warning(request, f'Pago {pago.numero_operacion} rechazado')
        
        return redirect('portal:admin_pagos')
    
    context = {
        'pago': pago,
        'active_tab': 'pagos',
    }
    
    return render(request, 'portal/admin/verificar_pago.html', context)


@login_required
@admin_required
def admin_usuarios(request):
    """Lista de alumnos por curso con estado de usuario."""
    # Obtener todos los alumnos agrupados por curso
    alumnos = Alumno.objects.all().order_by('apellido', 'nombres')
    
    # Agrupar por curso
    alumnos_por_curso = {}
    for alumno in alumnos:
        curso = alumno.curso_completo if alumno.curso_completo else 'Sin curso asignado'
        
        if curso not in alumnos_por_curso:
            alumnos_por_curso[curso] = []
        
        # Buscar si tiene usuario asociado
        perfil = PerfilUsuario.objects.select_related('usuario').filter(dni=alumno.documento).first()
        
        # Obtener email: Primero del usuario si existe, luego del tutor/responsable
        email_responsable = ''
        if perfil and perfil.usuario.email:
            email_responsable = perfil.usuario.email
        else:
            email_responsable = alumno.tutor_email or alumno.padre_email or alumno.madre_email or alumno.email or ''
        
        alumnos_por_curso[curso].append({
            'alumno': alumno,
            'nombre_completo': f"{alumno.nombres} {alumno.apellido}",
            'dni': alumno.documento,
            'email': email_responsable,
            'perfil': perfil,
            'tiene_usuario': perfil is not None,
            'must_change_password': perfil.must_change_password if perfil else True,
        })
    
    context = {
        'alumnos_por_curso': dict(sorted(alumnos_por_curso.items())),
        'active_tab': 'usuarios',
    }
    
    return render(request, 'portal/admin/usuarios.html', context)


@login_required
@admin_required
def admin_reset_password(request, usuario_id):
    """Resetear contraseña de un usuario."""
    perfil = get_object_or_404(PerfilUsuario, id=usuario_id)
    config = ConfiguracionSistema.get_config()
    
    perfil.usuario.set_password(config.password_default)
    perfil.usuario.save()
    perfil.must_change_password = True
    perfil.save()
    
    RegistroAuditoria.log(
        request.user, 'PASSWORD_RESET',
        f'Contraseña reseteada para {perfil.usuario.username}',
        request
    )
    
    messages.success(request, f'Contraseña de {perfil.usuario.username} reseteada a la genérica')
    return redirect('portal:admin_usuarios')


@login_required
@admin_required
def admin_force_password_change(request, usuario_id):
    """Forzar cambio de contraseña en el próximo login."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    perfil = get_object_or_404(PerfilUsuario, id=usuario_id)
    perfil.must_change_password = True
    perfil.save()
    
    RegistroAuditoria.log(
        request.user, 'PASSWORD_RESET',
        f'Forzado cambio de contraseña para {perfil.usuario.username}',
        request
    )
    
    return JsonResponse({'success': True})


@login_required
@admin_required
def admin_crear_alumno(request):
    """Crear un nuevo alumno y su usuario correspondiente."""
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos inválidos'})
    
    # Validar campos obligatorios
    documento = data.get('documento', '').strip()
    apellido = data.get('apellido', '').strip()
    nombres = data.get('nombres', '').strip()
    nivel = data.get('nivel', '').strip()
    curso = data.get('curso', '').strip()
    division = data.get('division', '').strip()
    tutor_email = data.get('tutor_email', '').strip()
    tutor_nombre = data.get('tutor_nombre', '').strip()
    tutor_dni = data.get('tutor_dni', '').strip()
    
    if not all([documento, apellido, nombres, nivel, curso, division, tutor_email]):
        return JsonResponse({'success': False, 'error': 'Complete todos los campos obligatorios'})
    
    # Validar DNI
    try:
        dni_alumno = int(documento)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'DNI inválido'})
    
    # Verificar que el alumno no exista
    if Alumno.objects.filter(documento=dni_alumno).exists():
        return JsonResponse({'success': False, 'error': f'Ya existe un alumno con DNI {dni_alumno}'})
    
    # Verificar que el username no exista
    username = str(dni_alumno)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'success': False, 'error': f'Ya existe un usuario con ese DNI'})
    
    config = ConfiguracionSistema.get_config()
    
    try:
        # Crear Alumno
        alumno = Alumno.objects.create(
            documento=dni_alumno,
            apellido=apellido,
            nombres=nombres,
            nivel=nivel,
            curso=curso,
            division=division,
            tutor_email=tutor_email,
            tutor_nombre=tutor_nombre,
            tutor_dni=int(tutor_dni) if tutor_dni else None,
        )
        
        # Crear User
        user = User.objects.create_user(
            username=username,
            password=config.password_default,
            first_name=nombres,
            last_name=apellido,
            email=tutor_email
        )
        
        # Crear PerfilUsuario
        PerfilUsuario.objects.create(
            usuario=user,
            dni=dni_alumno,
            rol='padre',
            must_change_password=True
        )
        
        # Registrar en auditoría
        RegistroAuditoria.log(
            request.user, 'USER_CREATED',
            f'Alumno y usuario creado: {apellido}, {nombres} (DNI: {dni_alumno})',
            request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Usuario creado exitosamente',
            'dni': dni_alumno,
            'password_default': config.password_default
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error al crear usuario: {str(e)}'})


@login_required
@admin_required
def admin_avisos(request):
    """Envío de avisos de deuda."""
    # Obtener morosos (deudas pendientes agrupadas por alumno)
    morosos = []
    alumnos_con_deuda = Alumno.objects.filter(
        deudas__estado='pendiente'
    ).annotate(
        total_deuda=Sum('deudas__monto', filter=Q(deudas__estado='pendiente'))
    ).distinct()
    
    for alumno in alumnos_con_deuda:
        # Buscar email del responsable
        perfil = PerfilUsuario.objects.select_related('usuario').filter(dni=alumno.documento).first()
        email = ''
        if perfil and perfil.usuario.email:
            email = perfil.usuario.email
        else:
            email = alumno.padre_email or alumno.madre_email or alumno.tutor_email or alumno.email
        
        morosos.append({
            'alumno': alumno,
            'email': email,
            'total_deuda': alumno.total_deuda or 0,
        })
    
    context = {
        'morosos': morosos,
        'config': ConfiguracionSistema.get_config(),
        'active_tab': 'avisos',
    }
    
    return render(request, 'portal/admin/avisos.html', context)


@login_required
@admin_required
def admin_enviar_avisos_masivos(request):
    """Enviar avisos masivos a todos los morosos por email.
    
    Envía el mismo mensaje genérico a todos los morosos con email.
    Lanza el envío en un hilo separado para no trabar Railway.
    """
    from .email_services import enviar_emails_masivos_async
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    asunto = request.POST.get('asunto', '').strip()
    mensaje = request.POST.get('mensaje', '').strip()
    
    if not asunto or not mensaje:
        return JsonResponse({'success': False, 'error': 'Debe completar el asunto y el mensaje'})
    
    # Obtener morosos con deuda pendiente
    alumnos_con_deuda = Alumno.objects.filter(
        deudas__estado='pendiente'
    ).distinct()
    
    destinatarios = []
    emails_sin_correo = []
    
    for alumno in alumnos_con_deuda:
        # Prioridad: email del User (actualizado en primer login) > emails del Alumno
        perfil = PerfilUsuario.objects.select_related('usuario').filter(dni=alumno.documento).first()
        email = ''
        if perfil and perfil.usuario.email:
            email = perfil.usuario.email
        else:
            email = alumno.padre_email or alumno.madre_email or alumno.tutor_email or alumno.email
        
        if email:
            destinatarios.append(email)
        else:
            emails_sin_correo.append(alumno.nombre_completo)
    
    # Deduplicar emails (un padre puede tener varios hijos)
    destinatarios = list(set(destinatarios))
    
    if not destinatarios:
        return JsonResponse({
            'success': False, 
            'error': 'No hay morosos con email registrado para enviar avisos'
        })
    
    # Construir versión HTML del mensaje con links clicables
    import re
    mensaje_html = mensaje.replace('\n', '<br>')
    # Hacer clicables las URLs del portal
    mensaje_html = re.sub(
        r'(https?://[^\s<]+)',
        r'<a href="\1" target="_blank" style="color:#1976D2;font-weight:bold;">\1</a>',
        mensaje_html
    )
    mensaje_html = f'<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#333;">{mensaje_html}</div>'
    
    # Lanzar envío en hilo separado (no bloquea Railway)
    enviar_emails_masivos_async(
        destinatarios=destinatarios,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        batch_size=50,
        delay=10,
        total_padres_db=len(destinatarios) + len(emails_sin_correo),
    )
    
    # Registrar en auditoría
    RegistroAuditoria.log(
        request.user, 'EMAIL_SENT',
        f'Envío masivo iniciado: {len(destinatarios)} emails en background - Asunto: {asunto[:50]}',
        request
    )
    
    return JsonResponse({
        'success': True,
        'enviados': len(destinatarios),
        'emails': destinatarios,
        'sin_correo': emails_sin_correo,
        'message': f'Envío masivo iniciado: {len(destinatarios)} emails se están enviando en segundo plano'
    })


@login_required
@admin_required
def admin_enviar_aviso_individual(request):
    """Enviar aviso individual a un moroso por email."""
    from django.core.mail import send_mail, BadHeaderError
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    email = request.POST.get('email', '').strip()
    asunto = request.POST.get('asunto', '').strip()
    mensaje = request.POST.get('mensaje', '').strip()
    
    if not email or not asunto or not mensaje:
        return JsonResponse({'success': False, 'error': 'Faltan datos requeridos (email, asunto o mensaje)'})
    
    try:
        from django.conf import settings as django_settings
        from_email = getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'cobranzasns@colegionuevosiglo.edu.ar')
        
        # Enviar email
        send_mail(
            asunto,
            mensaje,
            from_email,
            [email],
            fail_silently=False,
        )
        
        # Registrar en auditoría
        RegistroAuditoria.log(
            request.user, 'EMAIL_SENT',
            f'Aviso individual enviado a {email} - Asunto: {asunto[:50]}',
            request
        )
        
        return JsonResponse({'success': True, 'message': f'Email enviado correctamente a {email}'})
        
    except BadHeaderError:
        return JsonResponse({'success': False, 'error': 'Error en el encabezado del email'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error al enviar email: {str(e)}'})


@login_required
@login_required
@login_required
@admin_required
def admin_cobro(request):
    """Vista para generar deudas mensuales (Publicar Pagos)."""
    conceptos = ConceptoDeuda.objects.all().order_by('orden', 'codigo')
    
    context = {
        'active_tab': 'cobro',
        'conceptos': conceptos,
    }
    return render(request, 'portal/admin/cobro.html', context)


@login_required
@admin_required
def admin_archivos(request):
    """Vista unificada de Archivos (Importar/Exportar)."""
    # Datos para Exportar
    alumnos_count = Alumno.objects.count()
    deudas_count = RegistroDeuda.objects.filter(estado='pendiente').count()
    total_deuda = RegistroDeuda.objects.filter(estado='pendiente').aggregate(
        total=Sum('monto'))['total'] or 0
    
    # Contexto base
    context = {
        'alumnos_count': alumnos_count,
        'deudas_count': deudas_count,
        'total_deuda': total_deuda,
        'active_tab': 'archivos',
        'fecha_actual': timezone.now().strftime('%Y%m%d'),
        'resultados': request.session.pop('import_resultados', None) # Recuperar resultados si existen
    }
    
    return render(request, 'portal/admin/archivos.html', context)


@login_required
@admin_required
def admin_importar(request):
    """Importar deudas desde Excel o CSV - Soporta formato del colegio."""
    import openpyxl
    from io import BytesIO
    import re
    
    resultados = None
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        reemplazar = request.POST.get('reemplazar') == 'on'
        filename = archivo.name.lower()
        
        config = ConfiguracionSistema.get_config()
        added = 0
        updated = 0
        skipped = 0
        duplicados = 0
        users_created = 0
        errores = []
        
        try:
            # Reiniciar la base de datos de deudas y pagos antes de importar
            # Esto reinicia los contadores del dashboard
            RegistroDeuda.objects.all().delete()
            
            # Procesar Excel
            if filename.endswith(('.xlsx', '.xls')):
                wb = openpyxl.load_workbook(BytesIO(archivo.read()))
                ws = wb.active
                
                # Obtener headers
                headers = []
                headers_raw = []
                for cell in ws[1]:
                    raw_val = str(cell.value).strip() if cell.value else ''
                    headers_raw.append(raw_val)
                    headers.append(raw_val.lower())
                
                # Detectar formato del colegio (columnas pivoteadas de conceptos)
                # El formato del colegio tiene: Documento, Apellido, Nombres, Niv, Cur, Div
                # y columnas de conceptos como: 0_Matrícula, 1_Cuota, 2_Cuota, etc.
                is_colegio_format = (
                    'documento' in headers and 
                    'apellido' in headers and
                    any('_' in h for h in headers)  # Columnas de concepto tienen formato N_Concepto
                )
                
                if is_colegio_format:
                    # FORMATO DEL COLEGIO - Columnas pivoteadas
                    # Identificar columnas de conceptos (tienen formato: numero_nombre)
                    concepto_columns = []
                    for idx, header in enumerate(headers_raw):
                        if '_' in header and idx > 7:  # Las primeras 8 columnas son datos del alumno
                            concepto_columns.append((idx, header))
                    
                    # Procesar cada fila
                    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                        if not any(row):
                            continue
                        
                        # Crear diccionario con headers
                        row_dict = {}
                        for i, value in enumerate(row):
                            if i < len(headers):
                                row_dict[headers[i]] = value
                        
                        # Extraer datos del alumno
                        dni_val = row_dict.get('documento')
                        if not dni_val:
                            errores.append(f'Fila {row_idx}: Sin documento')
                            skipped += 1
                            continue
                        
                        try:
                            dni_alumno = int(dni_val)
                        except:
                            errores.append(f'Fila {row_idx}: DNI inválido "{dni_val}"')
                            skipped += 1
                            continue
                        
                        apellido = str(row_dict.get('apellido', '')).strip()
                        nombres = str(row_dict.get('nombres', '')).strip()
                        nivel = str(row_dict.get('niv', '')).strip()
                        curso = str(row_dict.get('cur', '')).strip()
                        division = str(row_dict.get('div', '')).strip()
                        
                        # Crear/obtener alumno
                        alumno, alumno_created = Alumno.objects.get_or_create(
                            documento=dni_alumno,
                            defaults={
                                'apellido': apellido,
                                'nombres': nombres,
                                'nivel': nivel,
                                'curso': curso,
                                'division': division,
                            }
                        )
                        
                        # Actualizar datos si cambió
                        if not alumno_created:
                            updated_alumno = False
                            if nivel and alumno.nivel != nivel:
                                alumno.nivel = nivel
                                updated_alumno = True
                            if curso and alumno.curso != curso:
                                alumno.curso = curso
                                updated_alumno = True
                            if division and alumno.division != division:
                                alumno.division = division
                                updated_alumno = True
                            if updated_alumno:
                                alumno.save()
                        
                        # Crear usuario si no existe
                        username = str(dni_alumno)
                        if not User.objects.filter(username=username).exists():
                            user = User.objects.create_user(
                                username=username,
                                password=config.password_default,
                                first_name=nombres,
                                last_name=apellido
                            )
                            PerfilUsuario.objects.create(
                                usuario=user,
                                dni=dni_alumno,
                                rol='padre',
                                must_change_password=True
                            )
                            users_created += 1
                        
                        # Procesar cada columna de concepto
                        for col_idx, concepto_header in concepto_columns:
                            monto_val = row[col_idx] if col_idx < len(row) else None
                            
                            if monto_val is None or monto_val == '' or monto_val == 0:
                                continue  # Sin deuda en este concepto
                            
                                                        
                            # Parsear nombre del concepto (formato: "N_NombreConcepto")
                            parts = concepto_header.split('_', 1)
                            if len(parts) == 2:
                                concepto_codigo = parts[0]
                                concepto_nombre = parts[1].replace('_', ' ').title()
                            else:
                                concepto_codigo = concepto_header[:10]
                                concepto_nombre = concepto_header
                            
                            # Obtener o crear concepto
                            concepto, _ = ConceptoDeuda.objects.get_or_create(
                                codigo=concepto_codigo,
                                defaults={'nombre': concepto_nombre, 'orden': int(concepto_codigo) if concepto_codigo.isdigit() else 99}
                            )
                            
                            # Validar valores especiales (Texto)
                            val_str = str(monto_val).lower().strip()
                            if 'pagad' in val_str:
                                # Crear deuda pagada (monto 0 para no afectar deuda total, pero estado pagado)
                                # Verificar duplicado (mismo alumno + concepto)
                                deuda_existente = RegistroDeuda.objects.filter(
                                    alumno=alumno,
                                    concepto=concepto
                                ).first()
                                
                                if deuda_existente:
                                    if reemplazar:
                                        deuda_existente.monto = 0
                                        deuda_existente.estado = 'pagado'
                                        deuda_existente.save()
                                        updated += 1
                                    else:
                                        duplicados += 1
                                else:
                                    RegistroDeuda.objects.create(
                                        alumno=alumno,
                                        concepto=concepto,
                                        monto=0,
                                        periodo='',
                                        estado='pagado'
                                    )
                                    added += 1
                                continue
                            
                            if 'no corresponde' in val_str or 'nocorresponde' in val_str:
                                # Crear registro "No Corresponde"
                                deuda_existente = RegistroDeuda.objects.filter(
                                    alumno=alumno,
                                    concepto=concepto
                                ).first()
                                
                                if deuda_existente:
                                    if reemplazar:
                                        deuda_existente.monto = 0
                                        deuda_existente.estado = 'no_corresponde'
                                        deuda_existente.save()
                                        updated += 1
                                    else:
                                        duplicados += 1
                                else:
                                    RegistroDeuda.objects.create(
                                        alumno=alumno,
                                        concepto=concepto,
                                        monto=0,
                                        periodo='',
                                        estado='no_corresponde'
                                    )
                                    added += 1
                                continue

                            try:
                                monto = Decimal(str(monto_val).replace(',', '.'))
                                if monto <= 0:
                                    continue
                            except:
                                continue
                            

                            # Verificar duplicado (mismo alumno + concepto)
                            deuda_existente = RegistroDeuda.objects.filter(
                                alumno=alumno,
                                concepto=concepto
                            ).first()
                            
                            if deuda_existente:
                                if reemplazar:
                                    deuda_existente.monto = monto
                                    deuda_existente.estado = 'pendiente'
                                    deuda_existente.save()
                                    updated += 1
                                else:
                                    duplicados += 1
                            else:
                                RegistroDeuda.objects.create(
                                    alumno=alumno,
                                    concepto=concepto,
                                    monto=monto,
                                    periodo='',
                                    estado='pendiente'
                                )
                                added += 1
                
                else:
                    # FORMATO ESTÁNDAR - Una fila por deuda
                    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                        if not any(row):
                            continue
                        
                        row_dict = {}
                        for i, value in enumerate(row):
                            if i < len(headers) and headers[i]:
                                row_dict[headers[i]] = str(value).strip() if value is not None else ''
                        
                        result = procesar_fila_estandar(row_idx, row_dict, config, reemplazar)
                        if result['status'] == 'added':
                            added += 1
                        elif result['status'] == 'updated':
                            updated += 1
                        elif result['status'] == 'duplicado':
                            duplicados += 1
                        elif result['status'] == 'error':
                            skipped += 1
                            errores.append(result['error'])
                        if result.get('user_created'):
                            users_created += 1
            
            # Procesar CSV (formato estándar)
            elif filename.endswith('.csv'):
                decoded = archivo.read().decode('utf-8-sig')
                lines = decoded.strip().split('\n')
                delimiter = ',' if ',' in lines[0] else ';'
                reader = csv.DictReader(lines, delimiter=delimiter)
                
                for row_idx, row in enumerate(reader, start=2):
                    row_dict = {k.lower().strip(): v.strip() for k, v in row.items() if k}
                    result = procesar_fila_estandar(row_idx, row_dict, config, reemplazar)
                    if result['status'] == 'added':
                        added += 1
                    elif result['status'] == 'updated':
                        updated += 1
                    elif result['status'] == 'duplicado':
                        duplicados += 1
                    elif result['status'] == 'error':
                        skipped += 1
                        errores.append(result['error'])
                    if result.get('user_created'):
                        users_created += 1
            else:
                messages.error(request, 'Formato no soportado. Use Excel (.xlsx) o CSV (.csv)')
                return render(request, 'portal/admin/importar.html', {'active_tab': 'importar'})
            
            # Guardar resultados
            resultados = {
                'added': added,
                'updated': updated,
                'skipped': skipped,
                'duplicados': duplicados,
                'users_created': users_created,
                'errores': errores[:20],
                'total_errores': len(errores),
            }
            
            RegistroAuditoria.log(
                request.user, 'IMPORT',
                f'Importación: {added} nuevas, {updated} actualizadas, {duplicados} duplicados, {skipped} omitidas, {users_created} usuarios',
                request
            )
            
            if added > 0 or updated > 0:
                messages.success(request, f'✅ Importación completada: {added} deudas nuevas, {updated} actualizadas, {users_created} usuarios creados')
            if duplicados > 0:
                messages.warning(request, f'⚠️ {duplicados} registros duplicados no fueron importados (ya existen)')
            if skipped > 0:
                messages.warning(request, f'⚠️ {skipped} registros omitidos por errores')
                
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
    
    context = {
        'active_tab': 'importar',
        'resultados': resultados,
    }
    
    return render(request, 'portal/admin/importar.html', context)


def procesar_fila_estandar(row_idx, row, config, reemplazar):
    """Procesa una fila en formato estándar (una deuda por fila)."""
    result = {'status': 'error', 'error': '', 'user_created': False}
    
    # Mapear columnas flexibles
    alumno_nombre = (
        row.get('alumno') or row.get('nombre_alumno') or 
        row.get('estudiante') or row.get('nombre') or ''
    )
    
    dni_str = (
        row.get('dni_alumno') or row.get('dni') or 
        row.get('documento') or row.get('doc') or ''
    ).replace('.', '').replace('-', '')
    
    curso = (
        row.get('curso') or row.get('division') or 
        row.get('curso/division') or row.get('grado') or ''
    )
    
    concepto_nombre = (
        row.get('concepto') or row.get('descripcion') or 
        row.get('detalle') or 'Cuota'
    )
    
    monto_str = (
        row.get('monto') or row.get('importe') or 
        row.get('monto_adeudado') or row.get('deuda') or '0'
    )
    
    periodo = (
        row.get('periodo') or row.get('mes') or 
        row.get('mes_periodo') or row.get('fecha') or ''
    )
    
    # Validar DNI
    if not dni_str:
        result['error'] = f'Fila {row_idx}: Sin DNI - {alumno_nombre}'
        return result
    
    try:
        dni_alumno = int(dni_str)
    except ValueError:
        result['error'] = f'Fila {row_idx}: DNI inválido "{dni_str}"'
        return result
    
    # Validar monto
    try:
        monto = Decimal(monto_str.replace(',', '.').replace('$', '').strip())
    except:
        result['error'] = f'Fila {row_idx}: Monto inválido "{monto_str}"'
        return result
    
    # Parsear nombre
    if ',' in alumno_nombre:
        apellido = alumno_nombre.split(',')[0].strip()
        nombres = alumno_nombre.split(',')[1].strip() if len(alumno_nombre.split(',')) > 1 else ''
    else:
        partes = alumno_nombre.split()
        apellido = partes[0] if partes else ''
        nombres = ' '.join(partes[1:]) if len(partes) > 1 else ''
    
    # Obtener o crear alumno
    alumno, alumno_created = Alumno.objects.get_or_create(
        documento=dni_alumno,
        defaults={'apellido': apellido, 'nombres': nombres, 'curso': curso}
    )
    
    if not alumno_created and curso and alumno.curso != curso:
        alumno.curso = curso
        alumno.save()
    
    # Crear usuario si no existe
    username = str(dni_alumno)
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(
            username=username,
            password=config.password_default,
            first_name=nombres,
            last_name=apellido
        )
        PerfilUsuario.objects.create(
            usuario=user,
            dni=dni_alumno,
            rol='padre',
            must_change_password=True
        )
        result['user_created'] = True
    
    # Obtener o crear concepto
    concepto, _ = ConceptoDeuda.objects.get_or_create(
        codigo=concepto_nombre[:20].upper().replace(' ', '_'),
        defaults={'nombre': concepto_nombre}
    )
    
    # Verificar duplicado
    deuda_existente = RegistroDeuda.objects.filter(
        alumno=alumno,
        concepto=concepto,
        periodo=periodo
    ).first()
    
    if deuda_existente:
        if reemplazar:
            deuda_existente.monto = monto
            deuda_existente.save()
            result['status'] = 'updated'
        else:
            result['status'] = 'duplicado'
    else:
        RegistroDeuda.objects.create(
            alumno=alumno,
            concepto=concepto,
            monto=monto,
            periodo=periodo,
            estado='pendiente'
        )
        result['status'] = 'added'
    
    return result


@login_required
@admin_required
def admin_exportar(request):
    """Exportar deudas a Excel o CSV con formato pivoteado."""
    from io import BytesIO
    from decimal import Decimal
    from django.conf import settings
    import os
    from openpyxl.utils import get_column_letter

    if request.method == 'POST':
        formato = request.POST.get('formato', 'csv')
        
        # 1. Obtener todos los conceptos para encabezados (Columnas I en adelante)
        conceptos = ConceptoDeuda.objects.all().order_by('orden', 'codigo')
        
        # 2. Obtener todos los alumnos
        alumnos = Alumno.objects.all().order_by('apellido', 'nombres')
        
        # 3. Obtener TODAS las deudas (Snapshot en tiempo real)
        all_deudas = RegistroDeuda.objects.select_related('alumno', 'concepto').all()
        
        # 4. Mapear deudas en memoria para acceso rápido
        # Estructura: deudas_map[alumno_pk] = { concepto_id: valor }
        # Valor puede ser el monto (si es pendiente) o 'pagado' (si está verificado)
        deudas_map = {}
        for d in all_deudas:
            if d.alumno_id not in deudas_map:
                deudas_map[d.alumno_id] = {}
            
            # Prioridad: Si ya hay un estado 'pagado' para este concepto, se mantiene.
            # Si no, se guarda el actual.
            current_val = deudas_map[d.alumno_id].get(d.concepto_id)
            
            # Si ya está marcado como texto especial, no sobrescribir excepto si hay pago real?
            if current_val in ['pagado', 'no corresponde']:
                continue

            if d.estado in ['pago_verificado', 'pagado']:
                deudas_map[d.alumno_id][d.concepto_id] = 'pagado'
            elif d.estado == 'no_corresponde':
                deudas_map[d.alumno_id][d.concepto_id] = 'no corresponde'
            else:
                # Si es pendiente/otro, sumamos el monto
                if isinstance(current_val, (int, float, Decimal)):
                    deudas_map[d.alumno_id][d.concepto_id] += d.monto
                else:
                    deudas_map[d.alumno_id][d.concepto_id] = d.monto
        
        # Headers del archivo
        headers = ['Familia', 'Documento', 'Apellido', 'Nombres', 'Niv', 'Cur', 'Div', 'Saldo_Moroso']
        # Agregar headers dinámicos de conceptos
        headers.extend([f"{c.codigo}_{c.nombre}" for c in conceptos])
        
        # Construir filas
        rows = []
        for alumno in alumnos:
            datos_deuda = deudas_map.get(alumno.pk, {})
            
            # Fila base
            row = [
                alumno.familia,
                alumno.documento,
                alumno.apellido,
                alumno.nombres,
                alumno.nivel,
                alumno.curso,
                alumno.division,
                0, # Placeholder para Saldo_Moroso (Index 7, Col H)
            ]
            
            # Rellenar columnas de conceptos
            for concepto in conceptos:
                val = datos_deuda.get(concepto.id, 0.0)
                # Excel prefiere números o string 'pagado'
                if val == 'pagado':
                    row.append('pagado')
                elif val == 'no corresponde':
                    row.append('no corresponde')
                else:
                    row.append(float(val))
            
            rows.append(row)
        
        # Crear directorio de exportaciones si no existe
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exportaciones')
        os.makedirs(export_dir, exist_ok=True)
        
        fecha_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        if formato == 'excel':
            # Generar Excel
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Deudas"
            
            # Escribir headers con estilo
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="800020", end_color="800020", fill_type="solid")
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            
            # Escribir datos
            last_col_idx = len(headers)
            last_col_letter = get_column_letter(last_col_idx)
            start_sum_col = 9 # Columna I (Conceptos empiezan acá)
            start_sum_letter = get_column_letter(start_sum_col)
            
            for row_idx, row_data in enumerate(rows, 2):
                for col_idx, value in enumerate(row_data, 1):
                    # Si es la columna H (Saldo Moroso, index 8), poner fórmula
                    if col_idx == 8:
                        # Formula: =SUM(I{row}:<Last>{row})
                        formula = f"=SUM({start_sum_letter}{row_idx}:{last_col_letter}{row_idx})"
                        ws.cell(row=row_idx, column=col_idx, value=formula)
                    else:
                        ws.cell(row=row_idx, column=col_idx, value=value)
            
            # Ajustar anchos de columna
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws.column_dimensions[column].width = min(max_length + 2, 30)
            
            filename = f'deudas_{fecha_str}.xlsx'
            filepath = os.path.join(export_dir, filename)
            wb.save(filepath)
            
        else:
            # Generar CSV
            filename = f'deudas_{fecha_str}.csv'
            filepath = os.path.join(export_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row_data in rows:
                    # Calcular saldo para CSV manual
                    saldo = 0
                    csv_row = list(row_data) # Copia
                    
                    # Sumar conceptos (Indices 8 en adelante)
                    for val in csv_row[8:]:
                        if isinstance(val, (int, float)):
                            saldo += val
                    
                    csv_row[7] = saldo # Actualizar Col H
                    writer.writerow(csv_row)
        
        RegistroAuditoria.log(
            request.user, 'EXPORT',
            f'Exportación de deudas ({len(rows)} alumnos) en formato {formato.upper()}',
            request
        )
        
        # Redirigir a la descarga del archivo
        from django.http import FileResponse
        file_handle = open(filepath, 'rb')
        response = FileResponse(file_handle, as_attachment=True, filename=filename)
        return response
    
    # GET - Mostrar página
    alumnos_count = Alumno.objects.count()
    deudas_count = RegistroDeuda.objects.filter(estado='pendiente').count()
    total_deuda = RegistroDeuda.objects.filter(estado='pendiente').aggregate(
        total=Sum('monto'))['total'] or 0
    
    return redirect('portal:admin_archivos')


@login_required
@admin_required
def admin_config(request):
    """Configuración del sistema."""
    config = ConfiguracionSistema.get_config()
    
    if request.method == 'POST':
        config.alias_transferencia = request.POST.get('alias', config.alias_transferencia)
        config.cbu = request.POST.get('cbu', config.cbu)
        config.password_default = request.POST.get('password_default', config.password_default)
        config.save()
        
        RegistroAuditoria.log(request.user, 'CONFIG_UPDATE', 'Configuración actualizada', request)
        messages.success(request, 'Configuración guardada correctamente')
    
    # Obtener usuarios admin
    admins = PerfilUsuario.objects.filter(rol='admin').select_related('usuario')
    
    context = {
        'config': config,
        'admins': admins,
        'active_tab': 'config',
    }
    
    return render(request, 'portal/admin/config.html', context)


@login_required
@admin_required
def admin_auditoria(request):
    """Log de auditoría."""
    from datetime import datetime
    
    fecha = request.GET.get('fecha', '')
    usuario = request.GET.get('usuario', '')

    registros = RegistroAuditoria.objects.select_related('usuario').all()
    
    if fecha:
        try:
            dt = datetime.strptime(fecha, '%Y-%m-%d')
            registros = registros.filter(timestamp__date=dt.date())
        except ValueError:
            pass
            
    if usuario:
        registros = registros.filter(usuario__username__icontains=usuario)

    registros = registros[:200]
    
    context = {
        'registros': registros,
        'active_tab': 'auditoria',
        'filtro_fecha': fecha,
        'filtro_usuario': usuario,
    }
    
    return render(request, 'portal/admin/auditoria.html', context)


# ==================== VISTAS PÚBLICAS (consulta sin login) ====================

def consulta_publica(request):
    """
    Vista pública para consultar deudas sin login.
    Permite buscar por DNI del alumno o responsable.
    """
    context = {
        'alumnos': [],
        'total_adeudado': 0,
        'dni_buscado': '',
        'mensaje_error': '',
        'busqueda_realizada': False,
    }
    
    dni = request.GET.get('dni', '').strip()
    
    if dni:
        context['dni_buscado'] = dni
        context['busqueda_realizada'] = True
        
        try:
            dni_int = int(dni)
            
            alumnos = Alumno.objects.filter(
                Q(documento=dni_int) |
                Q(padre_dni=dni_int) |
                Q(madre_dni=dni_int) |
                Q(tutor_dni=dni_int)
            ).prefetch_related('deudas', 'deudas__concepto').distinct()
            
            if alumnos.exists():
                alumnos_data = []
                total_general = 0
                
                for alumno in alumnos:
                    deudas_pendientes = alumno.deudas.filter(estado='pendiente')
                    total_alumno = deudas_pendientes.aggregate(total=Sum('monto'))['total'] or 0
                    
                    alumnos_data.append({
                        'alumno': alumno,
                        'deudas': alumno.deudas.all(),
                        'total': total_alumno,
                    })
                    total_general += total_alumno
                
                context['alumnos'] = alumnos_data
                context['total_adeudado'] = total_general
            else:
                context['mensaje_error'] = f'No se encontraron registros para el DNI {dni}'
                
        except ValueError:
            context['mensaje_error'] = 'Por favor ingrese un DNI válido (solo números)'
    
    return render(request, 'portal/consulta_publica.html', context)


# ==================== TEST EMAIL ====================

@login_required
@admin_required
def test_email_batch(request):
    """
    Vista de prueba para verificar el sistema de envío masivo.
    Envía 5 emails de prueba usando el servicio de batching.
    Solo accesible para administradores.
    """
    from .email_services import enviar_emails_masivos
    from django.conf import settings as django_settings

    # 5 emails de prueba (cambiar por direcciones propias)
    emails_prueba = [
        'joeljjs100@gmail.com',
        'clientmagnetweb@gmail.com',
    ]

    resultado = enviar_emails_masivos(
        destinatarios=emails_prueba,
        asunto='[TEST] Prueba de envío masivo — Colegio Nuevo Siglo',
        mensaje_texto=(
            'Este es un email de prueba del sistema de envío masivo.\n'
            'Si recibís este mensaje, el sistema funciona correctamente.\n\n'
            'Colegio Nuevo Siglo'
        ),
        mensaje_html=(
            '<h2>Prueba de Envío Masivo</h2>'
            '<p>Este es un email de prueba del sistema de envío masivo.</p>'
            '<p>Si recibís este mensaje, el sistema funciona correctamente.</p>'
            '<br><p><strong>Colegio Nuevo Siglo</strong></p>'
        ),
        batch_size=1,
        delay=30,
    )

    backend_actual = django_settings.EMAIL_BACKEND
    test_mode = getattr(django_settings, 'EMAIL_TEST_MODE', True)

    return JsonResponse({
        'success': True,
        'modo': 'CONSOLA (test)' if test_mode else 'SMTP REAL',
        'backend': backend_actual,
        'resultado': resultado,
    })
