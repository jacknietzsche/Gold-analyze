#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试算力云的其他可用模型
"""
import urllib.request
import urllib.error
import json
import time

API_KEY = "YOUR_API_KEY"
BASE_URL = "https://api.suanli.cn/v1"

# 之前获取的可用模型列表
AVAILABLE_MODELS = [
    "free:QwQ-32B",        # 无可用渠道
    "deepseek-r1:7b",      # 尝试这个
    "free:Qwen3-30B-A3B"  # 尝试这个
]

print("测试算力云API - 其他可用模型")
print("="*60)

success = False
working_model = None

for model in AVAILABLE_MODELS:
    print(f"\n测试模型: {model}")
    print("-" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
        ],
        "temperature": 0.7,
        "max_tokens": 200,
        "stream": False
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
            status_code = response.status
            response_data = json.loads(response.read().decode('utf-8'))
            
            print(f"✅ 状态码: {status_code}")
            print(f"⏱️  响应时间: {elapsed:.2f}秒")
            
            # 解析响应
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0]['message']['content']
                print(f"\n📝 回复内容:\n{content}\n")
                
                success = True
                working_model = model
                break  # 成功就退出
                
            else:
                print(f"⚠️  响应格式异常: {response_data}")
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} - {e.reason}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"   错误详情: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
        except:
            pass
        
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
    
    if model != AVAILABLE_MODELS[-1]:
        print(f"\n⏸️  等待2秒后尝试下一个模型...")
        time.sleep(2)

print(f"\n{'='*60}")
if success:
    print("🎉 算力云API测试成功！")
    print(f"💡 建议配置: suanli_model: str = \"{working_model}\"")
else:
    print("⚠️  所有模型都失败了")
    print("\n可能原因:")
    print("  1. API密钥权限不足（分组限制）")
    print("  2. 需要联系算力云开通模型访问权限")
    print("  3. 免费模型需要特殊申请")
    print("\n建议:")
    print("  - 暂时使用OpenRouter API（已测试成功）")
    print("  - 或联系算力云客服了解如何访问这些模型")
print(f"{'='*60}")
