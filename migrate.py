import os
import re

print('Starting migration script...')

blue_theme_path = r'd:\Projects\Project-AKI\desktop\themes\blue_theme.py'
aki_theme_path = r'd:\Projects\Project-AKI\desktop\themes\aki_theme.py'

if os.path.exists(blue_theme_path):
    with open(blue_theme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Modify BlueTheme to AkiTheme
    content = content.replace('BlueTheme', 'AkiTheme')
    content = content.replace('blue_theme', 'aki_theme')
    
    # Update colors
    content = re.sub(r'PRIMARY: str = .*', 'PRIMARY: str = "#A259FF"', content)
    content = re.sub(r'SECONDARY: str = .*', 'SECONDARY: str = "#A259FF"', content)
    content = re.sub(r'ACCENT: str = .*', 'ACCENT: str = "#A259FF"', content)
    
    content = re.sub(r'SURFACE_BASE: str = .*', 'SURFACE_BASE: str = "#0B0B10"', content)
    content = re.sub(r'SURFACE_GLASS: str = .*', 'SURFACE_GLASS: str = "#13131A"', content)
    content = re.sub(r'SURFACE_CARD: str = .*', 'SURFACE_CARD: str = "#13131A"', content)
    
    content = re.sub(r'TEXT_PRIMARY: str = .*', 'TEXT_PRIMARY: str = "#ECECF1"', content)
    content = re.sub(r'TEXT_SECONDARY: str = .*', 'TEXT_SECONDARY: str = "#9A9AA5"', content)
    content = re.sub(r'TEXT_MUTED: str = .*', 'TEXT_MUTED: str = "#9A9AA5"', content)
    
    content = re.sub(r'BORDER_LIGHT: str = .*', 'BORDER_LIGHT: str = "#26262E"', content)
    content = re.sub(r'BORDER_ACCENT: str = .*', 'BORDER_ACCENT: str = "#A259FF"', content)
    
    content = re.sub(r'RADIUS_SM: int = .*', 'RADIUS_SM: int = 6', content)
    content = re.sub(r'RADIUS_MD: int = .*', 'RADIUS_MD: int = 6', content)
    content = re.sub(r'RADIUS_LG: int = .*', 'RADIUS_LG: int = 8', content)
    content = re.sub(r'RADIUS_XL: int = .*', 'RADIUS_XL: int = 8', content)
    
    # Disable rgba method by just returning hex
    content = re.sub(
        r'def _rgba\(self, hex_color: str, alpha: float\) -> str:.*?(?=    # -)',
        'def _rgba(self, hex_color: str, alpha: float) -> str:\n        return hex_color\n\n',
        content, flags=re.DOTALL
    )
    
    with open(aki_theme_path, 'w', encoding='utf-8') as f:
        f.write(content)

# Update imports globally
for root, dirs, files in os.walk(r'd:\Projects\Project-AKI'):
    for file in files:
        if file.endswith(('.py', '.css', '.html', '.qss')):
            path = os.path.join(root, file)
            if 'migrate.py' in path:
                continue
            with open(path, 'r', encoding='utf-8') as f:
                original = f.read()
            
            modified = original.replace('BlueTheme', 'AkiTheme')
            modified = modified.replace('blue_theme', 'aki_theme')
            
            # For CSS files, replace old hex colors
            if file.endswith('.css') or file.endswith('.html'):
                modified = re.sub(r'(?i)#2E7CFF', '#A259FF', modified)
                modified = re.sub(r'(?i)#7C4DFF', '#A259FF', modified)
                modified = re.sub(r'(?i)#00E5FF', '#A259FF', modified)
                modified = re.sub(r'(?i)#0B0E17', '#0B0B10', modified)
                modified = re.sub(r'(?i)rgba\(\s*24\s*,\s*30\s*,\s*48\s*,\s*0\.62\s*\)', '#13131A', modified)
                modified = re.sub(r'(?i)#141a29', '#13131A', modified)
                modified = re.sub(r'(?i)#F5F7FF', '#ECECF1', modified)
                modified = re.sub(r'(?i)#A9B3D0', '#9A9AA5', modified)
                modified = re.sub(r'(?i)#6B7591', '#9A9AA5', modified)
                modified = re.sub(r'(?i)rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.08\s*\)', '#26262E', modified)
                modified = re.sub(r'(?i)rgba\(\s*46\s*,\s*124\s*,\s*255\s*,\s*0\.55\s*\)', '#A259FF', modified)
                
                # Remove box-shadow and backdrop-filter
                modified = re.sub(r'(?i)box-shadow:[^;]+;', '', modified)
                modified = re.sub(r'(?i)backdrop-filter:[^;]+;', '', modified)

            if modified != original:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(modified)
                print(f'Updated {path}')
