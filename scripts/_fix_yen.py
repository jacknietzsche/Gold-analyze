import sys
sys.stdout.reconfigure(encoding='utf-8')
filepath = r'c:\Users\21471\WorkBuddy\gold\src\report\gold_report_generator_v5.py'
with open(filepath, encoding='utf-8') as f:
    content = f.read()
content = content.replace('\u00a5', 'CNY ')  # ¥ -> CNY
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
import ast; ast.parse(content); print("SYNTAX OK")
