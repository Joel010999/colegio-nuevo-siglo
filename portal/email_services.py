"""
email_services.py — Servicio de envío masivo de emails con batching.

Diseñado para enviar hasta 700+ emails sin que Gmail bloquee la cuenta.
Divide los destinatarios en tandas de 50, con pausas entre tandas.
Incluye ejecución en hilo separado para no trabar el servidor de Railway.
"""

import time
import threading
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def obtener_emails_desde_db():
    """
    Consulta la base de datos para obtener todos los emails de padres/responsables
    que no estén vacíos. Prioriza el email del User (actualizado en primer login)
    y como fallback usa los emails del modelo Alumno.

    Returns:
        dict con claves:
            - "emails": list — lista de emails únicos no vacíos.
            - "total_padres": int — cantidad total de perfiles de padre en la DB.
    """
    from .models import PerfilUsuario, Alumno

    emails = set()

    # 1) Emails de usuarios con perfil de padre que ya actualizaron su email
    perfiles_padre = PerfilUsuario.objects.filter(rol='padre').select_related('usuario')
    total_padres = perfiles_padre.count()

    for perfil in perfiles_padre:
        user_email = perfil.usuario.email
        if user_email and user_email.strip():
            emails.add(user_email.strip().lower())
        else:
            # Fallback: buscar en el modelo Alumno por DNI del perfil
            if perfil.dni:
                alumno = Alumno.objects.filter(documento=perfil.dni).first()
                if alumno:
                    fallback = (
                        alumno.padre_email or alumno.madre_email
                        or alumno.tutor_email or alumno.email
                    )
                    if fallback and fallback.strip():
                        emails.add(fallback.strip().lower())

    logger.info(
        f"Consulta a DB: {len(emails)} emails válidos encontrados "
        f"de {total_padres} perfiles de padre."
    )

    return {
        "emails": list(emails),
        "total_padres": total_padres,
    }


def enviar_emails_masivos(
    destinatarios,
    asunto,
    mensaje_texto,
    mensaje_html=None,
    batch_size=50,
    delay=10,
):
    """
    Envía emails en tandas para evitar bloqueos de Gmail.

    Args:
        destinatarios: Lista de direcciones de email.
        asunto: Asunto del email.
        mensaje_texto: Cuerpo del email en texto plano.
        mensaje_html: (Opcional) Cuerpo del email en HTML.
        batch_size: Cantidad de emails por tanda (default: 50).
        delay: Segundos de pausa entre tandas (default: 10).

    Returns:
        dict con claves:
            - "enviados": int — cantidad de emails enviados con éxito.
            - "fallidos": list — lista de dicts {"email": str, "error": str}.
            - "total": int — total de destinatarios.
    """
    enviados = 0
    fallidos = []
    total = len(destinatarios)

    # Dividir en tandas
    tandas = [
        destinatarios[i : i + batch_size]
        for i in range(0, total, batch_size)
    ]

    total_tandas = len(tandas)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)

    logger.info(
        f"Iniciando envío masivo: {total} destinatarios, "
        f"{total_tandas} tandas de hasta {batch_size}"
    )

    for idx, tanda in enumerate(tandas, start=1):
        logger.info(f"Procesando tanda {idx}/{total_tandas} ({len(tanda)} emails)...")

        for email_dest in tanda:
            try:
                send_mail(
                    subject=asunto,
                    message=mensaje_texto,
                    from_email=from_email,
                    recipient_list=[email_dest],
                    html_message=mensaje_html,
                    fail_silently=False,
                )
                enviados += 1
                logger.debug(f"  ✓ Enviado a {email_dest}")

            except Exception as e:
                error_msg = str(e)
                fallidos.append({"email": email_dest, "error": error_msg})
                logger.error(f"  ✗ Error enviando a {email_dest}: {error_msg}")

        # Pausa entre tandas (no pausar después de la última)
        if idx < total_tandas:
            logger.info(f"  Pausa de {delay}s antes de la siguiente tanda...")
            time.sleep(delay)

    logger.info(
        f"Envío masivo finalizado: {enviados}/{total} enviados, "
        f"{len(fallidos)} fallidos"
    )

    return {
        "enviados": enviados,
        "fallidos": fallidos,
        "total": total,
    }


def enviar_emails_masivos_async(
    destinatarios,
    asunto,
    mensaje_texto,
    mensaje_html=None,
    batch_size=50,
    delay=10,
    total_padres_db=0,
):
    """
    Lanza el envío masivo en un hilo separado (daemon) para no bloquear
    el servidor de Railway. El hilo ejecuta enviar_emails_masivos() y
    loguea el resultado final.

    Args:
        destinatarios: Lista de emails.
        asunto: Asunto del email.
        mensaje_texto: Cuerpo en texto plano.
        mensaje_html: (Opcional) Cuerpo en HTML.
        batch_size: Emails por tanda.
        delay: Pausa entre tandas en segundos.
        total_padres_db: Total de padres encontrados en la DB (para el log).

    Returns:
        None (el resultado se loguea desde el hilo).
    """
    def _worker():
        try:
            resultado = enviar_emails_masivos(
                destinatarios=destinatarios,
                asunto=asunto,
                mensaje_texto=mensaje_texto,
                mensaje_html=mensaje_html,
                batch_size=batch_size,
                delay=delay,
            )
            # Log de producción requerido
            logger.info(
                f"Se enviaron {resultado['enviados']} mails de un total de "
                f"{total_padres_db} padres encontrados en la DB"
            )
            if resultado['fallidos']:
                logger.warning(
                    f"Emails fallidos ({len(resultado['fallidos'])}): "
                    f"{[f['email'] for f in resultado['fallidos']]}"
                )
        except Exception as e:
            logger.critical(f"Error fatal en hilo de envío masivo: {e}", exc_info=True)

    hilo = threading.Thread(target=_worker, daemon=True)
    hilo.start()

    logger.info(
        f"Hilo de envío masivo iniciado: {len(destinatarios)} emails en background"
    )
