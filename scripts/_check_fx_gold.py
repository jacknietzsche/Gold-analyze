#!/usr/bin/env python3
"""检查macro_china_fx_gold()返回的数据"""
import akshare as ak
import pandas as pd

print("获取macro_china_fx_gold数据...")
fx_gold = ak.macro_china_fx_gold()

if fx_gold is not None:
    print(f"\n数据类型: {type(fx_gold)}")
    print(f"数据形状: {fx_gold.shape}")
    print(f"\n列名: {fx_gold.columns.tolist()}")
    print(f"\n前5行数据:")
    print(fx_gold.head())
    print(f"\n后5行数据:")
    print(fx_gold.tail())
    
    # 查找黄金储备相关列
    for col in fx_gold.columns:
        if '黄金' in str(col) or 'gold' in str(col).lower():
            print(f"\n=== 列: {col} ===")
            print(fx_gold[[col]].tail(10))
            
            # 尝试转换为数字
            val = pd.to_numeric(fx_gold.iloc[-1][col], errors='coerce')
            print(f"\n最新值: {val}")
            print(f"数据类型: {type(val)}")
else:
    print("获取数据失败")
