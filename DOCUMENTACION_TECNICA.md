# 🎓 Documentación Técnica - Portal Colegio Nuevo Siglo

> **Sistema de Gestión de Deudas y Pagos para Padres/Tutores**  
> Versión: 1.0  
> Última actualización: Enero 2026

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Base de Datos](#base-de-datos)
4. [Arquitectura del Sistema](#arquitectura-del-sistema)
5. [Protocolos de Comunicación](#protocolos-de-comunicación)
6. [Módulos Funcionales](#módulos-funcionales)
7. [Seguridad](#seguridad)
8. [Estructura del Proyecto](#estructura-del-proyecto)
9. [Flujos de Datos](#flujos-de-datos)

---

## Resumen Ejecutivo

El **Portal Colegio Nuevo Siglo** es una aplicación web desarrollada para la gestión integral de deudas estudiantiles y pagos. Permite a los padres/tutores consultar el estado de cuenta de sus hijos y enviar comprobantes de pago, mientras que los administradores pueden verificar pagos, gestionar usuarios y enviar comunicaciones masivas.

### Objetivos del Sistema

- ✅ Centralizar la información de deudas de alumnos
- ✅ Facilitar el proceso de pago y verificación
- ✅ Automatizar la comunicación con padres morosos
- ✅ Mantener un registro de auditoría completo
- ✅ Importar datos desde archivos Excel existentes

---

## Stack Tecnológico

### Tecnologías Principales

| Componente | Tecnología | Versión | Descripción |
|------------|------------|---------|-------------|
| **Framework Backend** | Django | 6.0.1 | Framework web de alto nivel para Python |
| **Lenguaje** | Python | 3.x | Lenguaje de programación principal |
| **Base de Datos** | SQLite3 | - | Base de datos relacional embebida |
| **Frontend** | HTML5, CSS3, JavaScript | - | Tecnologías web estándar |
| **Motor de Templates** | Django Template Engine | - | Sistema de plantillas de Django |
| **Servidor (Desarrollo)** | Django Dev Server | WSGI | Servidor de desarrollo integrado |

### ¿Por qué Django?

- 🔒 **Seguridad incorporada**: Protección contra CSRF, XSS, SQL Injection
- 🚀 **Desarrollo rápido**: ORM potente, sistema de administración automático
- 📦 **Baterías incluidas**: Autenticación, sesiones, email, etc.
- 🐍 **Python**: Lenguaje versátil y fácil de mantener
- 📚 **Documentación extensa**: Gran comunidad y soporte

---

## Base de Datos

### Motor: SQLite3

SQLite es una base de datos relacional embebida que almacena toda la información en un único archivo (`db.sqlite3`).

#### Ventajas para este proyecto:

| Característica | Beneficio |
|----------------|-----------|
| **Sin servidor** | No requiere instalación ni configuración de servidor de BD |
| **Portable** | Un solo archivo, fácil de respaldar y migrar |
| **Transacciones ACID** | Garantiza integridad de datos |
| **Cero configuración** | Funciona inmediatamente |
| **Ideal para escala media** | Perfecto para cientos/miles de usuarios |

### Modelo de Datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DIAGRAMA ENTIDAD-RELACIÓN                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐         ┌──────────────────┐                   │
│  │   ConceptoDeuda  │         │      Alumno      │                   │
│  ├──────────────────┤         ├──────────────────┤                   │
│  │ codigo (PK)      │         │ documento (PK)   │                   │
│  │ nombre           │         │ apellido         │                   │
│  │ orden            │         │ nombres          │                   │
│  └────────┬─────────┘         │ curso            │                   │
│           │                   │ padre_dni        │                   │
│           │ 1                 │ madre_dni        │                   │
│           │                   │ tutor_dni        │                   │
│           │                   │ ...emails...     │                   │
│           ▼ N                 └────────┬─────────┘                   │
│  ┌──────────────────┐                  │                             │
│  │  RegistroDeuda   │◄─────────────────┘                             │
│  ├──────────────────┤         1       N                              │
│  │ id (PK)          │                                                │
│  │ alumno (FK)      │         ┌──────────────────┐                   │
│  │ concepto (FK)    │         │       Pago       │                   │
│  │ monto            │────────►├──────────────────┤                   │
│  │ estado           │  1   N  │ numero_operacion │                   │
│  │ periodo          │         │ deuda (FK)       │                   │
│  └──────────────────┘         │ monto_pagado     │                   │
│                               │ comprobante      │                   │
│                               │ estado           │                   │
│  ┌──────────────────┐         └──────────────────┘                   │
│  │  PerfilUsuario   │                                                │
│  ├──────────────────┤         ┌──────────────────┐                   │
│  │ usuario (FK)     │         │RegistroAuditoria │                   │
│  │ dni              │         ├──────────────────┤                   │
│  │ rol              │         │ usuario (FK)     │                   │
│  │ must_change_pwd  │         │ accion           │                   │
│  └──────────────────┘         │ detalles         │                   │
│                               │ ip_address       │                   │
│  ┌──────────────────┐         │ timestamp        │                   │
│  │ConfiguracionSist.│         └──────────────────┘                   │
│  ├──────────────────┤                                                │
│  │ alias_transfer.  │  (Singleton - Solo 1 registro)                 │
│  │ cbu              │                                                │
│  │ password_default │                                                │
│  └──────────────────┘                                                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Descripción de Tablas

| Modelo | Descripción | Registros Típicos |
|--------|-------------|-------------------|
| **Alumno** | Datos completos del estudiante y sus responsables (padre, madre, tutor) | ~500-2000 |
| **RegistroDeuda** | Deudas individuales (matrícula, cuotas, materiales) | ~5000-20000 |
| **ConceptoDeuda** | Catálogo de tipos de deuda | ~10-20 |
| **Pago** | Comprobantes de pago enviados | Variable |
| **PerfilUsuario** | Extensión del usuario Django con rol y DNI | ~500-2000 |
| **ConfiguracionSistema** | Configuración global (CBU, alias, contraseña default) | 1 (singleton) |
| **RegistroAuditoria** | Log de acciones del sistema | Ilimitado |

---

## Arquitectura del Sistema

### Patrón MTV (Model-Template-View)

Django utiliza el patrón MTV, una variación del clásico MVC:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FLUJO DE PETICIÓN HTTP                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│    CLIENTE (Navegador)                                                │
│         │                                                             │
│         ▼ HTTP Request (GET/POST)                                     │
│    ┌─────────────────────────────────────────────────────────────┐   │
│    │                     MIDDLEWARE                               │   │
│    │  • SecurityMiddleware (headers de seguridad)                 │   │
│    │  • SessionMiddleware (manejo de sesiones)                    │   │
│    │  • CsrfViewMiddleware (protección CSRF)                      │   │
│    │  • AuthenticationMiddleware (usuario autenticado)            │   │
│    └─────────────────────────────────────────────────────────────┘   │
│         │                                                             │
│         ▼                                                             │
│    ┌─────────────────────────────────────────────────────────────┐   │
│    │                   URL DISPATCHER (urls.py)                   │   │
│    │  Mapea URLs a funciones de vista                             │   │
│    │  Ejemplo: /admin-panel/pagos/ → admin_pagos()                │   │
│    └─────────────────────────────────────────────────────────────┘   │
│         │                                                             │
│         ▼                                                             │
│    ┌─────────────────────────────────────────────────────────────┐   │
│    │                      VIEW (views.py)                         │   │
│    │  • Recibe la petición HTTP                                   │   │
│    │  • Procesa lógica de negocio                                 │   │
│    │  • Interactúa con modelos (base de datos)                    │   │
│    │  • Prepara contexto para el template                         │   │
│    └─────────────────────────────────────────────────────────────┘   │
│         │                           │                                 │
│         ▼                           ▼                                 │
│    ┌───────────────┐    ┌────────────────────────────────────────┐   │
│    │ MODEL (ORM)   │    │          TEMPLATE (.html)              │   │
│    │               │    │  • Recibe contexto de la vista         │   │
│    │ • Alumno      │    │  • Renderiza HTML dinámico             │   │
│    │ • Deuda       │    │  • Usa variables {{ variable }}        │   │
│    │ • Pago        │    │  • Lógica simple {% if %} {% for %}    │   │
│    │ • Usuario     │    └────────────────────────────────────────┘   │
│    └───────────────┘                │                                 │
│         │                           │                                 │
│         ▼                           ▼                                 │
│    ┌───────────────┐    ┌────────────────────────────────────────┐   │
│    │   SQLite3     │    │              HTTP Response             │   │
│    │  (db.sqlite3) │    │  (HTML renderizado al navegador)       │   │
│    └───────────────┘    └────────────────────────────────────────┘   │
│                                     │                                 │
│                                     ▼                                 │
│                              CLIENTE (Navegador)                      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Protocolos de Comunicación

### Protocolos Utilizados

| Protocolo | Puerto | Uso en el Sistema |
|-----------|--------|-------------------|
| **HTTP** | 80 (dev: 8000) | Comunicación web cliente-servidor |
| **HTTPS** | 443 | Comunicación segura (producción) |
| **SMTP/TLS** | 587 | Envío de emails vía Gmail |
| **WSGI** | - | Interfaz servidor web ↔ Django |

### Configuración de Email

```python
# Servidor SMTP de Gmail
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True  # Conexión cifrada
```

**Funcionalidades de email:**
- 📧 Envío masivo a padres morosos
- 📧 Notificaciones de sistema
- 📧 Alertas de pagos

---

## Módulos Funcionales

### Vista General de Módulos

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MÓDULOS DEL SISTEMA                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │                    AUTENTICACIÓN                            │    │
│   │  • Login con DNI y contraseña                               │    │
│   │  • Cambio obligatorio de contraseña en primer ingreso       │    │
│   │  • Logout seguro                                            │    │
│   │  • Roles: Administrador / Padre-Responsable                 │    │
│   └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│   ┌───────────────────────┐     ┌───────────────────────────────┐    │
│   │    PORTAL PADRES      │     │     PANEL ADMINISTRATIVO      │    │
│   ├───────────────────────┤     ├───────────────────────────────┤    │
│   │ • Ver deudas de hijos │     │ • Gestión de Deudas           │    │
│   │ • Enviar comprobantes │     │ • Verificación de Pagos       │    │
│   │ • Ver historial pagos │     │ • Gestión de Usuarios         │    │
│   │ • Descargar recibos   │     │ • Envío de Avisos Masivos     │    │
│   └───────────────────────┘     │ • Importación Excel           │    │
│                                 │ • Exportación de Datos        │    │
│   ┌───────────────────────┐     │ • Configuración del Sistema   │    │
│   │   CONSULTA PÚBLICA    │     │ • Registro de Auditoría       │    │
│   ├───────────────────────┤     └───────────────────────────────┘    │
│   │ • Consulta sin login  │                                          │
│   │ • Búsqueda por DNI    │                                          │
│   └───────────────────────┘                                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Detalle de Funcionalidades

#### 🔐 Autenticación
- Login mediante DNI (username) y contraseña
- Primer login obliga cambio de contraseña
- Validación de contraseña: 8-20 caracteres, mayúsculas, minúsculas y números
- Sesiones seguras con timeout

#### 👨‍👩‍👧 Portal de Padres
- Vista de todos los hijos asociados al DNI del padre
- Listado de deudas por hijo con estados (Pendiente, Verificado, etc.)
- Envío de comprobantes de pago (imágenes)
- Historial de pagos realizados

#### 🔍 Consulta Pública
- Acceso sin autenticación
- Búsqueda de saldo por DNI del alumno
- Solo muestra información básica de deuda

#### ⚙️ Panel Administrativo

| Sección | Funcionalidad |
|---------|---------------|
| **Deudas** | Ver todas las deudas, filtrar, totales |
| **Pagos** | Verificar comprobantes, aprobar/rechazar |
| **Usuarios** | Ver usuarios por curso, reset contraseñas |
| **Avisos** | Enviar emails masivos a morosos |
| **Importar** | Cargar datos desde Excel |
| **Exportar** | Descargar reportes |
| **Configuración** | CBU, alias, contraseña default |
| **Auditoría** | Log de acciones del sistema |

---

## Seguridad

### Medidas de Seguridad Implementadas

| Capa | Protección | Descripción |
|------|------------|-------------|
| **Transporte** | TLS/HTTPS | Cifrado de datos en tránsito |
| **Aplicación** | CSRF Protection | Token en formularios previene ataques CSRF |
| **Aplicación** | XSS Prevention | Escape automático en templates |
| **Aplicación** | SQL Injection | ORM previene inyección SQL |
| **Aplicación** | Clickjacking | X-Frame-Options header |
| **Autenticación** | Sesiones seguras | Cookies httponly, expiración |
| **Autenticación** | Validación passwords | 4 validadores de complejidad |
| **Autorización** | Roles | Admin vs Padre/Responsable |
| **Auditoría** | Logging | Registro de acciones con IP |

### Middleware de Seguridad

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',      # Headers de seguridad
    'django.contrib.sessions.middleware.SessionMiddleware', # Sesiones
    'django.middleware.csrf.CsrfViewMiddleware',          # Protección CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Auth
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # Clickjacking
]
```

### Validación de Contraseñas

```python
AUTH_PASSWORD_VALIDATORS = [
    UserAttributeSimilarityValidator,  # No similar al username
    MinimumLengthValidator,            # Longitud mínima
    CommonPasswordValidator,           # No contraseñas comunes
    NumericPasswordValidator,          # No solo números
]
```

---

## Estructura del Proyecto

```
ColegioNuevoSiglo/
│
├── 📁 colegio_ns/                 # Configuración del proyecto Django
│   ├── __init__.py
│   ├── settings.py                # Configuración principal
│   ├── urls.py                    # URLs raíz del proyecto
│   ├── wsgi.py                    # Punto de entrada WSGI
│   └── asgi.py                    # Punto de entrada ASGI
│
├── 📁 portal/                     # Aplicación principal
│   ├── 📁 management/
│   │   └── 📁 commands/
│   │       └── importar_datos.py  # Comando de importación Excel
│   │
│   ├── 📁 templates/
│   │   └── 📁 portal/
│   │       ├── 📁 admin/          # Templates del panel admin
│   │       │   ├── base_admin.html
│   │       │   ├── deudas.html
│   │       │   ├── pagos.html
│   │       │   ├── usuarios.html
│   │       │   └── ...
│   │       ├── login.html
│   │       ├── portal_padre.html
│   │       └── ...
│   │
│   ├── 📁 static/                 # Archivos estáticos (CSS, JS, imágenes)
│   │
│   ├── __init__.py
│   ├── admin.py                   # Configuración admin Django
│   ├── apps.py                    # Configuración de la app
│   ├── models.py                  # Modelos de datos
│   ├── views.py                   # Vistas/controladores
│   └── urls.py                    # URLs de la aplicación
│
├── 📁 media/                      # Archivos subidos
│   └── 📁 comprobantes/           # Comprobantes de pago
│
├── 📄 db.sqlite3                  # Base de datos SQLite
├── 📄 manage.py                   # Script de administración Django
├── 📄 alumnos.xlsx                # Datos de alumnos (importación)
└── 📄 deudas.xlsx                 # Datos de deudas (importación)
```

---

## Flujos de Datos

### Flujo de Importación de Datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IMPORTACIÓN DESDE EXCEL                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐   │
│   │ alumnos.xlsx│     │  Comando Django │     │    Base Datos    │   │
│   │             │────▶│ importar_datos  │────▶│                  │   │
│   │ • DNI       │     │                 │     │  • Alumno        │   │
│   │ • Nombre    │     │ • Lee Excel     │     │  • PerfilUsuario │   │
│   │ • Curso     │     │ • Valida datos  │     │  • User (Django) │   │
│   │ • Padres    │     │ • Crea usuarios │     │                  │   │
│   └─────────────┘     └─────────────────┘     └──────────────────┘   │
│                                                                       │
│   ┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐   │
│   │ deudas.xlsx │     │  Panel Admin    │     │    Base Datos    │   │
│   │             │────▶│  (Importar)     │────▶│                  │   │
│   │ • DNI       │     │                 │     │ • RegistroDeuda  │   │
│   │ • Concepto  │     │ • Subir archivo │     │ • ConceptoDeuda  │   │
│   │ • Monto     │     │ • Procesar      │     │                  │   │
│   │ • Periodo   │     │ • Notificar     │     │                  │   │
│   └─────────────┘     └─────────────────┘     └──────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Flujo de Pago

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FLUJO DE PAGO COMPLETO                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   PADRE/TUTOR                           ADMINISTRADOR                 │
│       │                                       │                       │
│       ▼                                       │                       │
│   ┌─────────────────┐                         │                       │
│   │  Ver deudas     │                         │                       │
│   │  pendientes     │                         │                       │
│   └────────┬────────┘                         │                       │
│            │                                  │                       │
│            ▼                                  │                       │
│   ┌─────────────────┐                         │                       │
│   │ Seleccionar     │                         │                       │
│   │ deuda a pagar   │                         │                       │
│   └────────┬────────┘                         │                       │
│            │                                  │                       │
│            ▼                                  │                       │
│   ┌─────────────────┐                         │                       │
│   │ Subir imagen    │                         │                       │
│   │ comprobante     │                         │                       │
│   └────────┬────────┘                         │                       │
│            │                                  │                       │
│            ▼                                  │                       │
│   ┌─────────────────┐                         │                       │
│   │ Estado cambia a │                         │                       │
│   │ "Pendiente      │                         │                       │
│   │  Verificación"  │                         │                       │
│   └────────┬────────┘                         │                       │
│            │                                  │                       │
│            │         Notificación             │                       │
│            └─────────────────────────────────▶│                       │
│                                               ▼                       │
│                                   ┌─────────────────┐                 │
│                                   │ Ver pagos       │                 │
│                                   │ pendientes      │                 │
│                                   └────────┬────────┘                 │
│                                            │                          │
│                                            ▼                          │
│                                   ┌─────────────────┐                 │
│                                   │ Revisar         │                 │
│                                   │ comprobante     │                 │
│                                   └────────┬────────┘                 │
│                                            │                          │
│                                    ┌───────┴───────┐                  │
│                                    ▼               ▼                  │
│                           ┌──────────────┐ ┌──────────────┐           │
│                           │   APROBAR    │ │   RECHAZAR   │           │
│                           └──────┬───────┘ └──────────────┘           │
│                                  │                                    │
│                                  ▼                                    │
│                          ┌─────────────────┐                          │
│                          │ Estado cambia a │                          │
│                          │ "Verificado"    │                          │
│                          └─────────────────┘                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Configuración Regional

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| **LANGUAGE_CODE** | `es-ar` | Español Argentina |
| **TIME_ZONE** | `America/Argentina/Cordoba` | Zona horaria local |
| **USE_I18N** | `True` | Internacionalización activa |
| **USE_TZ** | `True` | Soporte timezone-aware |

---

## Escalabilidad Futura

### Migración a Producción

Para un despliegue en producción, se recomienda:

| Componente | Desarrollo | Producción |
|------------|------------|------------|
| **Base de Datos** | SQLite | PostgreSQL / MySQL |
| **Servidor Web** | Django Dev Server | Nginx + Gunicorn |
| **Archivos Estáticos** | Local | CDN / S3 |
| **Email** | Gmail SMTP | SendGrid / SES |
| **Hosting** | Local | AWS / DigitalOcean / Railway |

---

## Contacto y Soporte

**Desarrollado por:** Render Byte  
**Proyecto:** Portal Colegio Nuevo Siglo  
**Año:** 2026

---

> 📝 **Nota:** Esta documentación está destinada a propósitos de presentación y referencia técnica del proyecto.
