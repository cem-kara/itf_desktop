import os

files = [
    'ui/components/base_table_model.py',
    'ui/components/drive_upload_worker.py',
    'tests/services/__init__.py',
    'tests/services/test_bakim_service.py',
    'core/services/__init__.py',
    'core/services/bakim_service.py',
    'core/services/ariza_service.py',
    'core/services/izin_service.py',
    'core/services/kalibrasyon_service.py',
    'core/services/personel_service.py',
]

fixed = 0
for f in files:
    if os.path.exists(f):
        with open(f, 'rb') as fp:
            content = fp.read()
        
        if b'\r\n' in content:
            fixed_content = content.replace(b'\r\n', b'\n')
            with open(f, 'wb') as fp:
                fp.write(fixed_content)
            print(f'✓ Düzeltildi: {f}')
            fixed += 1
        else:
            print(f'- Zaten LF: {f}')
    else:
        print(f'✗ Bulunamadı: {f}')

print(f'\nToplam düzeltilen: {fixed} dosya')
