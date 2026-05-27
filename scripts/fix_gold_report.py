#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复黄金报告生成问题
1. 解决tqdm兼容性问题
2. 设置LLM API Key
3. 确保AI分析集成
"""
import sys
import os
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 禁用tqdm
import sys
import io
class NoTqdm:
    def __init__(self, *args, **kwargs):
        pass
    def update(self, n=1):
        pass
    def close(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

# 替换tqdm
try:
    sys.modules['tqdm'] = type(sys)('tqdm')
    sys.modules['tqdm'].tqdm = NoTqdm
    sys.modules['tqdm'].auto = type(sys)('auto')
    sys.modules['tqdm'].auto.tqdm = NoTqdm
except:
    pass

def set_api_key():
    """设置LLM API Key"""
    # 你可以在这里设置你的ChatAnywhere API Key
    # 或者从环境变量读取
    api_key = os.environ.get("CHATANYWHERE_API_KEY")
    
    if not api_key:
        print("[INFO] 未设置CHATANYWHERE_API_KEY环境变量")
        print("可以通过以下方式设置:")
        print("1. 设置环境变量: export CHATANYWHERE_API_KEY='your-key'")
        print("2. 在代码中临时设置: os.environ['CHATANYWHERE_API_KEY'] = 'your-key'")
        
        # 尝试从配置文件读取
        try:
            from src.config.gold_config import CONFIG
            if CONFIG.llm.chatanywhere_api_key:
                api_key = CONFIG.llm.chatanywhere_api_key
                print(f"[INFO] 从配置文件读取API Key")
                return api_key
        except:
            pass
        
        # 提示用户
        print("\n[ACTION] 需要设置ChatAnywhere API Key才能启用AI分析")
        print("请访问: https://www.chatanywhere.cn/ 获取API Key")
        print("然后设置环境变量或修改配置文件")
        
        return None
    else:
        print(f"[OK] 使用环境变量中的API Key (长度: {len(api_key)})")
        return api_key

def run_report_with_fixes():
    """运行修复后的报告生成"""
    print("=" * 60)
    print("修复黄金报告生成问题")
    print("=" * 60)
    
    # 1. 设置API Key
    api_key = set_api_key()
    
    # 2. 运行报告生成器
    try:
        # 动态修改配置
        if api_key:
            os.environ['CHATANYWHERE_API_KEY'] = api_key
        
        # 导入并运行
        from src.report.gold_report_generator_v6 import main
        
        print("\n[1] 开始生成报告 (包含AI分析)...")
        print("    注意: 可能需要2-3分钟，AI分析需要API Key")
        
        # 强制启用LLM
        result = main(use_llm=True, llm_type='chatanywhere', api_key=api_key)
        
        if result:
            print("\n[SUCCESS] 报告生成成功!")
            
            # 检查报告文件
            import glob
            reports = glob.glob("reports/gold_report_*.html")
            if reports:
                latest_report = max(reports, key=os.path.getctime)
                print(f"    报告文件: {latest_report}")
                print(f"    文件大小: {os.path.getsize(latest_report) / 1024:.1f} KB")
                
                # 检查是否包含AI分析
                with open(latest_report, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'AI分析' in content or 'LLM' in content or '人工智能' in content:
                        print("    AI分析: ✅ 包含")
                    else:
                        print("    AI分析: ❌ 未包含 (可能API Key无效)")
                        
                return True, latest_report
            else:
                print("[WARN] 未找到生成的报告文件")
                return False, None
        else:
            print("[ERROR] 报告生成失败")
            return False, None
            
    except Exception as e:
        print(f"[ERROR] 运行报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_data_sources():
    """测试数据源"""
    print("\n" + "=" * 60)
    print("测试数据源...")
    print("=" * 60)
    
    try:
        # 禁用tqdm后导入
        import src.data.providers.akshare_provider as ak_module
        print("[OK] akshare provider导入成功")
        
        # 测试黄金价格
        from src.data.data_service import get_data_service
        
        print("\n[1] 测试黄金价格数据...")
        price_df = get_data_service().get_gold_price(symbol="Au99.99", period="30d")
        if price_df is not None and not price_df.empty:
            print(f"  成功: {len(price_df)} 条记录")
            print(f"  最新价格: {price_df.iloc[-1] if len(price_df) > 0 else '无数据'}")
        else:
            print("  失败: 数据为空")
            
        return True
    except Exception as e:
        print(f"[ERROR] 数据源测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("黄金量化分析报告修复工具")
    print("版本: V6修复版")
    print("=" * 60)
    
    # 1. 测试数据源
    data_ok = test_data_sources()
    if not data_ok:
        print("\n[ERROR] 数据源测试失败，无法继续")
        return
    
    # 2. 运行修复后的报告生成
    success, report_path = run_report_with_fixes()
    
    if success and report_path:
        print("\n" + "=" * 60)
        print("[SUCCESS] 修复完成!")
        print(f"报告已生成: {report_path}")
        print("=" * 60)
        
        # 提供打开报告的选项
        print("\n[建议] 可以手动打开报告文件查看完整分析")
        print(f"文件路径: {os.path.abspath(report_path)}")
    else:
        print("\n" + "=" * 60)
        print("[FAILED] 修复失败")
        print("=" * 60)

if __name__ == "__main__":
    main()