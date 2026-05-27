#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取算力云API的可用模型列表
"""
import urllib.request
import urllib.error
import json

API_KEY = "YOUR_API_KEY"

print("正在获取算力云模型列表...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

try:
    req = urllib.request.Request(
        "https://api.suanli.cn/v1/models",
        headers=headers,
        method='GET'
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        status_code = response.status
        data = json.loads(response.read().decode('utf-8'))
        
        print(f"✅ 状态码: {status_code}")
        
        models = data.get('data', [])
        print(f"📊 总模型数: {len(models)}\n")
        
        if models:
            print("="*60)
            print("可用的模型列表：")
            print("="*60)
            
            for i, model in enumerate(models[:20], 1):  # 只显示前20个
                model_id = model.get('id', model.get('name', 'N/A'))
                print(f"{i}. {model_id}")
            
            if len(models) > 20:
                print(f"\n... 还有 {len(models) - 20} 个模型未显示")
            
            # 保存完整列表到文件
            output_path = r"C:\Users\21471\WorkBuddy\gold\suanli_models.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(models, f, ensure_ascii=False, indent=2)
            print(f"\n💾 完整模型列表已保存到: {output_path}")
            
            # 查找包含QwQ或qwq的模型
            qwq_models = [m for m in models if 'qwq' in str(m).lower() or '32b' in str(m).lower()]
            if qwq_models:
                print(f"\n💡 找到包含QwQ/32B的模型:")
                for m in qwq_models[:5]:
                    print(f"  {m.get('id', m.get('name', m))}")
        else:
            print("⚠️  未找到任何模型")
            print(f"API响应: {data}")
        
        exit(0)
        
except urllib.error.HTTPError as e:
    print(f"❌ HTTP错误: {e.code} - {e.reason}")
    try:
        error_data = json.loads(e.read().decode('utf-8'))
        print(f"错误详情: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
    except:
        pass
    exit(1)
    
except Exception as e:
    print(f"❌ 错误: {type(e).__name__}: {e}")
    exit(1)
