#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试算力云API - 使用正确的参数
"""
import urllib.request
import urllib.error
import json
import time

API_KEY = "YOUR_API_KEY"
BASE_URL = "https://api.suanli.cn/v1"
MODEL = "free:QwQ-32B"

print(f"测试算力云 API")
print(f"URL: {BASE_URL}")
print(f"Model: {MODEL}")
print("="*60)

# 尝试不同的请求格式
test_cases = [
    {
        "name": "标准格式",
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
            ],
            "temperature": 0.7,
            "max_tokens": 200,
            "stream": False
        }
    },
    {
        "name": "添加stream_options",
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
            ],
            "temperature": 0.7,
            "max_tokens": 200,
            "stream": False,
            "stream_options": None
        }
    },
    {
        "name": "使用QwQ的思考模式",
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
            ],
            "temperature": 0.7,
            "max_tokens": 200,
            "stream": False,
            "enable_thinking": True
        }
    }
]

success = False

for i, test in enumerate(test_cases, 1):
    print(f"\n【测试 {i}】{test['name']}")
    print("-" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/chat/completions",
            data=json.dumps(test['payload']).encode('utf-8'),
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
                
                # 打印使用统计（如果有）
                if 'usage' in response_data:
                    usage = response_data['usage']
                    print(f"📊 Token使用: 输入={usage.get('prompt_tokens', 'N/A')}, 输出={usage.get('completion_tokens', 'N/A')}")
                
                success = True
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
        
    except urllib.error.URLError as e:
        print(f"❌ URL错误: {e.reason}")
        
    except Exception as e:
        print(f"❌ 未知错误: {type(e).__name__}: {e}")
    
    if i < len(test_cases):
        print(f"\n⏸️  等待2秒后尝试下一个格式...")
        time.sleep(2)

print(f"\n{'='*60}")
if success:
    print("🎉 算力云API测试成功！")
    print(f"💡 建议配置: suanli_model: str = \"{MODEL}\"")
else:
    print("⚠️  所有测试格式都失败了")
    print("可能原因:")
    print("  1. API密钥无效或过期")
    print("  2. 该密钥没有访问 free:QwQ-32B 的权限")
    print("  3. 算力云API需要特殊认证或白名单")
print(f"{'='*60}")
