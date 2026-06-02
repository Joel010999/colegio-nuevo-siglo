import os
import django
import pandas as pd
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_ns.settings')
django.setup()

from portal.models import Alumno, ConceptoDeuda, RegistroDeuda, PerfilUsuario, ConfiguracionSistema
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

def run():
    file_path = "deudasulti.xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ ERROR: No se encontró el archivo {file_path}")
        return

    print("📥 Leyendo Excel de producción...")
    df = pd.read_excel(file_path)
    
    config = ConfiguracionSistema.get_config()
    hashed_pwd = make_password(config.password_default)
    
    try:
        idx_saldo = list(df.columns).index('Saldo_Moroso')
        conceptos_cols = list(df.columns)[idx_saldo + 1:]
    except ValueError:
        print("❌ ERROR: No se encontró la columna 'Saldo_Moroso'.")
        return

    print("⚙️ Creando conceptos de deuda...")
    conceptos_map = {}
    for col_order, col_name in enumerate(conceptos_cols):
        c_nombre = str(col_name).strip()
        c_codigo = (c_nombre[:10] + c_nombre[-10:]).upper().replace(' ', '_') if len(c_nombre) > 20 else c_nombre.upper().replace(' ', '_')
        concepto, _ = ConceptoDeuda.objects.get_or_create(codigo=c_codigo, defaults={'nombre': c_nombre, 'orden': col_order})
        conceptos_map[col_name] = concepto

    print(f"👥 Procesando {len(df)} alumnos...")
    
    for index, row in df.iterrows():
        try:
            dni = int(row['Documento'])
        except:
            continue
            
        apellido = str(row.get('Apellido', '')).strip()
        nombres = str(row.get('Nombres', '')).strip()
        nivel = str(row.get('Niv', '')).strip()
        curso = str(row.get('Cur', '')).strip()
        division = str(row.get('Div', '')).strip()
        
        if nivel == 'nan': nivel = ''
        if curso == 'nan': curso = ''
        if division == 'nan': division = ''
        
        familia = row.get('Familia', 0)
        if pd.isna(familia): familia = 0
        
        alumno, _ = Alumno.objects.get_or_create(
            documento=dni,
            defaults={'apellido': apellido, 'nombres': nombres, 'nivel': nivel, 'curso': curso, 'division': division, 'familia': familia}
        )
        
        username = str(dni)
        if not User.objects.filter(username=username).exists():
            user = User.objects.create(username=username, password=hashed_pwd, first_name=nombres, last_name=apellido)
            PerfilUsuario.objects.create(usuario=user, dni=dni, rol='padre', must_change_password=True)

        for col_name in conceptos_cols:
            val = row.get(col_name)
            if pd.isna(val) or str(val).strip() == '':
                continue
                
            val_str = str(val).lower().strip()
            concepto = conceptos_map[col_name]
            
            if RegistroDeuda.objects.filter(alumno=alumno, concepto=concepto).exists():
                continue
            
            if 'pagad' in val_str:
                RegistroDeuda.objects.create(alumno=alumno, concepto=concepto, monto=0, estado='pagado')
            else:
                try:
                    monto = Decimal(str(val).replace(',', '.').strip())
                    if monto > 0:
                        RegistroDeuda.objects.create(alumno=alumno, concepto=concepto, monto=monto, estado='pendiente')
                except:
                    pass

    print("✅ ¡ÉXITO! Base de datos local idéntica a Producción.")

if __name__ == '__main__':
    run()
