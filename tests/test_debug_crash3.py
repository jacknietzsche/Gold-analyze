#!/usr/bin/env python3
"""测试报告生成 - 分步导入调试"""
import faulthandler
import sys
import os

faulthandler.enable()

log_file = open('test_output2.log', 'w', buffering=1)

def log(msg):
    print(msg, flush=True)
    log_file.write(msg + '\n')
    log_file.flush()

log('[TEST] 开始...')
log(f'[TEST] Python: {sys.version}')
log(f'[TEST] 工作目录: {os.getcwd()}')

# 先单独测试 akshare 导入
log('[TEST] 步骤1: 单独导入akshare...')
try:
    import akshare as ak
    log(f'[TEST] akshare 导入成功，版本: {ak.__version__}')
except Exception as e:
    log(f'[TEST] akshare 导入失败: {e}')
    import traceback
    traceback.print_exc(file=log_file)
    sys.exit(1)

# 再测试 data_service 导入
log('[TEST] 步骤2: 导入data_service...')
try:
    from src.data.data_service import get_data_service
    log('[TEST] data_service 导入成功')
except Exception as e:
    log(f'[TEST] data_service 导入失败: {e}')
    import traceback
    traceback.print_exc(file=log_file)
    sys.exit(1)

# 再测试生成器导入
log('[TEST] 步骤3: 导入GoldReportGeneratorV6...')
try:
    from src.report.gold_report_generator_v6 import GoldReportGeneratorV6
    log('[TEST] 生成器导入成功')
except Exception as e:
    log(f'[TEST] 生成器导入失败: {e}')
    import traceback
    traceback.print_exc(file=log_file)
    sys.exit(1)

# 创建生成器
log('[TEST] 步骤4: 创建生成器实例...')
try:
    gen = GoldReportGeneratorV6(llm_type='openrouter', use_llm=False)
    log('[TEST] 生成器创建成功')
except Exception as e:
    log(f'[TEST] 生成器创建失败: {e}')
    import traceback
    traceback.print_exc(file=log_file)
    sys.exit(1)

# 获取数据
log('[TEST] 步骤5: 获取数据...')
try:
    gen.fetch_all_data()
    log('[TEST] 数据获取完成')
except Exception as e:
    log(f'[TEST] 数据获取失败: {e}')
    import traceback
    traceback.print_exc(file=log_file)
    sys.exit(1)

# 保存报告
log('[TEST] 步骤6: 保存报告...')
try:
    result = gen.save_report(use_llm=False)
    log(f'[TEST] 报告保存完成: {result}')
except Exception as e:
    log(f'[TEST] 报告保存失败: {e}')
    import traceback
    traceback.print_exc(file=log_file)
    sys.exit(1)

log('[TEST] 全部完成!')
log_file.close()
sys.exit(0)
