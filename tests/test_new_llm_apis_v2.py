#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新增的两个LLM API配置 - 修正版
尝试不同的模型名称
"""

import urllib.request
import urllib.error
import json
import time

def test_api(base_url, api_key, model, api_name):
    """测试单个API"""
    print(f"\n{'='*60}")
    print(f"测试 {api_name}")
    print(f"URL: {base_url}")
    print(f"Model: {model}")
    print(f"{'='*60}")
    
    # 构建请求
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "请用一句话介绍黄金投资的基本原则。"}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        # 创建请求
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        # 发送请求
        start_time = time.time()
        print("⏳ 发送请求...")
        
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
                
                return True
            else:
                print(f"⚠️  响应格式异常: {response_data}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} - {e.reason}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"   错误详情: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
        except:
            pass
        return False
        
    except urllib.error.URLError as e:
        print(f"❌ URL错误: {e.reason}")
        return False
        
    except Exception as e:
        print(f"❌ 未知错误: {type(e).__name__}: {e}")
        return False

def main():
    """主测试函数"""
    print("="*60)
    print("LLM API 配置测试 - 修正版")
    print("="*60)
    
    # 测试1: 算力云 API - 尝试不同的模型名称
    print("\n【测试1】算力云 API - 尝试多个模型名称")
    suanli_models = [
        "free:QwQ-32B",
        "QwQ-32B",
        "qwq-32b",
        "free:qwq-32b",
    ]
    
    suanli_success = False
    for model in suanli_models:
        if test_api(
            base_url="https://api.suanli.cn/v1",
            api_key="YOUR_API_KEY",
            model=model,
            api_name=f"算力云 API ({model})"
        ):
            suanli_success = True
            break
        
        print(f"\n⏸️  等待2秒后尝试下一个模型...")
        time.sleep(2)
    
    # 等待一下，避免速率限制
    if suanli_success:
        print("\n⏸️  等待3秒...")
        time.sleep(3)
    
    # 测试2: OpenRouter API - 尝试不同的模型名称
    print("\n\n【测试2】OpenRouter API - 尝试多个模型名称")
    openrouter_models = [
        "tencent/hy3-preview:free",
        "google/glm-4-32b:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "microsoft/phi-3-medium-128k-instruct:free",
    ]
    
    openrouter_success = False
    for model in openrouter_models:
        if test_api(
            base_url="https://openrouter.ai/api/v1",
            api_key="YOUR_OPENROUTER_API_KEY",
            model=model,
            api_name=f"OpenRouter API ({model})"
        ):
            openrouter_success = True
            break
        
        print(f"\n⏸️  等待2秒后尝试下一个模型...")
        time.sleep(2)
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print(f"算力云 API: {'✅ 成功' if suanli_success else '❌ 失败'}")
    print(f"OpenRouter API: {'✅ 成功' if openrouter_success else '❌ 失败'}")
    print(f"{'='*60}")
    
    if suanli_success and openrouter_success:
        print("\n🎉 所有API测试通过！可以集成到黄金量化系统中。")
        return 0
    else:
        print("\n⚠️  部分API测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    exit(main())
