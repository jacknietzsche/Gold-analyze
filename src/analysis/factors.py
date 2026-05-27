#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化因子计算模块
实现所有核心因子计算，无机器学习依赖
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from src.analysis.indicators import rsi as _rsi, macd as _macd, atr as _atr, bollinger_bands as _boll

class GoldFactors:
    """黄金量化因子计算器"""
    
    def __init__(self):
        self.factors_data = {}
        
    # ====================== 辅助函数 ======================
    
    def _log_return(self, series):
        """计算对数收益率"""
        return np.log(series / series.shift(1))
    
    def _z_score(self, series):
        """计算z-score标准化"""
        return (series - series.mean()) / series.std()
    
    def _percentile_rank(self, series):
        """计算分位数排名（0-1）"""
        return series.rank(pct=True)
    
    def _get_recent_n(self, series, n=20):
        """获取最近N个有效值"""
        valid_series = series.dropna()
        if len(valid_series) >= n:
            return valid_series.iloc[-n:]
        else:
            return valid_series
    
    def _align_data(self, gold_price_df, factor_series, freq='D'):
        """对齐数据，确保与黄金价格数据时间索引一致"""
        # 创建统一的日期索引
        gold_dates = pd.to_datetime(gold_price_df['date'])
        
        # 将因子数据转换为DataFrame
        factor_df = pd.DataFrame({'date': factor_series.index, 'value': factor_series.values})
        factor_df['date'] = pd.to_datetime(factor_df['date'])
        
        # 使用黄金日期索引重新索引因子数据
        factor_aligned = pd.DataFrame(index=gold_dates)
        factor_aligned = factor_aligned.merge(factor_df, left_index=True, right_on='date', how='left')
        
        # 向前填充缺失值
        factor_aligned['value'] = factor_aligned['value'].ffill()
        
        return factor_aligned['value']
    
    # ====================== 2.1 宏观定价核心因子 ======================
    
    def calculate_real_rate(self, treasury_10y_df, tips_df, gold_price_df):
        """计算实际利率因子"""
        print("\n[因子计算] 计算实际利率因子...")
        
        if treasury_10y_df.empty or tips_df.empty:
            print("[WARN] 缺少美债或TIPS数据")
            return pd.Series()
        
        try:
            # 方法1：直接使用TIPS收益率（负值表示实际利率）
            tips_series = pd.Series(data=tips_df['tips_yield'].values, index=tips_df['date'])
            tips_aligned = self._align_data(gold_price_df, tips_series)
            
            # 方法2：计算名义利率 - 通胀预期（备选）
            if 't10y_yield' in treasury_10y_df.columns:
                t10y_series = pd.Series(data=treasury_10y_df['t10y_yield'].values, index=treasury_10y_df['date'])
                # 这里需要通胀预期数据，暂时用CPI作为代理
                # real_rate = t10y_series - inflation_expectation
                pass
            
            # 使用TIPS收益率作为实际利率代理（取负值）
            real_rate = -tips_aligned
            
            self.factors_data['real_rate'] = real_rate
            print(f"[OK] 实际利率因子计算完成: {len(real_rate.dropna())} 个有效值")
            return real_rate
            
        except Exception as e:
            print(f"[ERR] 计算实际利率因子失败: {e}")
            return pd.Series()
    
    def calculate_dxy_return(self, dxy_df, gold_price_df, period='daily'):
        """计算美元指数变动因子"""
        print("\n[因子计算] 计算美元指数变动因子...")
        
        if dxy_df.empty:
            print("[WARN] 缺少美元指数数据")
            return pd.Series()
        
        try:
            dxy_series = pd.Series(data=dxy_df['dxy'].values, index=dxy_df['date'])
            dxy_aligned = self._align_data(gold_price_df, dxy_series)
            
            if period == 'daily':
                # 日收益率
                dxy_return = self._log_return(dxy_aligned)
            elif period == 'weekly':
                # 周收益率（5日滚动）
                dxy_return = self._log_return(dxy_aligned).rolling(5).sum()
            elif period == 'monthly':
                # 月收益率（20日滚动）
                dxy_return = self._log_return(dxy_aligned).rolling(20).sum()
            
            self.factors_data['dxy_return'] = dxy_return
            print(f"[OK] 美元指数变动因子计算完成: {len(dxy_return.dropna())} 个有效值")
            return dxy_return
            
        except Exception as e:
            print(f"[ERR] 计算美元指数变动因子失败: {e}")
            return pd.Series()
    
    def calculate_inflation_expectation(self, cpi_df, ppi_df, gold_price_df):
        """计算通胀预期因子"""
        print("\n[因子计算] 计算通胀预期因子...")
        
        if cpi_df.empty:
            print("[WARN] 缺少CPI数据")
            return pd.Series()
        
        try:
            cpi_series = pd.Series(data=cpi_df['cpi'].values, index=cpi_df['date'])
            cpi_aligned = self._align_data(gold_price_df, cpi_series)
            
            # 使用CPI同比作为通胀预期代理
            inflation_expectation = cpi_aligned
            
            self.factors_data['inflation_expectation'] = inflation_expectation
            print(f"[OK] 通胀预期因子计算完成: {len(inflation_expectation.dropna())} 个有效值")
            return inflation_expectation
            
        except Exception as e:
            print(f"[ERR] 计算通胀预期因子失败: {e}")
            return pd.Series()
    
    # ====================== 2.2 供需基本面因子 ======================
    
    def calculate_etf_flow(self, etf_df, gold_price_df):
        """计算ETF资金流因子"""
        print("\n[因子计算] 计算ETF资金流因子...")
        
        if etf_df.empty:
            print("[WARN] 缺少ETF数据")
            return pd.Series()
        
        try:
            etf_series = pd.Series(data=etf_df['gld_volume'].values, index=etf_df['date'])
            etf_aligned = self._align_data(gold_price_df, etf_series)
            
            # 计算ETF持仓变动率
            etf_flow = self._log_return(etf_aligned)
            
            # 计算滚动20日累计净流入
            etf_flow_cumulative = etf_flow.rolling(20).sum()
            
            self.factors_data['etf_flow'] = etf_flow
            self.factors_data['etf_flow_cumulative'] = etf_flow_cumulative
            print(f"[OK] ETF资金流因子计算完成: {len(etf_flow.dropna())} 个有效值")
            return etf_flow
            
        except Exception as e:
            print(f"[ERR] 计算ETF资金流因子失败: {e}")
            return pd.Series()
    
    def calculate_seasonal_factor(self, gold_price_df):
        """计算季节性因子（Phase-1修复：统一覆盖10-12月，避免月份重复赋值）"""
        print("\n[因子计算] 计算季节性因子...")
        
        try:
            # 获取日期索引
            dates = pd.to_datetime(gold_price_df['date'])
            seasonal = pd.Series(0, index=dates)
            
            # 黄金消费旺季：
            # - 印度排灯节 (Diwali): 通常10-11月
            # - 中国春节备货:          11-12月
            # - 两者合并 -> 10/11/12月 统一为旺季=1
            # [Phase-1 修复] 原代码两个 for 循环覆盖不同月份，逻辑清晰但重复
            # 改为向量化一次完成，且不遗漏任何月份
            seasonal_months = dates.dt.month.isin([10, 11, 12])
            seasonal[seasonal_months] = 1
            
            self.factors_data['seasonal_factor'] = seasonal
            n_on = seasonal_months.sum()
            print(f"[OK] 季节性因子计算完成: 旺季{n_on}天 / 共{len(seasonal)}天")
            return seasonal
            
        except Exception as e:
            print(f"[ERR] 计算季节性因子失败: {e}")
            return pd.Series()
    
    # ====================== 2.3 风险与情绪因子 ======================
    
    def calculate_vix_shock(self, vix_df, gold_price_df):
        """计算VIX市场恐慌因子"""
        print("\n[因子计算] 计算VIX市场恐慌因子...")
        
        if vix_df.empty:
            print("[WARN] 缺少VIX数据")
            return pd.Series()
        
        try:
            vix_series = pd.Series(data=vix_df['vix'].values, index=vix_df['date'])
            vix_aligned = self._align_data(gold_price_df, vix_series)
            
            # VIX当日涨跌幅
            vix_return = self._log_return(vix_aligned)
            
            # 过去5日累计涨跌幅
            vix_5d_cumulative = vix_return.rolling(5).sum()
            
            self.factors_data['vix_return'] = vix_return
            self.factors_data['vix_5d_cumulative'] = vix_5d_cumulative
            print(f"[OK] VIX市场恐慌因子计算完成: {len(vix_return.dropna())} 个有效值")
            return vix_return
            
        except Exception as e:
            print(f"[ERR] 计算VIX市场恐慌因子失败: {e}")
            return pd.Series()
    
    def calculate_gpr_shock(self, gpr_df, gold_price_df):
        """计算地缘风险冲击因子"""
        print("\n[因子计算] 计算地缘风险冲击因子...")
        
        if gpr_df.empty:
            print("[WARN] 缺少GPR数据")
            return pd.Series()
        
        try:
            gpr_series = pd.Series(data=gpr_df['gpr'].values, index=gpr_df['date'])
            gpr_aligned = self._align_data(gold_price_df, gpr_series)
            
            # 计算GPR偏离度：当日值 - 30日移动平均
            gpr_ma_30 = gpr_aligned.rolling(30).mean()
            gpr_shock = gpr_aligned - gpr_ma_30
            
            self.factors_data['gpr_shock'] = gpr_shock
            print(f"[OK] 地缘风险冲击因子计算完成: {len(gpr_shock.dropna())} 个有效值")
            return gpr_shock
            
        except Exception as e:
            print(f"[ERR] 计算地缘风险冲击因子失败: {e}")
            return pd.Series()
    
    # ====================== 2.4 技术面因子 ======================
    
    def calculate_momentum(self, gold_price_df, periods=[5, 10, 20, 60, 120]):
        """计算趋势动量因子"""
        print("\n[因子计算] 计算趋势动量因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            momentum_factors = {}
            for period in periods:
                # 计算过去N日对数收益率
                momentum = self._log_return(price_series).rolling(period).sum()
                factor_name = f'momentum_{period}d'
                self.factors_data[factor_name] = momentum
                momentum_factors[factor_name] = momentum
                print(f"  - {factor_name}: {len(momentum.dropna())} 个有效值")
            
            return momentum_factors
            
        except Exception as e:
            print(f"[ERR] 计算趋势动量因子失败: {e}")
            return {}
    
    def calculate_ma_trend(self, gold_price_df):
        """计算均线排列因子及均线值"""
        print("\n[因子计算] 计算均线排列因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算移动平均线
            ma5 = price_series.rolling(5).mean()
            ma10 = price_series.rolling(10).mean()
            ma20 = price_series.rolling(20).mean()
            ma60 = price_series.rolling(60).mean()
            
            # 存储均线值供报告使用
            self.factors_data['ma5'] = ma5
            self.factors_data['ma10'] = ma10
            self.factors_data['ma20'] = ma20
            self.factors_data['ma60'] = ma60
            
            # 均线排列判断
            ma_trend = pd.Series(0, index=price_series.index)
            
            # 多头排列: MA5 > MA20 > MA60
            ma_trend[(ma5 > ma20) & (ma20 > ma60)] = 1
            # 空头排列: MA5 < MA20 < MA60
            ma_trend[(ma5 < ma20) & (ma20 < ma60)] = -1
            
            # 金叉判断
            golden_cross = pd.Series(0, index=price_series.index)
            # MA5上穿MA20
            golden_cross[(ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))] = 1
            # MA5下穿MA20
            golden_cross[(ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))] = -1
            
            self.factors_data['ma_trend'] = ma_trend
            self.factors_data['golden_cross'] = golden_cross
            print(f"[OK] 均线排列因子计算完成: {len(ma_trend.dropna())} 个有效值")
            return ma_trend
            
        except Exception as e:
            print(f"[ERR] 计算均线排列因子失败: {e}")
            return pd.Series()
    
    def calculate_rsi(self, gold_price_df, period=14):
        """计算RSI超买超卖因子（委托 indicators.rsi，Wilder EMA）"""
        print("\n[因子计算] 计算RSI超买超卖因子...")
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            rsi = _rsi(price_series, period)
            rsi_sig = pd.Series(0, index=price_series.index)
            rsi_sig[rsi > 70] = -1
            rsi_sig[rsi < 30] = 1
            self.factors_data['rsi'] = rsi
            self.factors_data['rsi_signal'] = rsi_sig
            print(f"[OK] RSI因子计算完成(Wilder EMA): {len(rsi.dropna())} 个有效值")
            return rsi
        except Exception as e:
            print(f"[ERR] 计算RSI因子失败: {e}")
            return pd.Series()
    
    def calculate_atr(self, gold_price_df, period=14):
        """计算ATR波动率因子（委托 indicators.atr）"""
        print("\n[因子计算] 计算ATR波动率因子...")
        try:
            h = pd.Series(data=gold_price_df['high'].values, index=gold_price_df['date'])
            l = pd.Series(data=gold_price_df['low'].values, index=gold_price_df['date'])
            c = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            atr = _atr(h, l, c, period)
            self.factors_data['atr'] = atr
            print(f"[OK] ATR波动率因子计算完成: {len(atr.dropna())} 个有效值")
            return atr
        except Exception as e:
            print(f"[ERR] 计算ATR因子失败: {e}")
            return pd.Series()
    
    def calculate_volatility(self, gold_price_df, period=20):
        """计算历史波动率因子"""
        print("\n[因子计算] 计算历史波动率因子...")
        
        try:
            close_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            log_return = self._log_return(close_series)
            volatility = log_return.rolling(period).std() * np.sqrt(252) * 100  # 年化波动率(%)
            
            self.factors_data['volatility_20d'] = volatility
            print(f"[OK] 20日波动率因子计算完成: {len(volatility.dropna())} 个有效值")
            return volatility
            
        except Exception as e:
            print(f"[ERR] 计算波动率因子失败: {e}")
            return pd.Series()
    
    def calculate_macd(self, gold_price_df, fast=12, slow=26, signal=9):
        """计算MACD指标（委托 indicators.macd）"""
        print("\n[因子计算] 计算MACD指标...")
        try:
            close_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            dif, dea, hist = _macd(close_series, fast, slow, signal)
            self.factors_data['macd_dif'] = dif
            self.factors_data['macd_dea'] = dea
            self.factors_data['macd_hist'] = hist
            print(f"[OK] MACD指标计算完成: {len(hist.dropna())} 个有效值")
            return hist
        except Exception as e:
            print(f"[ERR] 计算MACD指标失败: {e}")
            return pd.Series()
    
    def calculate_bb_signal(self, gold_price_df, period=20, std_dev=2):
        """计算布林带信号因子（委托 indicators.bollinger_bands）"""
        print("\n[因子计算] 计算布林带信号因子...")
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            upper_band, middle_band, lower_band = _boll(price_series, period, std_dev)
            
            # 布林带位置信号
            bb_position = (price_series - lower_band) / (upper_band - lower_band)
            
            # 布林带信号
            bb_signal = pd.Series(0, index=price_series.index)
            # 上穿上轨：超买
            bb_signal[(price_series > upper_band) & (price_series.shift(1) <= upper_band.shift(1))] = -1
            # 下穿下轨：超卖
            bb_signal[(price_series < lower_band) & (price_series.shift(1) >= lower_band.shift(1))] = 1
            
            # 带宽因子
            bb_bandwidth = (upper_band - lower_band) / middle_band
            
            self.factors_data['bb_position'] = bb_position
            self.factors_data['bb_signal'] = bb_signal
            self.factors_data['bb_bandwidth'] = bb_bandwidth
            print(f"[OK] 布林带因子计算完成: {len(bb_position.dropna())} 个有效值")
            return bb_position
            
        except Exception as e:
            print(f"[ERR] 计算布林带因子失败: {e}")
            return pd.Series()
    
    def calculate_trend_strength(self, gold_price_df, fast=20, slow=50):
        """计算短期相对趋势强度因子"""
        print("\n[因子计算] 计算短期相对趋势强度因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算指数移动平均
            ema_fast = price_series.ewm(span=fast, adjust=False).mean()
            ema_slow = price_series.ewm(span=slow, adjust=False).mean()
            
            # 短期相对趋势强度因子
            trend_strength = (ema_fast / ema_slow) - 1
            
            self.factors_data['trend_strength'] = trend_strength
            print(f"[OK] 短期相对趋势强度因子计算完成: {len(trend_strength.dropna())} 个有效值")
            return trend_strength
            
        except Exception as e:
            print(f"[ERR] 计算短期相对趋势强度因子失败: {e}")
            return pd.Series()
    
    def calculate_long_term_deviation(self, gold_price_df, period=200):
        """计算长期价格偏离度因子"""
        print("\n[因子计算] 计算长期价格偏离度因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算200日简单移动平均
            sma_200 = price_series.rolling(period).mean()
            
            # 长期价格偏离度因子
            long_term_deviation = (price_series / sma_200) - 1
            
            self.factors_data['long_term_deviation'] = long_term_deviation
            print(f"[OK] 长期价格偏离度因子计算完成: {len(long_term_deviation.dropna())} 个有效值")
            return long_term_deviation
            
        except Exception as e:
            print(f"[ERR] 计算长期价格偏离度因子失败: {e}")
            return pd.Series()
    
    def calculate_ma_slope(self, gold_price_df, period=20, k=5):
        """计算均线斜率因子"""
        print("\n[因子计算] 计算均线斜率因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算移动平均
            ma = price_series.rolling(period).mean()
            
            # 均线斜率因子
            ma_slope = (ma / ma.shift(k)) - 1
            
            self.factors_data['ma_slope'] = ma_slope
            print(f"[OK] 均线斜率因子计算完成: {len(ma_slope.dropna())} 个有效值")
            return ma_slope
            
        except Exception as e:
            print(f"[ERR] 计算均线斜率因子失败: {e}")
            return pd.Series()
    
    def calculate_donchian_channel(self, gold_price_df, period=20):
        """计算唐奇安通道因子"""
        print("\n[因子计算] 计算唐奇安通道因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            high_series = pd.Series(data=gold_price_df['high'].values, index=gold_price_df['date'])
            low_series = pd.Series(data=gold_price_df['low'].values, index=gold_price_df['date'])
            
            # 计算N日最高价和最低价
            donchian_high = high_series.rolling(period).max()
            donchian_low = low_series.rolling(period).min()
            
            # 区间位置因子
            donchian_position = (price_series - donchian_low) / (donchian_high - donchian_low)
            
            # 突破信号因子
            donchian_breakout = pd.Series(0, index=price_series.index)
            donchian_breakout[(price_series > donchian_high.shift(1))] = 1  # 向上突破
            donchian_breakout[(price_series < donchian_low.shift(1))] = -1  # 向下突破
            
            self.factors_data['donchian_position'] = donchian_position
            self.factors_data['donchian_breakout'] = donchian_breakout
            print(f"[OK] 唐奇安通道因子计算完成: {len(donchian_position.dropna())} 个有效值")
            return donchian_position
            
        except Exception as e:
            print(f"[ERR] 计算唐奇安通道因子失败: {e}")
            return pd.Series()
    
    def calculate_adx(self, gold_price_df, period=14):
        """计算平均趋向指数（ADX）因子"""
        print("\n[因子计算] 计算ADX因子...")
        
        try:
            high_series = pd.Series(data=gold_price_df['high'].values, index=gold_price_df['date'])
            low_series = pd.Series(data=gold_price_df['low'].values, index=gold_price_df['date'])
            close_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算真实波幅（TR）
            tr1 = high_series - low_series
            tr2 = abs(high_series - close_series.shift(1))
            tr3 = abs(low_series - close_series.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # 计算+DM和-DM
            plus_dm = high_series - high_series.shift(1)
            minus_dm = low_series.shift(1) - low_series
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            plus_dm[plus_dm < minus_dm] = 0
            minus_dm[minus_dm < plus_dm] = 0
            
            # Wilder平滑
            tr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()
            plus_dm_smooth = plus_dm.ewm(alpha=1/period, adjust=False).mean()
            minus_dm_smooth = minus_dm.ewm(alpha=1/period, adjust=False).mean()
            
            # 计算+DI和-DI
            plus_di = (plus_dm_smooth / tr_smooth) * 100
            minus_di = (minus_dm_smooth / tr_smooth) * 100
            
            # 计算DX
            dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
            
            # 计算ADX
            adx = dx.ewm(alpha=1/period, adjust=False).mean()
            
            # 趋势确认信号
            trend_confirmation = pd.Series(0, index=adx.index)
            trend_confirmation[adx > 25] = 1  # 趋势行情
            trend_confirmation[adx < 20] = -1  # 震荡市
            
            # ADX斜率因子
            adx_slope = adx - adx.shift(5)
            
            self.factors_data['adx'] = adx
            self.factors_data['trend_confirmation'] = trend_confirmation
            self.factors_data['adx_slope'] = adx_slope
            print(f"[OK] ADX因子计算完成: {len(adx.dropna())} 个有效值")
            return adx
            
        except Exception as e:
            print(f"[ERR] 计算ADX因子失败: {e}")
            return pd.Series()
    
    def calculate_rsi_trend(self, gold_price_df, period=14, ma_period=10):
        """计算RSI趋势因子（Phase-1修复：使用Wilder EMA）"""
        print("\n[因子计算] 计算RSI趋势因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算RSI（Wilder EMA）
            delta = price_series.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta).where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
            avg_loss_safe = avg_loss.replace(0, np.nan)
            rs = avg_gain / avg_loss_safe
            rsi = 100 - (100 / (1 + rs))
            
            # RSI趋势因子：RSI与其自身10日移动平均线的差值
            rsi_ma = rsi.rolling(ma_period).mean()
            rsi_trend = rsi - rsi_ma
            
            self.factors_data['rsi_trend'] = rsi_trend
            print(f"[OK] RSI趋势因子计算完成: {len(rsi_trend.dropna())} 个有效值")
            return rsi_trend
            
        except Exception as e:
            print(f"[ERR] 计算RSI趋势因子失败: {e}")
            return pd.Series()
    
    def calculate_macd_slope(self, gold_price_df, fast=12, slow=26, signal=9):
        """计算MACD柱斜率因子"""
        print("\n[因子计算] 计算MACD柱斜率因子...")
        
        try:
            close_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算MACD
            ema_fast = close_series.ewm(span=fast, adjust=False).mean()
            ema_slow = close_series.ewm(span=slow, adjust=False).mean()
            dif = ema_fast - ema_slow
            dea = dif.ewm(span=signal, adjust=False).mean()
            macd_hist = (dif - dea) * 2
            
            # MACD柱斜率因子
            macd_slope = macd_hist - macd_hist.shift(1)
            
            self.factors_data['macd_slope'] = macd_slope
            print(f"[OK] MACD柱斜率因子计算完成: {len(macd_slope.dropna())} 个有效值")
            return macd_slope
            
        except Exception as e:
            print(f"[ERR] 计算MACD柱斜率因子失败: {e}")
            return pd.Series()
    
    def calculate_stochastic(self, gold_price_df, period=14, d_period=3):
        """计算随机指标（Stochastic）"""
        print("\n[因子计算] 计算随机指标...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            high_series = pd.Series(data=gold_price_df['high'].values, index=gold_price_df['date'])
            low_series = pd.Series(data=gold_price_df['low'].values, index=gold_price_df['date'])
            
            # 计算%K线
            lowest_low = low_series.rolling(period).min()
            highest_high = high_series.rolling(period).max()
            k = 100 * (price_series - lowest_low) / (highest_high - lowest_low)
            
            # 计算%D线
            d = k.rolling(d_period).mean()
            
            self.factors_data['stochastic_k'] = k
            self.factors_data['stochastic_d'] = d
            print(f"[OK] 随机指标计算完成: {len(k.dropna())} 个有效值")
            return k
            
        except Exception as e:
            print(f"[ERR] 计算随机指标失败: {e}")
            return pd.Series()
    
    def calculate_efficiency_ratio(self, gold_price_df, period=10):
        """计算价格运行效率因子（ER）"""
        print("\n[因子计算] 计算价格运行效率因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算N日内的净价格变动绝对值
            net_change = abs(price_series - price_series.shift(period))
            
            # 计算N日内每日绝对波动的累加和
            daily_changes = abs(price_series.diff())
            sum_daily_changes = daily_changes.rolling(period).sum()
            
            # 价格运行效率因子
            efficiency_ratio = net_change / sum_daily_changes
            
            self.factors_data['efficiency_ratio'] = efficiency_ratio
            print(f"[OK] 价格运行效率因子计算完成: {len(efficiency_ratio.dropna())} 个有效值")
            return efficiency_ratio
            
        except Exception as e:
            print(f"[ERR] 计算价格运行效率因子失败: {e}")
            return pd.Series()
    
    def calculate_price_position(self, gold_price_df, period=20):
        """计算价格相对位置因子"""
        print("\n[因子计算] 计算价格相对位置因子...")
        
        try:
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            high_series = pd.Series(data=gold_price_df['high'].values, index=gold_price_df['date'])
            low_series = pd.Series(data=gold_price_df['low'].values, index=gold_price_df['date'])
            
            # 计算N日最高价和最低价
            n_high = high_series.rolling(period).max()
            n_low = low_series.rolling(period).min()
            
            # 价格相对位置因子
            price_position = (price_series - n_low) / (n_high - n_low)
            
            self.factors_data['price_position'] = price_position
            print(f"[OK] 价格相对位置因子计算完成: {len(price_position.dropna())} 个有效值")
            return price_position
            
        except Exception as e:
            print(f"[ERR] 计算价格相对位置因子失败: {e}")
            return pd.Series()
    
    def calculate_atr_related(self, gold_price_df, period=14):
        """计算ATR相关因子"""
        print("\n[因子计算] 计算ATR相关因子...")
        
        try:
            high_series = pd.Series(data=gold_price_df['high'].values, index=gold_price_df['date'])
            low_series = pd.Series(data=gold_price_df['low'].values, index=gold_price_df['date'])
            close_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算真实波幅（TR）
            tr1 = high_series - low_series
            tr2 = abs(high_series - close_series.shift(1))
            tr3 = abs(low_series - close_series.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # 计算ATR
            atr = tr.rolling(period).mean()
            
            # ATR比率因子：当前ATR与过去50日ATR均值的比值
            atr_50d = atr.rolling(50).mean()
            atr_ratio = atr / atr_50d
            
            # 动态止损宽度（2倍ATR）
            stop_loss_width = atr * 2
            
            self.factors_data['atr'] = atr
            self.factors_data['atr_ratio'] = atr_ratio
            self.factors_data['stop_loss_width'] = stop_loss_width
            print(f"[OK] ATR相关因子计算完成: {len(atr.dropna())} 个有效值")
            return atr
            
        except Exception as e:
            print(f"[ERR] 计算ATR相关因子失败: {e}")
            return pd.Series()
    
    def calculate_volatility_structure(self, gold_price_df, short_period=10, long_period=60):
        """计算波动率结构因子"""
        print("\n[因子计算] 计算波动率结构因子...")
        
        try:
            close_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            log_return = self._log_return(close_series)
            
            # 计算短期和长期历史波动率
            hv_short = log_return.rolling(short_period).std() * np.sqrt(252) * 100
            hv_long = log_return.rolling(long_period).std() * np.sqrt(252) * 100
            
            # 波动率结构因子：短期波动率与长期波动率的比值
            volatility_structure = hv_short / hv_long
            
            self.factors_data['volatility_structure'] = volatility_structure
            print(f"[OK] 波动率结构因子计算完成: {len(volatility_structure.dropna())} 个有效值")
            return volatility_structure
            
        except Exception as e:
            print(f"[ERR] 计算波动率结构因子失败: {e}")
            return pd.Series()
    
    def calculate_relative_volume(self, gold_price_df, period=20):
        """计算相对成交量因子"""
        print("\n[因子计算] 计算相对成交量因子...")
        
        try:
            volume_series = pd.Series(data=gold_price_df['volume'].values, index=gold_price_df['date'])
            
            # 计算20日平均成交量
            avg_volume = volume_series.rolling(period).mean()
            
            # 相对成交量因子
            relative_volume = volume_series / avg_volume
            
            self.factors_data['relative_volume'] = relative_volume
            print(f"[OK] 相对成交量因子计算完成: {len(relative_volume.dropna())} 个有效值")
            return relative_volume
            
        except Exception as e:
            print(f"[ERR] 计算相对成交量因子失败: {e}")
            return pd.Series()
    
    def calculate_obv(self, gold_price_df):
        """计算能量潮（OBV）因子"""
        print("\n[因子计算] 计算能量潮（OBV）因子...")
        
        try:
            close_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            volume_series = pd.Series(data=gold_price_df['volume'].values, index=gold_price_df['date'])
            
            # 计算价格变化方向
            price_change = close_series.diff()
            direction = np.sign(price_change)
            direction = direction.fillna(0)
            
            # 计算OBV
            obv = (direction * volume_series).cumsum()
            
            self.factors_data['obv'] = obv
            print(f"[OK] 能量潮（OBV）因子计算完成: {len(obv.dropna())} 个有效值")
            return obv
            
        except Exception as e:
            print(f"[ERR] 计算能量潮（OBV）因子失败: {e}")
            return pd.Series()
    
    def calculate_open_interest_change(self, gold_price_df, period=5):
        """计算持仓量变化率因子"""
        print("\n[因子计算] 计算持仓量变化率因子...")
        
        try:
            # 假设gold_price_df中有持仓量数据
            if 'open_interest' in gold_price_df.columns:
                oi_series = pd.Series(data=gold_price_df['open_interest'].values, index=gold_price_df['date'])
                
                # 计算过去一周持仓量的净变化
                oi_change = (oi_series / oi_series.shift(period)) - 1
                
                self.factors_data['open_interest_change'] = oi_change
                print(f"[OK] 持仓量变化率因子计算完成: {len(oi_change.dropna())} 个有效值")
                return oi_change
            else:
                print("[WARN] 缺少持仓量数据")
                return pd.Series()
                
        except Exception as e:
            print(f"[ERR] 计算持仓量变化率因子失败: {e}")
            return pd.Series()
    
    def calculate_etf_holdings_change(self, etf_data, gold_price_df, period=5):
        """计算ETF持仓变化因子"""
        print("\n[因子计算] 计算ETF持仓变化因子...")
        
        try:
            if etf_data.empty:
                print("[WARN] 缺少ETF数据")
                return pd.Series()
            
            # 假设etf_data中有持仓数据
            if 'holdings' in etf_data.columns:
                holdings_series = pd.Series(data=etf_data['holdings'].values, index=etf_data['date'])
                holdings_aligned = self._align_data(gold_price_df, holdings_series)
                
                # 计算持仓变化率
                etf_holdings_change = (holdings_aligned / holdings_aligned.shift(period)) - 1
                
                self.factors_data['etf_holdings_change'] = etf_holdings_change
                print(f"[OK] ETF持仓变化因子计算完成: {len(etf_holdings_change.dropna())} 个有效值")
                return etf_holdings_change
            else:
                print("[WARN] 缺少ETF持仓数据")
                return pd.Series()
                
        except Exception as e:
            print(f"[ERR] 计算ETF持仓变化因子失败: {e}")
            return pd.Series()
    
    def z_score_standardize(self, factor_series, window=252):
        """Z-Score标准化"""
        try:
            # 滚动窗口标准化
            rolling_mean = factor_series.rolling(window=window).mean()
            rolling_std = factor_series.rolling(window=window).std()
            z_score = (factor_series - rolling_mean) / rolling_std
            return z_score
        except Exception as e:
            print(f"[ERR] Z-Score标准化失败: {e}")
            return factor_series
    
    def percentile_standardize(self, factor_series, window=252):
        """百分位排名标准化"""
        try:
            # 滚动窗口百分位排名
            def percentile_rank(series):
                return series.rank(pct=True).iloc[-1]
            
            percentile = factor_series.rolling(window=window).apply(percentile_rank, raw=False)
            return percentile
        except Exception as e:
            print(f"[ERR] 百分位排名标准化失败: {e}")
            return factor_series
    
    def standardize_all_factors(self, window=252):
        """标准化所有因子"""
        print("\n[因子标准化] 标准化所有因子...")
        
        try:
            standardized_factors = {}
            for factor_name, factor_series in self.factors_data.items():
                if isinstance(factor_series, pd.Series) and len(factor_series.dropna()) > window:
                    # 对每个因子进行Z-Score标准化
                    z_score = self.z_score_standardize(factor_series, window)
                    standardized_factors[f"{factor_name}_zscore"] = z_score
                    
                    # 对每个因子进行百分位排名标准化
                    percentile = self.percentile_standardize(factor_series, window)
                    standardized_factors[f"{factor_name}_percentile"] = percentile
            
            # 将标准化后的因子添加到factors_data中
            for factor_name, factor_series in standardized_factors.items():
                self.factors_data[factor_name] = factor_series
            
            print(f"[OK] 因子标准化完成，共标准化 {len(standardized_factors)} 个因子")
            return standardized_factors
            
        except Exception as e:
            print(f"[ERR] 因子标准化失败: {e}")
            return {}
    
    # ====================== 综合因子计算 ======================
    
    def calculate_all_factors(self, gold_price_df, data_dict):
        """计算所有因子"""
        print("=" * 60)
        print("黄金量化因子计算 - 全面因子计算")
        print("=" * 60)
        
        # 重置因子数据
        self.factors_data = {}
        
        try:
            # 2.1 宏观定价核心因子
            real_rate = self.calculate_real_rate(
                data_dict['macro']['treasury_10y'],
                data_dict['macro']['tips'],
                gold_price_df
            )
            
            dxy_return = self.calculate_dxy_return(
                data_dict['macro']['dxy'],
                gold_price_df,
                period='daily'
            )
            
            inflation_exp = self.calculate_inflation_expectation(
                data_dict['macro']['cpi'],
                data_dict['macro']['ppi'],
                gold_price_df
            )
            
            # 2.2 供需基本面因子
            etf_flow = self.calculate_etf_flow(
                data_dict['risk']['etf'],
                gold_price_df
            )
            
            seasonal_factor = self.calculate_seasonal_factor(gold_price_df)
            
            # 2.3 风险与情绪因子
            vix_shock = self.calculate_vix_shock(
                data_dict['risk']['vix'],
                gold_price_df
            )
            
            gpr_shock = self.calculate_gpr_shock(
                data_dict['risk']['gpr'],
                gold_price_df
            )
            
            # 2.4 技术面因子
            momentum_factors = self.calculate_momentum(gold_price_df)
            ma_trend = self.calculate_ma_trend(gold_price_df)
            rsi = self.calculate_rsi(gold_price_df)
            rsi_trend = self.calculate_rsi_trend(gold_price_df)
            atr = self.calculate_atr(gold_price_df)
            atr_related = self.calculate_atr_related(gold_price_df)
            bb_signal = self.calculate_bb_signal(gold_price_df)
            volatility = self.calculate_volatility(gold_price_df)
            volatility_structure = self.calculate_volatility_structure(gold_price_df)
            macd = self.calculate_macd(gold_price_df)
            macd_slope = self.calculate_macd_slope(gold_price_df)
            stochastic = self.calculate_stochastic(gold_price_df)
            efficiency_ratio = self.calculate_efficiency_ratio(gold_price_df)
            price_position = self.calculate_price_position(gold_price_df)
            trend_strength = self.calculate_trend_strength(gold_price_df)
            long_term_deviation = self.calculate_long_term_deviation(gold_price_df)
            ma_slope = self.calculate_ma_slope(gold_price_df)
            donchian_channel = self.calculate_donchian_channel(gold_price_df)
            adx = self.calculate_adx(gold_price_df)
            relative_volume = self.calculate_relative_volume(gold_price_df)
            obv = self.calculate_obv(gold_price_df)
            open_interest_change = self.calculate_open_interest_change(gold_price_df)
            etf_holdings_change = self.calculate_etf_holdings_change(data_dict['risk']['etf'], gold_price_df)
            
            # 因子标准化
            self.standardize_all_factors()
            
            # 汇总因子数据
            factor_summary = {}
            for key, value in self.factors_data.items():
                if isinstance(value, pd.Series) and len(value.dropna()) > 0:
                    factor_summary[key] = {
                        'n_valid': len(value.dropna()),
                        'latest': value.dropna().iloc[-1] if len(value.dropna()) > 0 else None
                    }
            
            print("\n[完成] 因子计算完成")
            print("-" * 60)
            print(f"总计因子数量: {len(factor_summary)}")
            for factor_name, factor_info in factor_summary.items():
                print(f"  - {factor_name}: {factor_info['n_valid']} 个有效值")
            
            return self.factors_data
            
        except Exception as e:
            print(f"[ERR] 计算因子失败: {e}")
            return {}
    
    def get_factor_data(self, factor_name=None):
        """获取因子数据"""
        if factor_name:
            return self.factors_data.get(factor_name, pd.Series())
        else:
            return self.factors_data


if __name__ == '__main__':
    print("黄金因子计算模块 — 运行 pytest tests/test_factors.py 进行测试")