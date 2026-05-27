#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""今日黄金报告生成脚本（2026-05-08）"""
import sys, os, warnings, traceback, io
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 设置API Keys
os.environ['FRED_API_KEY'] = 'YOUR_FRED_API_KEY'
os.environ['SILICONFLOW_API_KEY'] = 'YOUR_SILICONFLOW_API_KEY"
os.environ['CHERRY_API_KEY'] = 'YOUR_CHERRY_API_KEY"

# 关键：绕过Windows代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
# 强制移除可能残留的代理设置
for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    if k in os.environ:
        del os.environ[k]

# Virtual tqdm
class VirtualTqdmModule:
    @staticmethod
    def tqdm(iterable=None, **kwargs):
        class V:
            def __init__(s, it=None, **kw):
                s.iterable = it; s.n = 0; s.total = len(it) if it else 100
            def update(s, n=1): s.n += n
            def close(s): pass
            def __enter__(s): return s
            def __exit__(s, *a): pass
            def __iter__(s):
                if s.iterable:
                    for i in s.iterable: yield i
            def set_description(s, d=None): pass
        return V(iterable, **kwargs)
    @staticmethod
    def get_tqdm():
        return VirtualTqdmModule.tqdm
sys.modules['tqdm'] = VirtualTqdmModule()
sys.modules['tqdm.auto'] = VirtualTqdmModule()
sys.modules['tqdm.autonotebook'] = VirtualTqdmModule()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Global SystemExit catch
_original_exit = sys.exit
def _safe_exit(*args, **kwargs):
    if args and (args[0] == 0 or args[0] is None):
        _original_exit(*args, **kwargs)
    print(f"  [BLOCKED] sys.exit({args}) prevented", flush=True)
sys.exit = _safe_exit

print('=' * 70, flush=True)
print('黄金量化分析报告 V6 - 2026-05-08', flush=True)
print(f'日期: {datetime.now().strftime("%Y-%m-%d %H:%M")}', flush=True)
print('=' * 70, flush=True)

try:
    from src.report.gold_report_generator_v6 import GoldReportGeneratorV6

    print('\n[1/4] 创建生成器...', flush=True)
    gen = GoldReportGeneratorV6(llm_type='chatanywhere', use_llm=True)
    print(f'  LLM: {gen.llm_type}, 启用: {gen.use_llm}', flush=True)

    print('\n[2/4] 获取市场数据...', flush=True)
    try:
        gen.fetch_all_data()
        print('  [OK] 数据获取完成', flush=True)
    except Exception as e:
        print(f'  [WARN] 数据获取部分失败: {e}', flush=True)

    print('\n[3/4] 生成AI内容...', flush=True)
    try:
        gen.generate_ai_content_for_topics()
        print('  [OK] AI内容完成', flush=True)
    except Exception as e:
        print(f'  [WARN] AI生成失败: {e}', flush=True)

    print('\n[4/4] 生成并保存HTML...', flush=True)
    html = gen.generate_html_report()
    if html:
        print(f'  HTML: {len(html)} 字符', flush=True)
        report_dir = Path('reports')
        report_dir.mkdir(exist_ok=True)
        ts = str(gen.data.get('sge_latest_date', datetime.now().strftime('%Y%m%d'))).replace('-','')
        filepath = report_dir / f'gold_report_{ts}_v6.html'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        size = os.path.getsize(filepath) / 1024
        print(f'\n{"="*70}', flush=True)
        print(f'[SUCCESS] {os.path.abspath(filepath)} ({size:.1f} KB)', flush=True)
        print(f'{"="*70}', flush=True)
    else:
        print('  [ERROR] HTML为空', flush=True)

except Exception as e:
    print(f'\n[ERROR] {e}', flush=True)
    traceback.print_exc()

sys.exit = _original_exit
