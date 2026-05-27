#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6 Assembly v5 - 最可靠方案：所有部分从独立文件读取
Part1: V5数据方法 (行1-1964) - 从V5源码提取
Part2: 新generate_html_report - 从_gen_html.py读取
Part3: LLM方法 - 从_gen_llm_v6.py读取
Part4: validate+main - 内嵌(简单代码，无多行字符串)
"""
import ast, sys, os

V5_PATH = 'c:/Users/21471/WorkBuddy/gold/src/report/gold_report_generator_v5.py'
V6_PATH = 'c:/Users/21471/WorkBuddy/gold/src/report/gold_report_generator_v6.py'
GEN_HTML = 'c:/Users/21471/WorkBuddy/gold/_gen_html_cn.py'
GEN_LLM  = 'c:/Users/21471/WorkBuddy/gold/_gen_llm_v6.py'

NL = chr(10)
print('=== V6 Assembly v5 ===')
print()

# ===== Step 1: 提取数据方法 (V5行1-1964) =====
with open(V5_PATH, encoding='utf-8') as f:
    v5_raw = f.read()
v5_lines = v5_raw.split(NL)
if v5_lines[-1] == '':
    v5_lines = v5_lines[:-1]
DATA_END = 1964
data_part = NL.join(v5_lines[:DATA_END])
try:
    ast.parse(data_part)
    print('[1] Data part OK (' + str(len(v5_lines[:DATA_END])) + ' lines)')
except SyntaxError as e:
    print('[FAIL] Data syntax error at line', e.lineno)
    sys.exit(1)

# ===== Step 2: 读取新generate_html_report =====
with open(GEN_HTML, encoding='utf-8') as f:
    gen_raw = f.read()
# 保留4空格类缩进，去掉\r换行符和末尾空白
gen_method = gen_raw.replace('\r', '').rstrip()
try:
    import textwrap
    ast.parse(textwrap.dedent(gen_method))
    print('[2] generate_html_report OK (' + str(gen_method.count(NL)+1) + ' lines)')
except SyntaxError as e:
    print('[FAIL] Gen method error at line', e.lineno, ':', e.msg)
    ml = gen_method.split(NL)
    for i in range(max(0,e.lineno-3), min(len(ml),e.lineno+2)):
        print(' ', i+1, repr(ml[i][:100]))
    sys.exit(1)

# ===== Step 3: 读取LLM方法 =====
with open(GEN_LLM, encoding='utf-8') as f:
    llm_raw = f.read()
# 保留4空格类缩进，去掉\r换行符和末尾空白
llm_methods = llm_raw.replace('\r', '').rstrip()
try:
    import textwrap
    ast.parse(textwrap.dedent(llm_methods))
    print('[3] LLM methods OK (' + str(llm_methods.count(NL)+1) + ' lines)')
except SyntaxError as e:
    print('[FAIL] LLM methods error at line', e.lineno, ':', e.msg)
    ml = llm_methods.split(NL)
    for i in range(max(0,e.lineno-3), min(len(ml),e.lineno+2)):
        print(' ', i+1, repr(ml[i][:100]))
    sys.exit(1)

# ===== Step 4: 类方法save_report + 模块级main (完整入口逻辑) =====
# 注意：save_report必须是类方法，放在LLM方法之后、main之前
class_methods = (
    NL +
    "    def validate_topics(self):" + NL +
    "        for topic in getattr(self, 'FIXED_TOPICS', []):" + NL +
    "            if topic.get('required') and topic['id'] not in self.topic_content:" + NL +
    "                self.topic_content[topic['id']] = self._get_fallback_content(topic['id'])" + NL +
    "        return True" + NL +
    NL +
    "    def save_report(self, filepath=None, use_llm=None, llm_type=None):" + NL +
    "        import os" + NL +
    "        from pathlib import Path" + NL +
    "        use_llm = self.use_llm if use_llm is None else use_llm" + NL +
    "        llm_type = self.llm_type if llm_type is None else llm_type" + NL +
    "        report_dir = Path('reports')" + NL +
    "        report_dir.mkdir(exist_ok=True)" + NL +
    "        if filepath is None:" + NL +
    "            ts = str(getattr(self, 'sge_latest_date', 'unknown')).replace('-','')" + NL +
    "            filepath = report_dir / ('gold_report_' + ts + '_v6.html')" + NL +
    "        html = self.generate_html_report()" + NL +
    "        if not html:" + NL +
    "            print('[ERROR] HTML generation failed')" + NL +
    "            return None" + NL +
    "        with open(filepath, 'w', encoding='utf-8') as f:" + NL +
    "            f.write(html)" + NL +
    "        print('[OK] Report saved:', filepath)" + NL +
    "        return str(filepath)" + NL
)

validate_main = (
    NL +
    class_methods +
    NL +
    NL +
    "def main(use_llm=True, llm_type=None, api_key=None):" + NL +
    "    try:" + NL +
    "        llm_type = llm_type or 'chatanywhere'" + NL +
    "        gen = GoldReportGeneratorV6(llm_type=llm_type, use_llm=use_llm, api_key=api_key)" + NL +
    "        gen.fetch_all_data()" + NL +
    "        gen.save_report()" + NL +
    "        return gen" + NL +
    "    except Exception as e:" + NL +
    "        print('[ERROR]', str(e))" + NL +
    "        import traceback; traceback.print_exc()" + NL +
    "        return None" + NL +
    NL +
    NL +
    "if __name__ == '__main__':" + NL +
    "    print('=' * 50)" + NL +
    "    print('Gold Report Generator V6')" + NL +
    "    print('=' * 50)" + NL +
    "    main()" + NL
)
try:
    # 包装成class测试
    test_vm = 'class T:' + NL + validate_main
    ast.parse(test_vm)
    print('[4] Validate/Main OK')
except SyntaxError as e:
    print('[FAIL] Validate/Main error at line', e.lineno)
    sys.exit(1)

# ===== Step 5: 组装 =====
parts = [data_part, '', gen_method, '', llm_methods, validate_main]
v6_src = NL.join(parts)

total = v6_src.count(NL) + 1
print()
print('--- Assembly Summary ---')
print('Data methods :', data_part.count(NL)+1, 'lines')
print('HTML report  :', gen_method.count(NL)+1, 'lines')
print('LLM methods  :', llm_methods.count(NL)+1, 'lines')
print('Valid/Main   :', validate_main.count(NL)+1, 'lines')
print('TOTAL        :', total, 'lines')

# ===== Step 6: 最终验证 =====
print()
print('Validating final V6...')
try:
    ast.parse(v6_src)
    print('[OK] V6 SYNTAX VALID!')
except SyntaxError as e:
    print('[FAIL] V6 ERROR at line', e.lineno, ':', e.msg)
    ls = v6_src.split(NL)
    for i in range(max(0, e.lineno-5), min(len(ls), e.lineno+3)):
        marker = '>>>' if i == e.lineno-1 else '   '
        print(marker, i+1, repr(ls[i][:120]))
    sys.exit(1)

# ===== Step 7: 写入 =====
v6_src = v6_src.replace('GoldReportGeneratorV5', 'GoldReportGeneratorV6')
with open(V6_PATH, 'w', encoding='utf-8') as f:
    f.write(v6_src)
print()
print('[SUCCESS] Written to:', V6_PATH)
