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
        df['std'] = df['close'].rolling(window=self.period).std()
        df['upper'] = df['middle'] + (df['std'] * self.std_dev)
        df['lower'] = df['middle'] - (df['std'] * self.std_dev)
        
        return df['upper'].iloc[-1], df['middle'].iloc[-1], df['lower'].iloc[-1]
    
    def check_buy_signal(self, daily_data):
        """매수 신호 확인 - 하단 밴드 돌파"""
        if len(daily_data) < self.period + 1:
            return False
            
        prices = [row[4] for row in daily_data]  # 종가
        prices.reverse()  # 오래된 순서로
        
        upper, middle, lower = self.calculate_bollinger_bands(prices[:-1])
        if upper is None:
            return False
            
        current_price = prices[-1]
        prev_price = prices[-2]
        
        # 이전 가격이 하단 밴드 위에 있었고, 현재 가격이 하단 밴드를 돌파한 경우
        if prev_price > lower and current_price <= lower:
            return True
        return False
    
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
