#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 OpenRouter API - 添加必需请求头
OpenRouter 要求: HTTP-Referer 和 X-Title
"""
import sys
import os
import urllib.request
import urllib.error
import json
import time

API_KEY = "YOUR_OPENROUTER_API_KEY"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "inclusionai/ring-2.6-1t:free"

print("=" * 60)
print("测试 OpenRouter API - 添加必需请求头")
print("=" * 60)

# OpenRouter 要求的请求头
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://localhost:8080",  # 必需
    "X-Title": "Gold Quantitative Analysis System"  # 必需
}

payload = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
    ],
    "temperature": 0.7,
    "max_tokens": 200
}

print(f"模型: {MODEL}")
print(f"请求头: HTTP-Referer, X-Title 已添加")
print("-" * 60)

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
        
        if 'choices' in response_data and len(response_data['choices']) > 0:
            content = response_data['choices'][0]['message']['content']
            print(f"\n📝 回复内容:\n{content}\n")
            print("=" * 60)
            print("🎉 OpenRouter API 测试成功！")
            print("=" * 60)
            print(f"\n💡 建议配置:")
            print(f"  openrouter_model: str = \"{MODEL}\"")
            sys.exit(0)
        else:
            print(f"⚠️  响应格式异常: {response_data}")
            sys.exit(1)
            
except urllib.error.HTTPError as e:
    print(f"❌ HTTP错误: {e.code} - {e.reason}")
    try:
        error_data = json.loads(e.read().decode('utf-8'))
        print(f"   错误详情: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
    except:
        pass
    sys.exit(1)
    
except Exception as e:
    print(f"❌ 错误: {type(e).__name__}: {e}")
    sys.exit(1)
