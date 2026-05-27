#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据服务类 - 整合所有数据相关功能
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from src.config.gold_config import get_config
from src.data.data_provider import DataSourceManager
from src.data.providers.akshare_provider import AkShareDataProvider
from src.data.providers.yinhe_provider import YinheDataProvider
from src.data.providers.goldapi_provider import GoldAPIProvider
from src.data.providers.openbb_provider import OpenBBProvider
from src.data.providers.china_http_provider import ChinaHttpProvider
from src.data.providers.fred_provider import FredProvider
from src.data.providers.sina_provider import SinaFinanceProvider
from src.data.providers.tencent_provider import TencentFinanceProvider
from src.data.data_cleaner import DataCleaner
from src.data.data_quality_monitor import DataQualityMonitor
from src.data.data_fusion import DataFusion
from src.data.data_cross_validator import DataCrossValidator


class DataService:
    """数据服务类"""
    
    def __init__(self):
        self.config = get_config()
        self.data_cleaner = DataCleaner()
        self.quality_monitor = DataQualityMonitor()
        self.data_fusion = DataFusion()
        self.cross_validator = DataCrossValidator()
        self.data_source_manager = self._initialize_data_sources()
    
    def _initialize_data_sources(self) -> DataSourceManager:
        """初始化数据源"""
        providers = []
        
        # 初始化AkShare数据源
        akshare_provider = AkShareDataProvider()
        providers.append(akshare_provider)
        
        # 初始化YinheData数据源
        yinhe_config = {
            'api_key': self.config.data.api_keys.get('yinhe', '')
        }
        yinhe_provider = YinheDataProvider(yinhe_config)
        providers.append(yinhe_provider)
        
        # 初始化Gold-API.com数据源
        goldapi_config = {
            'api_key': self.config.data.api_keys.get('goldapi', '')
        }
        goldapi_provider = GoldAPIProvider(goldapi_config)
        providers.append(goldapi_provider)
        
        # 初始化Yahoo Finance数据源 (已禁用 - 中国网络环境导致C级崩溃)
        # yahoo_provider = YahooFinanceProvider()
        # providers.append(yahoo_provider)
        
        # 初始化ChinaHttp数据源 (国内HTTP直连, 替代yfinance)
        china_http_provider = ChinaHttpProvider()
        providers.append(china_http_provider)
        
        # 初始化FRED数据源 (美联储经济数据 - VIX/国债/CPI/M2/美元指数)
        fred_config = {
            'api_key': self.config.data.api_keys.get('fred', '')
        }
        fred_provider = FredProvider(fred_config)
        providers.append(fred_provider)
        
        # 初始化OpenBB数据源
        openbb_provider = OpenBBProvider()
        providers.append(openbb_provider)
        
        # 初始化新浪财经数据源
        sina_provider = SinaFinanceProvider()
        providers.append(sina_provider)
        
        # 初始化腾讯财经数据源
        tencent_provider = TencentFinanceProvider()
        providers.append(tencent_provider)
        
        # 创建数据源管理器
        manager_config = {
            'source_priority': self.config.data.source_priority
        }
        return DataSourceManager(providers, manager_config)
    
    def get_gold_price(self, symbol: str = "Au99.99", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据"""
        sources_data = {}
        for provider in self.data_source_manager.providers:
            try:
                data = provider.get_gold_price(symbol, period, interval)
                if not data.empty:
                    cleaned_data = self.data_cleaner.clean_price_data(data)
                    if not cleaned_data.empty:
                        sources_data[provider.name] = cleaned_data
                        self.quality_monitor.monitor_data_quality(cleaned_data, 'price', provider.name)
            except Exception as e:
                print(f"[{provider.name}] 获取黄金价格失败: {e}")

        if 'akshare' in sources_data:
            return sources_data['akshare']

        if sources_data:
            return next(iter(sources_data.values()))

        data = self.data_source_manager.get_gold_price(symbol, period, interval)
        if not data.empty:
            cleaned_data = self.data_cleaner.clean_price_data(data)
            if not cleaned_data.empty:
                return cleaned_data
        return data
    
    def get_macro_data(self, indicators: List[str]) -> Dict[str, Any]:
        """获取宏观经济数据"""
        # 从多个数据源获取数据 (按能力路由)
        sources_data = {}
        for provider in self.data_source_manager.providers:
            if not provider.has_capability('macro'):
                continue
            try:
                data = provider.get_macro_data(indicators)
                if data:
                    sources_data[provider.name] = data
            except Exception as e:
                print(f"[{provider.name}] 获取宏观数据失败: {e}")
        
        # 进行交叉验证
        if len(sources_data) >= 2:
            validation_result = self.cross_validator.validate_macro_data(sources_data)
            print(f"宏观数据交叉验证结果: {'通过' if validation_result['valid'] else '失败'}")
            
            # 打印告警信息
            if validation_result['alerts']:
                print("宏观数据交叉验证告警:")
                for alert in validation_result['alerts']:
                    print(f"  [{alert['level'].upper()}] {alert['message']}")
        
        # 融合数据
        if sources_data:
            fused_data = self.data_fusion.fuse_macro_data(sources_data)
            if fused_data:
                return fused_data
        
        # 使用单一数据源
        return self.data_source_manager.get_macro_data(indicators)
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据"""
        # 从多个数据源获取数据 (按能力路由)
        sources_data = {}
        for provider in self.data_source_manager.providers:
            if not provider.has_capability('sentiment'):
                continue
            try:
                data = provider.get_market_sentiment()
                if data:
                    sources_data[provider.name] = data
            except Exception as e:
                print(f"[{provider.name}] 获取市场情绪失败: {e}")
        
        # 进行交叉验证
        if len(sources_data) >= 2:
            validation_result = self.cross_validator.validate_sentiment_data(sources_data)
            print(f"市场情绪数据交叉验证结果: {'通过' if validation_result['valid'] else '失败'}")
            
            # 打印告警信息
            if validation_result['alerts']:
                print("市场情绪数据交叉验证告警:")
                for alert in validation_result['alerts']:
                    print(f"  [{alert['level'].upper()}] {alert['message']}")
        
        # 融合数据
        if sources_data:
            fused_data = self.data_fusion.fuse_sentiment_data(sources_data)
            if fused_data:
                return fused_data
        
        # 使用单一数据源
        return self.data_source_manager.get_market_sentiment()
    
    def get_asset_correlation(self, assets: List[str]) -> pd.DataFrame:
        """获取资产相关性数据"""
        # 从多个数据源获取数据 (按能力路由)
        sources_data = {}
        for provider in self.data_source_manager.providers:
            if not provider.has_capability('correlation'):
                continue
            try:
                data = provider.get_asset_correlation(assets)
                if not data.empty:
                    sources_data[provider.name] = data
            except Exception as e:
                print(f"[{provider.name}] 获取资产相关性失败: {e}")
        
        # 进行交叉验证
        if len(sources_data) >= 2:
            validation_result = self.cross_validator.validate_correlation_data(sources_data)
            print(f"资产相关性数据交叉验证结果: {'通过' if validation_result['valid'] else '失败'}")
            
            # 打印告警信息
            if validation_result['alerts']:
                print("资产相关性数据交叉验证告警:")
                for alert in validation_result['alerts']:
                    print(f"  [{alert['level'].upper()}] {alert['message']}")
        
        # 融合数据
        if sources_data:
            fused_data = self.data_fusion.fuse_correlation_data(sources_data)
            if not fused_data.empty:
                return fused_data
        
        # 使用单一数据源
        return self.data_source_manager.get_asset_correlation(assets)
    
    def get_data_quality_report(self, data_type: str = None) -> Dict[str, Any]:
        """获取数据质量报告"""
        # 获取数据质量报告
        quality_report = self.quality_monitor.generate_quality_report()
        
        # 获取交叉验证报告
        validation_report = self.cross_validator.generate_validation_report(data_type)
        
        # 合并报告
        report = {
            'timestamp': quality_report['timestamp'],
            'data_quality': quality_report,
            'cross_validation': validation_report,
            'summary': {
                'data_quality_score': quality_report.get('summary', {}).get('overall', 0),
                'validation_valid_rate': validation_report.get('summary', {}).get('valid_rate', 0),
                'total_alerts': len(quality_report.get('alerts', [])) + len(validation_report.get('alerts', []))
            }
        }
        
        return report
    
    def validate_data_quality(self, data: pd.DataFrame, data_type: str) -> bool:
        """验证数据质量"""
        quality_metrics = self.quality_monitor.calculate_quality_metrics(data, data_type)
        
        # 检查是否满足最低质量要求
        if quality_metrics['completeness'] < self.config.data.min_data_quality:
            return False
        if quality_metrics['timeliness'] < self.config.data.min_data_quality:
            return False
        if quality_metrics['consistency'] < self.config.data.min_data_quality:
            return False
        
        return True
    
    def get_all_data(self, gold_symbol: str = "Au99.99", period: str = "1y", timeout: int = 120) -> Dict[str, Any]:
        """
        获取所有数据（带超时机制和增强错误处理）
        
        Parameters:
        -----------
        gold_symbol : str
            黄金合约代码
        period : str
            数据周期
        timeout : int
            超时时间（秒），默认120秒
            
        Returns:
        --------
        data : dict
            包含所有获取到的数据，如果超时或出错则返回部分数据
        """
        import time
        start_time = time.time()
        
        def _check_timeout():
            """检查是否超时"""
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"[超时] get_all_data() 执行时间 {elapsed:.1f}s 超过 {timeout}s，返回部分数据")
                return True
            return False
        
        data = {
            'price': None,
            'macro': {},
            'sentiment': {},
            'correlation': pd.DataFrame(),
            'quality_report': {}
        }
        
        # ===== 1. 获取价格数据 =====
        if _check_timeout():
            return data
        
        print(f"[数据获取] 开始获取价格数据... (已用 {time.time()-start_time:.1f}s)")
        price_data = None
        try:
            for provider in self.data_source_manager.providers:
                if provider.name == "akshare":
                    try:
                        price_data = provider.get_gold_price(gold_symbol, period)
                        if not price_data.empty:
                            price_data = self.data_cleaner.clean_price_data(price_data)
                            validation = provider.validate_price_data(price_data, gold_symbol)
                            if not validation['valid']:
                                print(f"[数据校验] AkShare价格数据验证失败: {validation['errors']}")
                                price_data = None
                            elif validation['warnings']:
                                for w in validation['warnings']:
                                    print(f"[数据校验] 警告: {w}")
                            else:
                                break
                    except Exception as e:
                        print(f"[AkShare] 获取黄金价格失败: {e}")
                        import traceback
                        traceback.print_exc()
            
            if price_data is None:
                # 尝试从其他数据源获取数据
                price_data = self.get_gold_price(gold_symbol, period)
                if not price_data.empty:
                    if not self.validate_data_quality(price_data, 'price'):
                        print("[数据质量] 所有数据源价格数据质量均不达标")
                        price_data = pd.DataFrame()
        
            data['price'] = price_data
            print(f"[数据获取] 价格数据获取完成 (已用 {time.time()-start_time:.1f}s)")
        except Exception as e:
            print(f"[错误] 获取价格数据时发生异常: {e}")
            import traceback
            traceback.print_exc()
            data['price'] = None
        
        # ===== 2-4. 并行获取宏观/情绪/相关性数据 =====
        if _check_timeout():
            return data

        print(f"[数据获取] 开始并行获取宏观/情绪/相关性数据... (已用 {time.time()-start_time:.1f}s)")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_macro():
            macro_data = self.get_macro_data([
                'bond_yield', 'vix', 'dollar_index',
                'central_bank_buying', 'china_reserves',
                'cpi', 'm2',
                'tips_yield', 'breakeven_inflation', 'sp500',
                'gold_volatility', 'gold_flows',
                'gold_import_price', 'gold_export_price',
                'china_reserves_ex_gold', 'fed_gold_certificate'
            ])
            if macro_data:
                for provider in self.data_source_manager.providers:
                    if provider.name == "akshare":
                        macro_validation = provider.validate_macro_data(macro_data)
                        if not macro_validation['valid']:
                            print(f"[数据校验] 宏观数据验证失败: {macro_validation['errors']}")
                        break
            return ('macro', macro_data)

        def _fetch_sentiment():
            return ('sentiment', self.get_market_sentiment())

        def _fetch_correlation():
            return ('correlation', self.get_asset_correlation(['gold', 'dollar', 'stock', 'bond']))

        futures = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures[executor.submit(_fetch_macro)] = 'macro'
            futures[executor.submit(_fetch_sentiment)] = 'sentiment'
            futures[executor.submit(_fetch_correlation)] = 'correlation'

            for future in as_completed(futures):
                key = futures[future]
                try:
                    result_key, result_data = future.result()
                    data[result_key] = result_data
                    print(f"[数据获取] {result_key}数据获取完成 (已用 {time.time()-start_time:.1f}s)")
                except Exception as e:
                    print(f"[错误] 获取{key}数据时发生异常: {e}")
                    import traceback
                    traceback.print_exc()
                    if key == 'correlation':
                        data[key] = pd.DataFrame()
                    else:
                        data[key] = {}
        
        # ===== 5. 生成数据质量报告 =====
        if _check_timeout():
            return data
        
        print(f"[数据获取] 开始生成数据质量报告... (已用 {time.time()-start_time:.1f}s)")
        try:
            quality_report = self.get_data_quality_report()
            data['quality_report'] = quality_report
            print(f"[数据获取] 数据质量报告生成完成 (已用 {time.time()-start_time:.1f}s)")
        except Exception as e:
            print(f"[错误] 生成数据质量报告时发生异常: {e}")
            import traceback
            traceback.print_exc()
            data['quality_report'] = {}
        
        total_time = time.time() - start_time
        print(f"[数据获取] get_all_data() 完成，总用时 {total_time:.1f}s")
        
        return data
    
    def refresh_data(self):
        """刷新数据"""
        # 清除缓存
        for provider in self.data_source_manager.providers:
            provider._cache.clear()
        
        print("数据已刷新")
    
    def get_supported_data_sources(self) -> List[str]:
        """获取支持的数据源"""
        return [provider.name for provider in self.data_source_manager.providers]
    
    def get_data_source_status(self) -> Dict[str, Dict[str, Any]]:
        """获取数据源状态"""
        status = {}
        
        for provider in self.data_source_manager.providers:
            try:
                # 测试数据源连接
                test_data = provider.get_gold_price(period="1d")
                is_available = not test_data.empty
                quality = provider.get_data_quality()
            except Exception as e:
                is_available = False
                quality = {'completeness': 0, 'timeliness': 0, 'consistency': 0}
            
            status[provider.name] = {
                'available': is_available,
                'quality': quality
            }
        
        return status
    
    def optimize_data_sources(self):
        """优化数据源选择"""
        # 分析各数据源的质量
        status = self.get_data_source_status()
        
        # 基于质量调整优先级
        sorted_sources = sorted(status.items(), 
                              key=lambda x: sum(x[1]['quality'].values()), 
                              reverse=True)
        
        # 更新优先级
        if sorted_sources:
            top_sources = [s[0] for s in sorted_sources if s[1]['available']]
            if top_sources:
                # 更新价格数据优先级
                self.config.data.source_priority['price'] = top_sources
                self.config.data.source_priority['historical'] = top_sources
                print(f"已优化数据源优先级: {top_sources}")
    
    def generate_data_health_report(self) -> Dict[str, Any]:
        """生成数据健康报告"""
        report = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'data_sources': self.get_data_source_status(),
            'quality_summary': self.get_data_quality_report(),
            'recommendations': []
        }
        
        # 生成建议
        status = report['data_sources']
        for source, info in status.items():
            if not info['available']:
                report['recommendations'].append(f"数据源 {source} 不可用，请检查连接")
            else:
                quality = info['quality']
                if quality['completeness'] < 0.8:
                    report['recommendations'].append(f"数据源 {source} 完整性不足")
                if quality['timeliness'] < 0.8:
                    report['recommendations'].append(f"数据源 {source} 时效性不足")
                if quality['consistency'] < 0.8:
                    report['recommendations'].append(f"数据源 {source} 一致性不足")
        
        return report


# 全局数据服务实例 (懒加载)
_DATA_SERVICE: Optional[DataService] = None


def get_data_service() -> DataService:
    """获取全局DataService单例 (懒加载)"""
    global _DATA_SERVICE
    if _DATA_SERVICE is None:
        _DATA_SERVICE = DataService()
    return _DATA_SERVICE
