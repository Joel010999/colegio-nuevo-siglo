import os
import glob

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content.replace("estado_filter=='pendiente'", "estado_filter == 'pendiente'")
    new_content = new_content.replace("estado_filter=='verificado'", "estado_filter == 'verificado'")
    new_content = new_content.replace("estado_filter=='comprobante_enviado'", "estado_filter == 'comprobante_enviado'")
    new_content = new_content.replace("estado_filter=='pago_verificado'", "estado_filter == 'pago_verificado'")
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {path}')
    else:
        print(f'No changes needed for {path}')

for p in glob.glob('portal/templates/portal/admin/*.html'):
    fix_file(p)
