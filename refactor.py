import os, re
import glob

regex_assign = re.compile(r'config\.state\[[\'"]([a-zA-Z0-9_]+)[\'"]\]\s*=\s*(.+)')
regex_get = re.compile(r'config\.state\[[\'"]([a-zA-Z0-9_]+)[\'"]\]')

for root, _, files in os.walk('c:/Users/jose8/OneDrive/Documents/MãosAObra/Hand'):
    for f in files:
        if f.endswith('.py') and f != 'state.py' and f != 'config.py':
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            changed = False
            for i, line in enumerate(lines):
                if 'config.state[' in line:
                    # Replace assignment
                    new_line = regex_assign.sub(r'config.app_state.set("\1", \2)', line)
                    if new_line != line:
                        lines[i] = new_line
                        changed = True
                    # Replace gets
                    new_line2 = regex_get.sub(r'config.app_state.get("\1")', lines[i])
                    if new_line2 != lines[i]:
                        lines[i] = new_line2
                        changed = True
            if changed:
                with open(path, 'w', encoding='utf-8') as file:
                    file.writelines(lines)
                print(f'Updated {path}')
