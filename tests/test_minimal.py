#!/usr/bin/env python3
"""最小测试 - 直接调用 get_all_data()"""
import sys

# 直接写入文件，不依赖stdout flush
log = open('minimal_test_log.txt', 'w')

def write(msg):
    print(msg, flush=True)
    log.write(msg + '\n')
    log.flush()

write('[TEST] 开始...')
write(f'[TEST] Python: {sys.version}')

try:
    write('[TEST] 导入 get_data_service()...')
    from src.data.data_service import get_data_service
    write('[TEST] 导入成功')
    
    write('[TEST] 调用 get_all_data()...')
    data = get_data_service().get_all_data()
    write('[TEST] get_all_data() 返回!')
    
    price = data.get('price', [])
    write(f'[TEST] 价格数据条数: {len(price) if hasattr(price, "__len__") else "N/A"}')
    
    write('[TEST] 完成!')
    log.close()
    sys.exit(0)
    
except Exception as e:
    write(f'[TEST] 异常: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc(file=log)
    log.close()
    sys.exit(1)
except:
    write('[TEST] 未知异常!')
    import traceback
    traceback.print_exc(file=log)
    log.close()
    sys.exit(1)
