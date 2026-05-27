#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全测试 OpenRouter API 集成
分阶段测试，避免静默崩溃
"""
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 60)
print("阶段1: 测试配置加载")
print("=" * 60)

try:
    from config.gold_config import CONFIG
    
    print(f"✅ 配置加载成功")
    print(f"   llm_type: {CONFIG.llm.llm_type}")
    print(f"   openrouter_model: {CONFIG.llm.openrouter_model}")
    print(f"   openrouter_base_url: {CONFIG.llm.openrouter_base_url}")
    print(f"   openrouter_api_key (前20字符): {CONFIG.llm.openrouter_api_key[:20]}...")
    
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    sys.exit(1)

print(f"\n{'=' * 60}")
print("阶段2: 直接测试 OpenRouter API 调用")
print("=" * 60)

import urllib.request
import json

try:
    headers = {
        "Authorization": f"Bearer {CONFIG.llm.openrouter_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": CONFIG.llm.openrouter_model,
        "messages": [
            {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
        ],
        "temperature": CONFIG.llm.temperature,
        "max_tokens": 200
    }
    
    print(f"请求模型: {CONFIG.llm.openrouter_model}")
    print("⏳ 发送请求...")
    
    req = urllib.request.Request(
        f"{CONFIG.llm.openrouter_base_url}/chat/completions",
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    import time
    start_time = time.time()
    
    with urllib.request.urlopen(req, timeout=CONFIG.llm.timeout) as response:
        elapsed = time.time() - start_time
        response_data = json.loads(response.read().decode('utf-8'))
        
        print(f"✅ API调用成功！响应时间: {elapsed:.2f}秒")
        
        if 'choices' in response_data and len(response_data['choices']) > 0:
            content = response_data['choices'][0]['message']['content']
            print(f"\n📝 回复内容:\n{content}\n")
            print("=" * 60)
            print("✅ OpenRouter API 集成测试通过！")
            print("=" * 60)
            sys.exit(0)
        else:
            print(f"⚠️  响应格式异常: {response_data}")
            sys.exit(1)
            
except Exception as e:
    print(f"❌ API调用失败: {type(e).__name__}: {e}")
    sys.exit(1)
