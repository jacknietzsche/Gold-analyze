#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
保存OpenRouter免费模型列表，并测试一个可用模型
"""
import urllib.request
import urllib.error
import json
import time

API_KEY = "YOUR_OPENROUTER_API_KEY"

print("正在获取OpenRouter模型列表...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

try:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers=headers,
        method='GET'
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        # 筛选免费模型
        free_models = [m for m in data.get('data', []) if ':free' in m.get('id', '')]
        
        print(f"✅ 找到 {len(free_models)} 个免费模型")
        
        # 保存完整列表到文件（使用UTF-8编码）
        output_path = r"C:\Users\21471\WorkBuddy\gold\openrouter_free_models.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(free_models, f, ensure_ascii=False, indent=2)
        print(f"💾 完整免费模型列表已保存到: {output_path}\n")
        
        # 显示前10个免费模型
        print("="*60)
        print("可用的免费模型（前10个）：")
        print("="*60)
        for i, model in enumerate(free_models[:10], 1):
            model_id = model.get('id', 'N/A')
            context_length = model.get('context_length', 'N/A')
            print(f"{i}. {model_id} (上下文: {context_length})")
        
        # 测试第一个免费模型
        if free_models:
            test_model = free_models[0]['id']
            print(f"\n{'='*60}")
            print(f"测试模型: {test_model}")
            print(f"{'='*60}")
            
            payload = {
                "model": test_model,
                "messages": [
                    {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
                ],
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            test_req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            print("⏳ 发送测试请求...")
            start_time = time.time()
            
            try:
                with urllib.request.urlopen(test_req, timeout=60) as test_response:
                    elapsed = time.time() - start_time
                    response_data = json.loads(test_response.read().decode('utf-8'))
                    
                    print(f"✅ 测试成功！响应时间: {elapsed:.2f}秒")
                    
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        content = response_data['choices'][0]['message']['content']
                        print(f"\n📝 回复内容:\n{content}\n")
                        
                        # 更新配置文件中的模型名称
                        print(f"💡 建议：将OpenRouter模型名称改为: {test_model}")
                        
            except Exception as e:
                print(f"❌ 测试失败: {e}")
        
        print(f"\n{'='*60}")
        print("建议的OpenRouter配置：")
        print(f"{'='*60}")
        print(f"openrouter_model: str = \"{free_models[0]['id']}\"  # 使用第一个可用的免费模型")
        
        exit(0)
        
except Exception as e:
    print(f"❌ 错误: {type(e).__name__}: {e}")
    exit(1)
