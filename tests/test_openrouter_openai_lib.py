#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 openai 官方库测试 OpenRouter API
"""
import sys
import os
import time

print("=" * 60)
print("使用 openai 库测试 OpenRouter API")
print("=" * 60)

try:
    from openai import OpenAI
    print("✅ openai 库加载成功")
except ImportError as e:
    print(f"❌ 导入 openai 库失败: {e}")
    sys.exit(1)

# 初始化 OpenRouter 客户端
client = OpenAI(
    api_key="YOUR_OPENROUTER_API_KEY",
    base_url="https://openrouter.ai/api/v1"
)

MODEL = "inclusionai/ring-2.6-1t:free"

print(f"\n模型: {MODEL}")
print(f"Base URL: https://openrouter.ai/api/v1")
print("-" * 60)

try:
    print("⏳ 发送请求...")
    start_time = time.time()
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
        ],
        temperature=0.7,
        max_tokens=200,
        extra_headers={
            "HTTP-Referer": "https://localhost:8080",
            "X-Title": "Gold Quantitative Analysis System"
        }
    )
    
    elapsed = time.time() - start_time
    
    print(f"✅ 请求成功！响应时间: {elapsed:.2f}秒")
    
    # 解析响应
    if response.choices and len(response.choices) > 0:
        content = response.choices[0].message.content
        print(f"\n📝 回复内容:\n{content}\n")
        
        print("=" * 60)
        print("🎉 OpenRouter API 测试成功！")
        print("=" * 60)
        print(f"\n💡 建议配置:")
        print(f"  openrouter_model: str = \"{MODEL}\"")
        print(f"  使用 openai 库调用（更稳定）")
        sys.exit(0)
    else:
        print(f"⚠️  响应格式异常: {response}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ 请求失败: {type(e).__name__}: {e}")
    
    # 尝试其他模型
    print(f"\n尝试其他免费模型...")
    free_models = [
        "baidu/cobuddy:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    ]
    
    for model in free_models:
        print(f"\n测试模型: {model}")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "测试"}],
                max_tokens=50
            )
            print(f"✅ 成功！模型 {model} 可用")
            print(f"\n💡 建议配置: openrouter_model: str = \"{model}\"")
            sys.exit(0)
        except Exception as e2:
            print(f"❌ 失败: {e2}")
    
    sys.exit(1)
