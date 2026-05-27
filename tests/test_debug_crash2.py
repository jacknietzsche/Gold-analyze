#!/usr/bin/env python3
"""测试报告生成 - 调试静默崩溃"""
import faulthandler
import sys
import os

# 将faulthandler输出到文件
faulthandler.enable()
faulthandler.dump_traceback_later(5, repeat=True, file=open('crash_debug.txt', 'w'))

log_file = open('test_output.log', 'w', buffering=1)

def log(msg):
    """同时输出到stdout和日志文件"""
    print(msg, flush=True)
    log_file.write(msg + '\n')
    log_file.flush()

log('[TEST] 开始...')
log(f'[TEST] Python: {sys.version}')
log(f'[TEST] 工作目录: {os.getcwd()}')

try:
    log('[TEST] 导入生成器...')
    from src.report.gold_report_generator_v6 import GoldReportGeneratorV6
    log('[TEST] 导入成功，创建生成器...')
    
    gen = GoldReportGeneratorV6(llm_type='openrouter', use_llm=False)
    log('[TEST] 已创建生成器，开始获取数据...')
    
    gen.fetch_all_data()
    log('[TEST] 数据获取完成，开始保存报告...')
    
    result = gen.save_report(use_llm=False)
    log(f'[TEST] 完成，结果: {result}')
    
except Exception as e:
    log(f'[TEST] 异常: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc(file=log_file)
    sys.exit(1)

log('[TEST] 脚本完成')
log_file.close()
sys.exit(0)
