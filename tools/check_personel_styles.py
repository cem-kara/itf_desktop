from pathlib import Path
import re
import json
import sys

base=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base))
pm_dir=base/'ui'/'pages'/'personel'
used=set()
used_styles=set()
for p in sorted(pm for pm in pm_dir.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    used.update(re.findall(r'S\["([^\"]+)"\]', txt))
    used_styles.update(re.findall(r'STYLES\["([^\"]+)"\]', txt))

# Import ThemeManager dynamically
try:
    from ui.theme_manager import ThemeManager
    available=set(ThemeManager.get_all_component_styles().keys())
except Exception as e:
    available=set()
    print('ERROR importing ThemeManager:', e)

out={
    'used_keys': sorted(used),
    'used_styles_keys': sorted(used_styles),
    'available_keys': sorted(available),
    'missing_S_keys': sorted(set(used)-available),
    'missing_STYLES_keys': sorted(set(used_styles)-available)
}
print(json.dumps(out, indent=2, ensure_ascii=False))
