#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终修复脚本 - 完整解决tqdm和LLM集成问题
"""
import sys
import os
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 第一步：创建完整的虚拟tqdm模块
class VirtualTqdmModule:
    """虚拟tqdm模块，完全模拟tqdm功能"""
    
    @staticmethod
    def tqdm(iterable=None, **kwargs):
        class VirtualTqdm:
            def __init__(self, iterable=None, **kwargs):
                self.iterable = iterable
                self.n = 0
                self.total = len(iterable) if iterable is not None else 100
                self.disable = kwargs.get('disable', True)
                self.desc = kwargs.get('desc', '')
                self.unit = kwargs.get('unit', 'it')
                
            def update(self, n=1):
                self.n += n
                
            def close(self):
                pass
                
            def __enter__(self):
                return self
                
            def __exit__(self, *args, **kwargs):
                pass
                
            def __iter__(self):
                if self.iterable:
                    for item in self.iterable:
                        yield item
                else:
                    # 返回一个空的迭代器
                    class EmptyIterator:
                        def __iter__(self):
                            return self
                        def __next__(self):
                            raise StopIteration
                    return EmptyIterator()
                    
            def set_description(self, desc=None):
                if desc:
                    self.desc = desc
                    
        return VirtualTqdm(iterable, **kwargs)
    
    # akshare需要get_tqdm函数
    @staticmethod
    def get_tqdm():
        return VirtualTqdmModule.tqdm
        
# 将虚拟模块注入sys.modules
sys.modules['tqdm'] = VirtualTqdmModule()
sys.modules['tqdm.auto'] = VirtualTqdmModule()
sys.modules['tqdm.autonotebook'] = VirtualTqdmModule()

# 第二步：设置LLM API Key
# 使用SiliconFlow API (DeepSeek-R1模型)
os.environ['SILICONFLOW_API_KEY'] = 'YOUR_SILICONFLOW_API_KEY'
os.environ['CHERRY_API_KEY'] = 'YOUR_CHERRY_API_KEY'
os.environ['FRED_API_KEY'] = 'YOUR_FRED_API_KEY'  # 美联储FRED经济数据

def run_with_progress():
    """带进度显示运行报告生成器"""
    print("=" * 70)
    print("黄金量化分析报告生成器 V6 (LLM增强版)")
    print("=" * 70)
    
    try:
        # 检查数据服务
        print("\n[1/5] 检查数据服务...")
        from src.data.data_service import get_data_service
        print("  ✅ 数据服务就绪")
        
        # 创建报告生成器
        print("[2/5] 初始化报告生成器...")
        from src.report.gold_report_generator_v6 import GoldReportGeneratorV6
        gen = GoldReportGeneratorV6(llm_type="chatanywhere", use_llm=True)
        print(f"  ✅ LLM启用: {gen.use_llm}")
        print(f"  ✅ LLM类型: {gen.llm_type}")
        
        # 获取数据
        print("[3/5] 获取市场数据...")
        gen.fetch_all_data()
        print("  ✅ 数据获取完成")
        
        # 生成报告
        print("[4/5] 生成量化分析报告...")
        html_report = gen.generate_html_report()
        if not html_report:
            print("  ❌ 报告生成失败")
            return False
            
        print(f"  ✅ 报告生成完成 ({len(html_report)} 字符)")
        
        # 保存报告
        print("[5/5] 保存报告文件...")
        gen.save_report()
        
        # 检查报告文件
        import glob
        reports = glob.glob("reports/gold_report_*.html")
        if not reports:
            print("  ❌ 未找到报告文件")
            return False
            
        latest_report = max(reports, key=os.path.getctime)
        print(f"  ✅ 报告已保存: {latest_report}")
        print(f"    文件大小: {os.path.getsize(latest_report) / 1024:.1f} KB")
        
        return True, latest_report
        
    except Exception as e:
        print(f"\n[ERROR] 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def analyze_report(report_path):
    """分析生成的报告"""
    print("\n" + "=" * 70)
    print("报告内容分析")
    print("=" * 70)
    
    try:
        with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # 检查关键部分
        checks = [
            ("封面信息", ["黄金量化分析报告", "当前价格", "报告日期"]),
            ("核心数据概览", ["当前金价", "5日收益", "RSI", "历史分位"]),
            ("周期收益分析", ["1日", "5日", "20日", "60日", "120日", "252日"]),
            ("GRAM评分", ["GRAM 评分", "驱动因子", "权重", "综合评分"]),
            ("技术指标", ["RSI", "MACD", "布林", "KDJ", "ATR"]),
            ("机构观点", ["高盛", "摩根大通", "贝莱德", "市场共识"]),
            ("量化分析模块", ["量化分析模块", "Strategy Backtest", "Risk Management", "Market Regime"]),
            ("风险量化", ["VaR", "CVaR", "最大回撤", "夏普比率"]),
            ("操作建议", ["趋势判断", "操作建议", "支撑位", "阻力位"]),
            ("资产配置", ["黄金配置比例", "保守型", "平衡型", "积极型"]),
        ]
        
        print("报告内容完整性检查:")
        all_passed = True
        for check_name, keywords in checks:
            passed = any(keyword in content for keyword in keywords)
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False
                
        # 检查AI分析部分
        ai_keywords = ["AI分析", "LLM", "人工智能", "智能分析", "深度分析", "综合研判"]
        has_ai = any(keyword in content for keyword in ai_keywords)
        ai_status = "✅ 包含AI分析" if has_ai else "⚠️  未检测到AI分析内容"
        print(f"\n  {ai_status}")
        
        if not has_ai:
            print("\n[INFO] AI分析缺失的可能原因:")
            print("  1. API Key无效或未配置")
            print("  2. LLM服务连接失败")
            print("  3. AI分析模块被跳过")
            print("\n解决方法:")
            print("  1. 设置有效的CHATANYWHERE_API_KEY环境变量")
            print("  2. 访问 https://www.chatanywhere.cn/ 获取API Key")
            print("  3. 检查网络连接")
            
        return all_passed, has_ai
        
    except Exception as e:
        print(f"[ERROR] 分析报告失败: {e}")
        return False, False

def main():
    """主函数"""
    print("\n黄金量化分析系统 - 完整运行流程")
    print("生成包含LLM AI分析的量化报告")
    print("=" * 70)
    
    # 显示系统信息
    print("系统信息:")
    print(f"  工作目录: {os.getcwd()}")
    print(f"  Python版本: {sys.version[:30]}...")
    print(f"  API Key配置: {'CHATANYWHERE_API_KEY' in os.environ}")
    if 'CHATANYWHERE_API_KEY' in os.environ:
        key = os.environ['CHATANYWHERE_API_KEY']
        print(f"  API Key长度: {len(key)} 字符")
        print(f"  API Key前缀: {key[:10]}...")
    
    # 运行报告生成器
    success, report_path = run_with_progress()
    
    if not success:
        print("\n" + "=" * 70)
        print("[FAILED] 报告生成失败")
        print("=" * 70)
        return
    
    # 分析报告
    report_ok, has_ai = analyze_report(report_path)
    
    # 总结
    print("\n" + "=" * 70)
    print("运行总结")
    print("=" * 70)
    
    if report_ok:
        print("✅ 报告生成成功!")
        print(f"   文件路径: {os.path.abspath(report_path)}")
        print(f"   AI分析: {'✅ 已集成' if has_ai else '⚠️  未集成'}")
        
        # 提供建议
        if not has_ai:
            print("\n⚠️  如需获取完整AI分析:")
            print("   1. 设置真实的ChatAnywhere API Key")
            print("      export CHATANYWHERE_API_KEY='your-real-api-key'")
            print("   2. 重新运行本脚本")
            
        print("\n📊 报告包含以下内容:")
        print("   - 核心数据概览和GRAM评分")
        print("   - 周期收益分析和技术指标")
        print("   - 机构观点对比和风险量化")
        print("   - 量化分析模块(策略回测、风险、机制检测)")
        print("   - 操作建议和资产配置")
        
    else:
        print("⚠️  报告生成完成，但内容不完整")
        print(f"   文件路径: {os.path.abspath(report_path)}")
        print("\n建议检查:")
        print("   1. 数据源连接状态")
        print("   2. API Key有效性")
        print("   3. 网络连接")
    
    print("\n" + "=" * 70)
    print("完成!")
    print("=" * 70)

if __name__ == "__main__":
    main()