#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取OpenRouter可用的免费模型列表
"""
import urllib.request
import urllib.error
import json

def main():
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
            status_code = response.status
            data = json.loads(response.read().decode('utf-8'))
            
            print(f"✅ 状态码: {status_code}")
            print(f"📊 总模型数: {len(data.get('data', []))}\n")
            
            # 筛选免费模型
            free_models = [m for m in data.get('data', []) if ':free' in m.get('id', '')]
            
            print(f"🆓 免费模型数量: {len(free_models)}\n")
            print("="*60)
            print("可用的免费模型列表：")
            print("="*60)
            
            for i, model in enumerate(free_models[:15], 1):  # 只显示前15个
                model_id = model.get('id', 'N/A')
                context_length = model.get('context_length', 'N/A')
                print(f"{i}. {model_id} (上下文: {context_length})")
            
            if len(free_models) > 15:
                print(f"\n... 还有 {len(free_models) - 15} 个免费模型未显示")
            
            # 保存完整列表到文件
            with open('/c/Users/21471/WorkBuddy/gold/openrouter_free_models.json', 'w', encoding='utf-8') as f:
                json.dump(free_models, f, ensure_ascii=False, indent=2)
            print(f"\n💾 完整免费模型列表已保存到: openrouter_free_models.json")
            
            return 0 if free_models else 1
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} - {e.reason}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"错误详情: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
        except:
            pass
        return 1
        
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
