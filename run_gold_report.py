#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金报告生成器运行脚本
解决导入路径和数据服务问题
"""
import sys
import os
import traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings('ignore')

def test_data_service():
    """测试数据服务"""
    print("=" * 60)
    print("测试数据服务...")
    print("=" * 60)
    
    try:
        from src.data.data_service import get_data_service
        print("[OK] 数据服务导入成功")
        
        # 测试黄金价格
        print("\n[1] 获取黄金价格数据...")
        price_df = get_data_service().get_gold_price(symbol="Au99.99", period="30d")
        if price_df is not None and not price_df.empty:
            print(f"  获取成功: {len(price_df)} 条记录")
            print(f"  最新价格: {price_df.iloc[-1] if len(price_df) > 0 else '无数据'}")
            print(f"  日期范围: {price_df.index[0]} 到 {price_df.index[-1]}")
        else:
            print("  获取失败或数据为空")
            
        # 测试美元指数和VIX - 通过宏观数据接口
        print("\n[2] 获取美元指数和VIX数据...")
        try:
            macro_data = get_data_service().get_macro_data(['dollar_index', 'vix'])
            if macro_data:
                if 'dollar_index' in macro_data:
                    print(f"  美元指数获取成功")
                if 'vix' in macro_data:
                    print(f"  VIX获取成功")
            else:
                print("  获取失败或数据为空")
        except Exception as e:
            print(f"  获取失败: {e}")
            
        return True
    except Exception as e:
        print(f"[ERROR] 数据服务测试失败: {e}")
        traceback.print_exc()
        return False

def test_report_generator():
    """测试报告生成器"""
    print("\n" + "=" * 60)
    print("测试报告生成器...")
    print("=" * 60)
    
    try:
        from src.report.gold_report_generator_v6 import GoldReportGeneratorV6
        print("[OK] 报告生成器导入成功")
        
        # 创建实例但不立即运行
        gen = GoldReportGeneratorV6(llm_type="openrouter", use_llm=True)
        print(f"  实例创建成功")
        print(f"  LLM启用: {gen.use_llm}")
        
        return gen
    except Exception as e:
        print(f"[ERROR] 报告生成器测试失败: {e}")
        traceback.print_exc()
        return None

def run_report_with_llm():
    """运行完整报告生成流程"""
    print("\n" + "=" * 60)
    print("运行完整报告生成流程...")
    print("=" * 60)
    
    try:
        # 检查API Key
        import os
        api_key = os.environ.get("CHATANYWHERE_API_KEY")
        if not api_key:
            print("[WARN] 未设置CHATANYWHERE_API_KEY环境变量")
            print("  将尝试从配置文件读取...")
            
        # 从配置文件读取API Key
        try:
            from src.config.gold_config import CONFIG
            if CONFIG.llm.chatanywhere_api_key:
                api_key = CONFIG.llm.chatanywhere_api_key
                print(f"[OK] 从配置文件读取API Key")
            else:
                print("[WARN] 配置文件中未找到API Key")
        except:
            print("[WARN] 无法读取配置文件")
        
        # 导入并运行
        from src.report.gold_report_generator_v6 import main
        
        print("\n[1] 开始生成报告...")
        print("   注意: 完整报告生成可能需要2-3分钟")
        
        # 优先使用OpenRouter（已测试成功）
        result = main(use_llm=True, llm_type="openrouter", api_key=api_key)
        
        if result:
            print("\n[SUCCESS] 报告生成成功!")
            print(f"  报告生成器实例: {result}")
            return True
        else:
            print("\n[ERROR] 报告生成失败!")
            return False
            
    except Exception as e:
        print(f"[ERROR] 运行报告生成流程失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("黄金量化分析报告生成系统")
    print("版本: V6 (LLM增强版)")
    print("=" * 60)
    
    # 1. 测试数据服务
    data_ok = test_data_service()
    if not data_ok:
        print("\n[ERROR] 数据服务测试失败，无法继续")
        return
    
    # 2. 测试报告生成器
    gen = test_report_generator()
    if not gen:
        print("\n[ERROR] 报告生成器测试失败，无法继续")
        return
    
    # 3. 运行完整报告
    success = run_report_with_llm()
    
    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] 黄金量化分析报告生成完成!")
        print("请查看 reports/ 目录下的HTML报告文件")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[FAILED] 报告生成失败")
        print("=" * 60)

if __name__ == "__main__":
    main()