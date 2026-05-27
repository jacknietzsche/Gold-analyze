#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复黄金报告生成问题 - 版本2
直接修复tqdm问题和运行报告生成器
"""
import sys
import os
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 修复1: 完全禁用tqdm
import builtins
original_import = builtins.__import__

def no_tqdm_import(name, *args, **kwargs):
    if name == 'tqdm' or name.startswith('tqdm.'):
        # 返回一个虚拟的tqdm模块
        class FakeTqdm:
            def __init__(self, iterable=None, **kwargs):
                self.iterable = iterable if iterable is not None else []
                self.n = 0
                self.total = len(self.iterable) if hasattr(self.iterable, '__len__') else 100
                
            def update(self, n=1):
                self.n += n
                
            def close(self):
                pass
                
            def __enter__(self):
                return self
                
            def __exit__(self, *args):
                pass
                
            def __iter__(self):
                if self.iterable:
                    return iter(self.iterable)
                # 返回一个空的迭代器
                class EmptyIterator:
                    def __iter__(self):
                        return self
                    def __next__(self):
                        raise StopIteration
                return EmptyIterator()
        
        fake_module = type(sys)('tqdm')
        fake_module.tqdm = FakeTqdm
        fake_module.autonotebook = fake_module
        fake_module.auto = fake_module
        return fake_module
    return original_import(name, *args, **kwargs)

builtins.__import__ = no_tqdm_import

# 修复2: 设置一个虚拟的API Key用于测试
# 注意: 这里设置的是一个无效的测试key，实际使用时需要替换为真实的API Key
os.environ['CHATANYWHERE_API_KEY'] = 'YOUR_TEST_KEY'

def run_report():
    """运行报告生成器"""
    print("=" * 60)
    print("修复后运行黄金报告生成器")
    print("=" * 60)
    
    try:
        # 导入模块
        from src.report.gold_report_generator_v6 import GoldReportGeneratorV6
        print("[OK] 导入报告生成器成功")
        
        # 创建实例
        gen = GoldReportGeneratorV6(llm_type="chatanywhere", use_llm=True)
        print("[OK] 创建生成器实例")
        
        # 获取数据
        print("\n[1] 获取数据...")
        gen.fetch_all_data()
        print("[OK] 数据获取完成")
        
        # 生成报告
        print("\n[2] 生成报告...")
        html_report = gen.generate_html_report()
        if html_report:
            print(f"[OK] 报告生成完成，长度: {len(html_report)} 字符")
        else:
            print("[ERROR] 报告生成失败")
            return False
            
        # 保存报告
        print("\n[3] 保存报告...")
        gen.save_report()
        print("[OK] 报告保存完成")
        
        # 检查是否生成了文件
        import glob
        reports = glob.glob("reports/gold_report_*.html")
        if reports:
            latest = max(reports, key=os.path.getctime)
            print(f"\n[SUCCESS] 最新报告: {latest}")
            print(f"文件大小: {os.path.getsize(latest) / 1024:.1f} KB")
            
            # 检查内容
            with open(latest, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # 检查关键部分
            checks = {
                '量化分析模块': '量化分析模块' in content,
                'GRAM评分': 'GRAM 评分' in content,
                '技术指标': '技术指标' in content,
                '风险量化': '风险量化' in content,
                'AI分析': any(keyword in content for keyword in ['AI分析', 'LLM', '人工智能', '智能分析'])
            }
            
            print("\n报告内容检查:")
            for check_name, result in checks.items():
                status = "✅" if result else "❌"
                print(f"  {status} {check_name}")
                
            return True
        else:
            print("[ERROR] 未找到报告文件")
            return False
            
    except Exception as e:
        print(f"[ERROR] 运行报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("黄金报告生成器修复工具 - 版本2")
    print("修复tqdm问题和API Key配置")
    print("=" * 60)
    
    # 显示当前配置
    print("当前配置:")
    print(f"  工作目录: {os.getcwd()}")
    print(f"  API Key已设置: {'CHATANYWHERE_API_KEY' in os.environ}")
    
    # 运行报告生成器
    success = run_report()
    
    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] 修复完成! 报告已生成")
        print("=" * 60)
        
        # 显示报告位置
        import glob
        reports = glob.glob("reports/gold_report_*.html")
        if reports:
            latest = max(reports, key=os.path.getctime)
            print(f"\n报告文件: {os.path.abspath(latest)}")
            print("\n注意:")
            print("1. 当前使用了测试API Key，AI分析可能不完整")
            print("2. 需要真实的ChatAnywhere API Key获取完整AI分析")
            print("3. 访问 https://www.chatanywhere.cn/ 获取API Key")
    else:
        print("\n" + "=" * 60)
        print("[FAILED] 修复失败")
        print("=" * 60)

if __name__ == "__main__":
    main()