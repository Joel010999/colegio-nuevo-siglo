"""
Script de importación de datos desde Excel.
Uso: python manage.py importar_datos
"""
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd
from portal.models import Alumno, ConceptoDeuda, RegistroDeuda


class Command(BaseCommand):
    help = 'Importa datos de alumnos y deudas desde archivos Excel'

    # Mapeo de códigos de concepto a nombres legibles
    CONCEPTOS_MAP = {
        '0': ('Matrícula', 1),
        '1': ('Cuota Marzo', 10),
        '2': ('Cuota Abril', 11),
        '3': ('Cuota Mayo', 12),
        '4': ('Cuota Junio', 13),
        '5': ('Cuota Julio', 14),
        '6': ('Cuota Agosto', 15),
        '7': ('Cuota Septiembre', 16),
        '8': ('Cuota Octubre', 17),
        '9': ('Cuota Noviembre', 18),
        '10': ('Cuota Diciembre', 19),
        '20': ('Material Didáctico', 30),
        '27': ('Matrícula Noviembre Secundario', 5),
        '31': ('Cuota de Admisión', 2),
        '34P': ('Matrícula Nuevos Primaria', 3),
        '34S': ('Matrícula Nuevos Secundaria', 4),
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--alumnos',
            type=str,
            default='alumnos.xlsx',
            help='Ruta al archivo de alumnos (default: alumnos.xlsx)'
        )
        parser.add_argument(
            '--deudas',
            type=str,
            default='deudas.xlsx',
            help='Ruta al archivo de deudas (default: deudas.xlsx)'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina todos los datos existentes antes de importar'
        )

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        alumnos_path = os.path.join(base_dir, options['alumnos'])
        deudas_path = os.path.join(base_dir, options['deudas'])

        if options['limpiar']:
            self.stdout.write('Limpiando datos existentes...')
            RegistroDeuda.objects.all().delete()
            Alumno.objects.all().delete()
            ConceptoDeuda.objects.all().delete()

        # 1. Crear conceptos de deuda
        self.stdout.write('Creando conceptos de deuda...')
        self.crear_conceptos()

        # 2. Importar alumnos
        self.stdout.write(f'Importando alumnos desde {alumnos_path}...')
        self.importar_alumnos(alumnos_path)

        # 3. Importar deudas
        self.stdout.write(f'Importando deudas desde {deudas_path}...')
        self.importar_deudas(deudas_path)

        self.stdout.write(self.style.SUCCESS('¡Importación completada exitosamente!'))

    def crear_conceptos(self):
        """Crea los conceptos de deuda basados en el mapeo"""
        for codigo, (nombre, orden) in self.CONCEPTOS_MAP.items():
            ConceptoDeuda.objects.update_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'orden': orden}
            )
        self.stdout.write(f'  - Creados {len(self.CONCEPTOS_MAP)} conceptos')

    def importar_alumnos(self, filepath):
        """Importa alumnos desde el archivo Excel"""
        df = pd.read_excel(filepath)
        count = 0
        
        for _, row in df.iterrows():
            try:
                documento = int(row.get('Documento', 0))
                if documento <= 0:
                    continue
                    
                Alumno.objects.update_or_create(
                    documento=documento,
                    defaults={
                        'apellido': str(row.get('apellido', '')).strip() if pd.notna(row.get('apellido')) else '',
                        'nombres': str(row.get('nombres', '')).strip() if pd.notna(row.get('nombres')) else '',
                        'fecha_nacimiento': row.get('fechanacimiento') if pd.notna(row.get('fechanacimiento')) else None,
                        'sexo': str(row.get('sexo', '')).strip()[:1] if pd.notna(row.get('sexo')) else '',
                        'direccion': str(row.get('diralu', '')).strip() if pd.notna(row.get('diralu')) else '',
                        'telefono1': str(row.get('tel1alu', '')).strip() if pd.notna(row.get('tel1alu')) else '',
                        'telefono2': str(row.get('tel2alu', '')).strip() if pd.notna(row.get('tel2alu')) else '',
                        'email': str(row.get('mailalu', '')).strip() if pd.notna(row.get('mailalu')) else '',
                        'barrio': str(row.get('BARRIOALU', '')).strip() if pd.notna(row.get('BARRIOALU')) else '',
                        # Padre
                        'padre_nombre': str(row.get('Padre', '')).strip() if pd.notna(row.get('Padre')) else '',
                        'padre_dni': int(row.get('dnip', 0)) if pd.notna(row.get('dnip')) and int(row.get('dnip', 0)) > 0 else None,
                        'padre_direccion': str(row.get('Direccionpadre', '')).strip() if pd.notna(row.get('Direccionpadre')) else '',
                        'padre_telefono1': str(row.get('tel1padre', '')).strip() if pd.notna(row.get('tel1padre')) else '',
                        'padre_telefono2': str(row.get('tel2padre', '')).strip() if pd.notna(row.get('tel2padre')) else '',
                        'padre_email': str(row.get('mailpadre', '')).strip() if pd.notna(row.get('mailpadre')) else '',
                        # Madre
                        'madre_nombre': str(row.get('Madre', '')).strip() if pd.notna(row.get('Madre')) else '',
                        'madre_dni': int(row.get('dnim', 0)) if pd.notna(row.get('dnim')) and int(row.get('dnim', 0)) > 0 else None,
                        'madre_direccion': str(row.get('Direccionmadre', '')).strip() if pd.notna(row.get('Direccionmadre')) else '',
                        'madre_telefono1': str(row.get('tel1madre', '')).strip() if pd.notna(row.get('tel1madre')) else '',
                        'madre_telefono2': str(row.get('tel2madre', '')).strip() if pd.notna(row.get('tel2madre')) else '',
                        'madre_email': str(row.get('mailmadre', '')).strip() if pd.notna(row.get('mailmadre')) else '',
                        # Tutor
                        'tutor_nombre': str(row.get('Tutor', '')).strip() if pd.notna(row.get('Tutor')) else '',
                        'tutor_dni': int(row.get('dnit', 0)) if pd.notna(row.get('dnit')) and int(row.get('dnit', 0)) > 0 else None,
                        'tutor_direccion': str(row.get('direcciontutor', '')).strip() if pd.notna(row.get('direcciontutor')) else '',
                        'tutor_telefono1': str(row.get('tel1tutor', '')).strip() if pd.notna(row.get('tel1tutor')) else '',
                        'tutor_telefono2': str(row.get('tel2tutor', '')).strip() if pd.notna(row.get('tel2tutor')) else '',
                        'tutor_email': str(row.get('mailtutor', '')).strip() if pd.notna(row.get('mailtutor')) else '',
                        # Otros
                        'familia': int(row.get('FAMILIA', 0)) if pd.notna(row.get('FAMILIA')) else 0,
                        'recargo': bool(row.get('RECARGO', False)) if pd.notna(row.get('RECARGO')) else False,
                    }
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Error en fila {_}: {e}'))
                
        self.stdout.write(f'  - Importados {count} alumnos')

    def importar_deudas(self, filepath):
        """Importa deudas desde el archivo Excel"""
        df = pd.read_excel(filepath, sheet_name='Hoja1')
        count = 0
        alumnos_actualizados = 0
        
        # Identificar columnas de conceptos (con formato X_Nombre)
        columnas_conceptos = []
        for col in df.columns:
            if '_' in str(col):
                partes = str(col).split('_', 1)
                if partes[0].replace('P', '').replace('S', '').isdigit() or partes[0].isdigit():
                    columnas_conceptos.append(col)
        
        self.stdout.write(f'  - Columnas de conceptos detectadas: {len(columnas_conceptos)}')
        
        for _, row in df.iterrows():
            try:
                documento = int(row.get('Documento', 0))
                if documento <= 0:
                    continue
                
                # Actualizar o crear alumno con datos de escolaridad del archivo de deudas
                alumno, created = Alumno.objects.update_or_create(
                    documento=documento,
                    defaults={
                        'apellido': str(row.get('Apellido', '')).strip() if pd.notna(row.get('Apellido')) else '',
                        'nombres': str(row.get('Nombres', '')).strip() if pd.notna(row.get('Nombres')) else '',
                        'nivel': str(row.get('Niv', '')).strip() if pd.notna(row.get('Niv')) else '',
                        'curso': str(row.get('Cur', '')).strip() if pd.notna(row.get('Cur')) else '',
                        'division': str(row.get('Div', '')).strip() if pd.notna(row.get('Div')) else '',
                        'saldo_moroso': Decimal(str(row.get('Saldo_Moroso', 0))) if pd.notna(row.get('Saldo_Moroso')) else Decimal('0'),
                    }
                )
                alumnos_actualizados += 1
                
                # Procesar cada columna de concepto
                for col in columnas_conceptos:
                    monto = row.get(col)
                    if pd.isna(monto) or float(monto) <= 0:
                        continue
                    
                    # Extraer código del nombre de columna
                    partes = str(col).split('_', 1)
                    codigo_raw = partes[0]
                    nombre_excel = partes[1] if len(partes) > 1 else codigo_raw
                    
                    # Ajustar código para matrículas nuevos P/S
                    if codigo_raw == '34':
                        if 'P' in nombre_excel.upper():
                            codigo = '34P'
                        elif 'S' in nombre_excel.upper():
                            codigo = '34S'
                        else:
                            codigo = codigo_raw
                    else:
                        codigo = codigo_raw
                    
                    # Obtener o crear concepto
                    concepto, _ = ConceptoDeuda.objects.get_or_create(
                        codigo=codigo,
                        defaults={
                            'nombre': self.CONCEPTOS_MAP.get(codigo, (nombre_excel.replace('_', ' ').title(), 100))[0],
                            'orden': self.CONCEPTOS_MAP.get(codigo, (nombre_excel, 100))[1]
                        }
                    )
                    
                    # Crear registro de deuda
                    RegistroDeuda.objects.update_or_create(
                        alumno=alumno,
                        concepto=concepto,
                        defaults={
                            'monto': Decimal(str(monto)),
                            'estado': 'pendiente',
                        }
                    )
                    count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Error en fila {_}: {e}'))
        
        self.stdout.write(f'  - Actualizados {alumnos_actualizados} alumnos')
        self.stdout.write(f'  - Creados {count} registros de deuda')
