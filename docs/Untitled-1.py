import os, re

patterns = {
    'RKE_* token':       r'RKE_BG|RKE_TX|RKE_BD|RKE_RED|RKE_AMBER|RKE_GREEN|RKE_BLUE|RKE_CYAN|RKE_PURP',
    'Colors.SUCCESS':    r'Colors\.SUCCESS\b',
    'ComponentStyles.*_BTN': r'ComponentStyles\.(SAVE|CANCEL|EDIT|DANGER|REPORT|PDF|BACK|CALC)_BTN',
}

for label, pat in patterns.items():
    print(f'\n=== {label} ===')
    found = False
    for root, dirs, files in os.walk('ui'):
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            for i, line in enumerate(open(path, encoding='utf-8', errors='ignore'), 1):
                if re.search(pat, line):
                    print(f'  {path}:{i}: {line.rstrip()}')
                    found = True
    if not found:
        print('  (bulunamadı — temiz)')

