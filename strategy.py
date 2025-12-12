import numpy as np
import pandas as pd


class BollingerBandStrategy:
    def __init__(self, period=20, std_dev=2):
        """
        볼린저밴드 전략
        period: 이동평균 기간 (기본 20일)
        std_dev: 표준편차 배수 (기본 2)
        """
        self.period = period
        self.std_dev = std_dev
        
    def calculate_bollinger_bands(self, prices):
        """볼린저밴드 계산"""
        if len(prices) < self.period:
            return None, None, None
            
        df = pd.DataFrame(prices, columns=['close'])
        df['middle'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std(ddof=0)  # 모집단 표준편차 사용
        df['upper'] = df['middle'] + (df['std'] * self.std_dev)
        df['lower'] = df['middle'] - (df['std'] * self.std_dev)
        
        # 마지막 유효한 값 반환
        last_idx = df['lower'].last_valid_index()
        if last_idx is not None:
            return df['upper'].iloc[last_idx], df['middle'].iloc[last_idx], df['lower'].iloc[last_idx]
        else:
            return None, None, None
    
    def check_buy_signal(self, daily_data):
        """매수 신호 확인 - 중간값과 상단 사이에서 매수"""
        # 데이터 타입 및 유효성 검사
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < self.period + 1:
            return False
            
        try:
            prices = [row[4] for row in daily_data]  # 종가
            prices.reverse()  # 오래된 순서로
            
            upper, middle, lower = self.calculate_bollinger_bands(prices)
            if upper is None or middle is None:
                return False
                
            current_price = prices[-1]
            
            # 현재 가격이 중간값과 상단 사이에 있을 때 매수
            if middle <= current_price <= upper:
                return True
            return False
        except (TypeError, IndexError, ValueError):
            return False
    
    def get_buy_signal_price(self, daily_data):
        """매수신호 발생 가격 계산 (볼린저밴드 중간값)"""
        # 데이터 타입 및 유효성 검사
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < self.period:
            return None
            
        try:
            # 일봉 데이터에서 종가 추출 (API에서 반환되는 형식: [date, open, high, low, close, volume])
            prices = [row[4] for row in daily_data]  # 종가
            prices.reverse()  # 오래된 순서로 (최신 데이터가 맨 앞에 오므로)
            
            # 볼린저밴드 계산
            upper, middle, lower = self.calculate_bollinger_bands(prices)
            
            if middle and not pd.isna(middle):
                return int(middle)
            else:
                return None
        except Exception as e:
            print(f"볼린저밴드 계산 오류: {e}")
            return None
    
    def calculate_profit_rate(self, buy_price, current_price):
        """수익률 계산"""
        return ((current_price - buy_price) / buy_price) * 100


class RSIStrategy:
    def __init__(self, period=14, oversold=30, overbought=70):
        """
        RSI 전략
        period: RSI 계산 기간 (기본 14일)
        oversold: 과매도 기준 (기본 30)
        overbought: 과매수 기준 (기본 70)
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        
    def calculate_rsi(self, prices):
        """RSI 계산"""
        if len(prices) < self.period + 1:
            return None
            
        try:
            df = pd.DataFrame(prices, columns=['close'])
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
            
            # 0으로 나누기 방지
            loss = loss.replace(0, 0.0001)  # 아주 작은 값으로 대체
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            last_rsi = rsi.iloc[-1]
            return last_rsi if not pd.isna(last_rsi) else None
        except (ZeroDivisionError, ValueError, IndexError):
            return None
    
    def check_buy_signal(self, daily_data):
        """매수 신호 확인 - RSI 과매도 반등"""
        # 데이터 타입 및 유효성 검사
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < self.period + 2:
            return False
            
        try:
            prices = [row[4] for row in daily_data]  # 종가
            prices.reverse()  # 오래된 순서로
            
            current_rsi = self.calculate_rsi(prices)
            prev_rsi = self.calculate_rsi(prices[:-1])
            
            if current_rsi is None or prev_rsi is None:
                return False
                
            # 이전 RSI가 과매도 영역에 있었고, 현재 RSI가 과매도 영역을 벗어난 경우
            if prev_rsi <= self.oversold and current_rsi > self.oversold:
                return True
            return False
        except (TypeError, IndexError, ValueError):
            return False
    
    def get_buy_signal_price(self, daily_data):
        """매수신호 발생 가격 계산 (RSI 30 돌파 가격)"""
        # 데이터 타입 및 유효성 검사
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < self.period:
            return None
            
        try:
            prices = [row[4] for row in daily_data]
            prices.reverse()
            
            current_rsi = self.calculate_rsi(prices)
            if current_rsi is None:
                return None
                
            # RSI 30 근처에서의 가격 추정 (현재가 기준)
            current_price = prices[-1]
            if current_rsi <= 35:  # RSI 35 이하일 때 매수 준비
                return int(current_price * 0.98)  # 현재가의 98%
            else:
                return int(current_price * 0.95)  # 현재가의 95%
        except Exception as e:
            print(f"RSI 계산 오류: {e}")
            return None
    
    def calculate_profit_rate(self, buy_price, current_price):
        """수익률 계산"""
        return ((current_price - buy_price) / buy_price) * 100


class ScalpingStrategy:
    def __init__(self, volume_threshold=1000000000, price_change_threshold=3.0):
        """
        단타 전략 (Strategy-3)
        volume_threshold: 거래대금 임계값 (기본 10억)
        price_change_threshold: 가격 변동 임계값 (기본 3%)
        """
        self.volume_threshold = volume_threshold
        self.price_change_threshold = price_change_threshold
        
    def check_buy_signal(self, daily_data):
        """매수 신호 확인 - 거래대금 급증 + 가격 상승"""
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < 3:
            return False
            
        try:
            # 최근 3일 데이터
            recent_data = daily_data[:3]
            
            # 오늘 데이터
            today = recent_data[0]
            yesterday = recent_data[1]
            
            today_close = today[4]  # 종가
            today_volume = today[5]  # 거래량
            yesterday_close = yesterday[4]
            
            # 가격 상승률 계산
            price_change = ((today_close - yesterday_close) / yesterday_close) * 100
            
            # 단타 조건: 거래량 급증 + 3% 이상 상승
            if (today_volume * today_close > self.volume_threshold and 
                price_change >= self.price_change_threshold):
                return True
                
            return False
        except (TypeError, IndexError, ValueError, ZeroDivisionError):
            return False
    
    def get_buy_signal_price(self, daily_data):
        """매수신호 발생 가격 계산 (현재가 기준)"""
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < 1:
            return None
            
        try:
            current_price = daily_data[0][4]  # 최신 종가
            return int(current_price * 1.01)  # 현재가의 101% (상승 모멘텀 타기)
        except (TypeError, IndexError, ValueError):
            return None
    
    def calculate_profit_rate(self, buy_price, current_price):
        """수익률 계산"""
        if buy_price <= 0:
            return 0
        return ((current_price - buy_price) / buy_price) * 100


class VolatilityBreakoutStrategy:
    def __init__(self, k_ratio=0.5, volume_multiplier=1.5):
        """
        래리 윌리엄스 변동성 돌파전략 (Strategy-4) - 개선버전
        k_ratio: 기본 변동성 비율 (기본 0.5)
        volume_multiplier: 거래량 증가 배수 (기본 1.5배)
        매수: 시가 + (전일 고가 - 전일 저가) * 적응형_K값
        """
        self.k_ratio = k_ratio
        self.volume_multiplier = volume_multiplier
        
    def calculate_adaptive_k(self, daily_data):
        """적응형 K값 계산 - 변동성에 따라 조정"""
        if len(daily_data) < 10:
            return self.k_ratio
            
        try:
            # 최근 10일 변동성 계산
            recent_ranges = []
            for i in range(min(10, len(daily_data))):
                high = daily_data[i][2]
                low = daily_data[i][3]
                recent_ranges.append(high - low)
            
            avg_range = sum(recent_ranges) / len(recent_ranges)
            yesterday_range = daily_data[1][2] - daily_data[1][3]
            
            # 변동성이 평균보다 클 때 K값 증가, 작을 때 감소
            if yesterday_range > avg_range * 1.2:
                return min(self.k_ratio * 0.7, 0.4)  # 변동성 클 때 낮게
            elif yesterday_range < avg_range * 0.8:
                return min(self.k_ratio * 1.3, 0.8)  # 변동성 작을 때 높게
            else:
                return self.k_ratio
        except:
            return self.k_ratio
        
    def check_buy_signal(self, daily_data):
        """매수 신호 확인 - 개선된 변동성 돌파 + 거래량 필터"""
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < 3:
            return False
            
        try:
            # 오늘과 어제 데이터
            today = daily_data[0]  # [date, open, high, low, close, volume]
            yesterday = daily_data[1]
            day_before = daily_data[2]
            
            today_open = today[1]  # 시가
            today_high = today[2]  # 고가
            today_volume = today[5]  # 거래량
            yesterday_high = yesterday[2]  # 전일 고가
            yesterday_low = yesterday[3]   # 전일 저가
            yesterday_volume = yesterday[5]  # 전일 거래량
            
            # 적응형 K값 계산
            adaptive_k = self.calculate_adaptive_k(daily_data)
            
            # 변동성 돌파 가격 계산
            breakout_price = today_open + (yesterday_high - yesterday_low) * adaptive_k
            
            # 거래량 필터: 오늘 거래량이 어제보다 1.5배 이상
            volume_condition = today_volume >= yesterday_volume * self.volume_multiplier
            
            # 변동성 돌파 + 거래량 증가 조건
            if today_high >= breakout_price and volume_condition:
                return True
                
            return False
        except (TypeError, IndexError, ValueError, ZeroDivisionError):
            return False
    
    def get_buy_signal_price(self, daily_data):
        """매수신호 발생 가격 계산 (적응형 변동성 돌파 가격)"""
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) < 2:
            return None
            
        try:
            today = daily_data[0]
            yesterday = daily_data[1]
            
            today_open = today[1]
            yesterday_high = yesterday[2]
            yesterday_low = yesterday[3]
            
            # 적응형 K값 사용
            adaptive_k = self.calculate_adaptive_k(daily_data)
            breakout_price = today_open + (yesterday_high - yesterday_low) * adaptive_k
            return int(breakout_price)
        except (TypeError, IndexError, ValueError):
            return None
    
    def calculate_profit_rate(self, buy_price, current_price):
        """수익률 계산"""
        if buy_price <= 0:
            return 0
        return ((current_price - buy_price) / buy_price) * 100


class PositionManager:
    def __init__(self):
        """포지션 관리"""
        self.positions = {}  # {종목코드: {'buy_price': 가격, 'quantity': 수량, 'half_sold': bool}}
        
    def add_position(self, code, buy_price, quantity):
        """포지션 추가"""
        self.positions[code] = {
            'buy_price': buy_price,
            'quantity': quantity,
            'half_sold': False
        }
        
    def remove_position(self, code):
        """포지션 제거"""
        if code in self.positions:
            del self.positions[code]
            
    def get_position(self, code):
        """포지션 조회"""
        return self.positions.get(code)
    
    def update_half_sold(self, code):
        """50% 매도 완료 표시"""
        if code in self.positions:
            self.positions[code]['half_sold'] = True
            
    def get_all_positions(self):
        """전체 포지션 조회"""
        return self.positions
