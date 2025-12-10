import sys
import time
from PyQt5.QtWidgets import QApplication
from kiwoom_api import KiwoomAPI
from strategy import BollingerBandStrategy, PositionManager


class TradingBot:
    def __init__(self):
        self.api = KiwoomAPI()
        self.strategy = BollingerBandStrategy(period=20, std_dev=2)
        self.position_manager = PositionManager()
        
        # 설정
        self.target_stocks = []  # 모니터링 종목
        self.max_stocks = 5  # 최대 보유 종목 수
        self.investment_per_stock = 1000000  # 종목당 투자금액 (100만원)
        
        # 수익률 설정
        self.profit_target_half = 1.0  # 1% 도달 시 50% 매도
        self.profit_target_full = 1.5  # 1.5% 도달 시 전량 매도
        self.stop_loss = -1.5  # -1.5% 손절
        
    def login(self):
        """로그인"""
        self.api.comm_connect()
        
    def select_target_stocks(self):
        """코스닥 거래대금 상위 15개 종목 선정"""
        print("코스닥 거래대금 상위 종목 조회 중...")
        
        try:
            # 코스닥 거래대금 상위 조회
            kosdaq_stocks = self.api.get_volume_rank(market="101")
            
            # 상위 15개 선정
            self.target_stocks = [stock['code'] for stock in kosdaq_stocks[:15]]
            
            print(f"\n모니터링 대상 {len(self.target_stocks)}개 종목 선정 완료")
            for stock in kosdaq_stocks[:15]:
                print(f"{stock['name']}({stock['code']}): {stock['price']:,}원, 거래대금: {stock['trade_amount']:,}원, 등락률: {stock['change_rate']:.2f}%")
                
        except Exception as e:
            print(f"종목 선정 실패: {e}")
            import traceback
            traceback.print_exc()
            self.target_stocks = []
            
    def check_buy_signals(self):
        """매수 신호 확인"""
        positions = self.position_manager.get_all_positions()
        if len(positions) >= self.max_stocks:
            return
            
        for code in self.target_stocks:
            if code in positions:
                continue
                
            try:
                daily_data = self.api.get_daily_data(code)
                if self.strategy.check_buy_signal(daily_data):
                    current_price = self.api.get_current_price(code)
                    quantity = int(self.investment_per_stock / current_price)
                    
                    if quantity > 0:
                        name = self.api.get_stock_name(code)
                        print(f"\n[매수 신호] {name}({code}): {current_price:,}원, {quantity}주")
                        
                        # 매수 주문
                        ret = self.api.send_order("신규매수", "0101", self.api.account_num, 
                                                  1, code, quantity, current_price, "00")
                        if ret == 0:
                            print("매수 주문 성공")
                            self.position_manager.add_position(code, current_price, quantity)
                        else:
                            print(f"매수 주문 실패: {ret}")
                            
            except Exception as e:
                print(f"매수 신호 확인 실패 ({code}): {e}")
                
    def show_account_info(self):
        """계좌 정보 출력"""
        try:
            balance = self.api.get_balance()
            
            print("\n" + "="*60)
            print("현재 계좌 상태")
            print("="*60)
            print(f"예수금: {balance['deposit']:,}원")
            print(f"총 평가금액: {balance['total_eval']:,}원")
            print(f"총 수익: {balance['total_profit']:,}원 ({balance['total_profit_rate']:.2f}%)")
            print(f"보유 종목 수: {len(balance['stocks'])}개")
            
            if balance['stocks']:
                print("\n[보유 종목]")
                for stock in balance['stocks']:
                    print(f"  {stock['name']}({stock['code']}): {stock['quantity']}주, "
                          f"매수가 {stock['buy_price']:,}원, 현재가 {stock['current_price']:,}원, "
                          f"수익률 {stock['profit_rate']:.2f}%")
            print("="*60 + "\n")
        except Exception as e:
            print(f"계좌 정보 조회 실패: {e}")
    
    def check_sell_signals(self):
        """매도 신호 확인"""
        positions = self.position_manager.get_all_positions()
        
        for code, pos in list(positions.items()):
            try:
                current_price = self.api.get_current_price(code)
                profit_rate = self.strategy.calculate_profit_rate(pos['buy_price'], current_price)
                
                name = self.api.get_stock_name(code)
                print(f"{name}({code}): 매수가 {pos['buy_price']:,}원, 현재가 {current_price:,}원, 수익률 {profit_rate:.2f}%")
                
                # 손절: -1.5%
                if profit_rate <= self.stop_loss:
                    print(f"[손절 매도] {name}({code}): {profit_rate:.2f}%")
                    ret = self.api.send_order("손절매도", "0102", self.api.account_num,
                                              2, code, pos['quantity'], 0, "03")  # 시장가
                    if ret == 0:
                        self.position_manager.remove_position(code)
                        
                # 전량 매도: +1.5%
                elif profit_rate >= self.profit_target_full:
                    print(f"[전량 매도] {name}({code}): {profit_rate:.2f}%")
                    ret = self.api.send_order("익절매도", "0102", self.api.account_num,
                                              2, code, pos['quantity'], current_price, "00")
                    if ret == 0:
                        self.position_manager.remove_position(code)
                        
                # 50% 매도: +1.0%
                elif profit_rate >= self.profit_target_half and not pos['half_sold']:
                    half_qty = pos['quantity'] // 2
                    print(f"[50% 매도] {name}({code}): {profit_rate:.2f}%, {half_qty}주")
                    ret = self.api.send_order("부분매도", "0102", self.api.account_num,
                                              2, code, half_qty, current_price, "00")
                    if ret == 0:
                        self.position_manager.update_half_sold(code)
                        pos['quantity'] -= half_qty
                        
            except Exception as e:
                print(f"매도 신호 확인 실패 ({code}): {e}")
                
    def run(self):
        """트레이딩 봇 실행"""
        print("=" * 50)
        print("키움증권 시스템 트레이딩 봇 시작")
        print("전략: 볼린저밴드 돌파")
        print("=" * 50)
        
        self.login()
        time.sleep(2)
        
        self.select_target_stocks()
        
        print("\n자동매매 시작...")
        iteration = 0
        
        while True:
            try:
                iteration += 1
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 반복 #{iteration}")
                
                # 계좌 정보 출력
                self.show_account_info()
                
                # 매수 신호 확인
                self.check_buy_signals()
                
                # 매도 신호 확인
                self.check_sell_signals()
                
                # 30초 대기
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\n프로그램 종료")
                break
            except Exception as e:
                print(f"오류 발생: {e}")
                time.sleep(10)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    bot = TradingBot()
    bot.run()
