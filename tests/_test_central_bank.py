#!/usr/bin/env python3
"""简单测试央行购金数据获取"""
import sys
sys.path.insert(0, 'src')

from data.providers.akshare_provider import AkShareProvider

provider = AkShareProvider()
print("测试央行购金数据获取...")
print("=" * 60)

# 测试宏观数据获取
indicators = ['central_bank_buying', 'china_reserves']
data = provider.get_macro_data(indicators)

print(f"\n获取到的数据: {data}")
if 'central_bank_buying' in data:
    print(f"\n✅ 央行购金: {data['central_bank_buying']} 吨/月")
    if data['central_bank_buying'] > 200:
        print("⚠️ 警告: 数值异常高！全球央行年购金才1000-1200吨")
    elif data['central_bank_buying'] > 100:
        print("⚠️ 警告: 数值偏高，请验证")
    else:
        print("✅ 数值合理")
else:
    print("\n❌ 未获取到央行购金数据")

if 'china_reserves' in data:
    print(f"✅ 中国储备: {data['china_reserves']} 万盎司")
    print(f"   约 {data['china_reserves'] * 31.1035 / 10000:.2f} 吨")

print("=" * 60)
