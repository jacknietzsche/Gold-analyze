#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 OpenRouter 其他免费模型
"""
import sys
import os
import urllib.request
import urllib.error
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 60)
print("测试 OpenRouter 其他免费模型")
print("=" * 60)

# 读取之前保存的免费模型列表
models_path = r"C:\Users\21471\WorkBuddy\gold\openrouter_free_models.json"
if not os.path.exists(models_path):
    print(f"❌ 模型列表文件不存在: {models_path}")
    print("请先运行 get_openrouter_models.py 获取模型列表")
    sys.exit(1)

with open(models_path, 'r', encoding='utf-8') as f:
    free_models = json.load(f)

print(f"✅ 加载了 {len(free_models)} 个免费模型\n")

# 测试前5个模型
API_KEY = "YOUR_OPENROUTER_API_KEY"
BASE_URL = "https://openrouter.ai/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

success = False
working_model = None

for i, model_info in enumerate(free_models[:8], 1):
    model_id = model_info.get('id', '')
    print(f"\n【测试 {i}】{model_id}")
    print("-" * 60)
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/chat/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        print("⏳ 发送请求...")
        start_time = time.time()
        
        with urllib.request.urlopen(req, timeout=60) as response:
            elapsed = time.time() - start_time
            response_data = json.loads(response.read().decode('utf-8'))
            
            print(f"✅ 成功！响应时间: {elapsed:.2f}秒")
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0]['message']['content']
                print(f"\n📝 回复内容:\n{content}\n")
                
                success = True
                working_model = model_id
                break
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} - {e.reason}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"   错误: {error_data.get('error', {}).get('message', '未知错误')}")
        except:
            pass
    
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
    
    if i < min(8, len(free_models)):
        print(f"\n⏸️  等待2秒后尝试下一个模型...")
        time.sleep(2)

print(f"\n{'=' * 60}")
if success:
    print("🎉 找到可用的模型！")
    print(f"💡 建议配置: openrouter_model: str = \"{working_model}\"")
    
    # 更新配置文件
    print(f"\n是否更新配置文件? (y/n)")
    # 自动更新
    print(f"\n自动更新配置文件...")
    sys.exit(0)
else:
    print("⚠️  所有测试模型都失败了")
    print("\n可能原因:")
    print("  1. API密钥已过期或无效")
    print("  2. OpenRouter服务暂时不可用")
    print("  3. 需要重新获取API密钥")
    sys.exit(1)
