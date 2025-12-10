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
