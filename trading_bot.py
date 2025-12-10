import sys
import time
from PyQt5.QtWidgets import QApplication
from kiwoom_api import KiwoomAPI
from strategy import BollingerBandStrategy, RSIStrategy, PositionManager


class TradingBot:
    def __init__(self):
        self.api = KiwoomAPI()
        self.position_manager = PositionManager()
        
        # 설정
        self.target_stocks = []  # 모니터링 종목
        self.max_stocks = 5  # 최대 보유 종목 수
        self.investment_per_stock = 1000000  # 종목당 투자금액 (100만원)
        
        # 수익률 설정
        self.profit_target_half = 1.0  # 1% 도달 시 50% 매도
        self.profit_target_full = 1.5  # 1.5% 도달 시 전량 매도
        self.stop_loss = -1.5  # -1.5% 손절
        
        # 매매전략 설정 (1: 볼린저밴드, 2: RSI)
        self.strategy_type = 1  # 기본: 볼린저밴드 (여기서 변경 가능)
        self.setup_strategy()
        
    def setup_strategy(self):
        """전략 설정"""
        if self.strategy_type == 1:
            self.strategy = BollingerBandStrategy(period=10, std_dev=1.5)
            print("선택된 전략: 볼린저밴드 상단 돌파")
        elif self.strategy_type == 2:
            self.strategy = RSIStrategy(period=14, oversold=30, overbought=70)
            print("선택된 전략: RSI 과매도 반등")
        else:
            self.strategy = BollingerBandStrategy(period=10, std_dev=1.5)
            print("기본 전략: 볼린저밴드 상단 돌파")
            
    def change_strategy(self, strategy_type):
        """전략 변경"""
        self.strategy_type = strategy_type
        self.setup_strategy()
        
    def login(self):
        """로그인"""
        self.api.comm_connect()
        
    def select_target_stocks(self):
        """코스닥 거래대금 상위 5개 종목 선정 (보유 종목 제외)"""
        print("코스닥 거래대금 상위 종목 조회 중...")
        
        try:
            # 코스닥 거래대금 상위 조회
            kosdaq_stocks = self.api.get_volume_rank(market="101")
            
            # 이미 보유한 종목 제외 (실제 계좌 잠고에서 가져오기)
            try:
                balance = self.api.get_balance()
                held_stocks = set([stock['code'].replace('A', '') for stock in balance['stocks'] if stock['quantity'] > 0])
                print(f"디버그 - 실제 보유 종목: {held_stocks}")
            except:
                held_stocks = set(self.position_manager.get_all_positions().keys())
                print(f"디버그 - 포지션 매니저 보유 종목: {held_stocks}")
            
            # 보유하지 않은 종목 중 일봉 데이터가 충분하고 볼린저밴드 조건을 만족하는 종목만 필터링
            available_stocks = []
            for stock in kosdaq_stocks:
                stock_code = stock['code'].replace('A', '')  # A 접두사 제거
                if stock_code not in held_stocks:
                    try:
                        daily_data = self.api.get_daily_data(stock_code)
                        if daily_data and len(daily_data) >= 20:
                            # 볼린저밴드 중간값 계산
                            middle_band = self.strategy.get_buy_signal_price(daily_data)
                            if middle_band and stock['price'] >= middle_band:
                                stock['code'] = stock_code  # 통일된 코드로 업데이트
                                available_stocks.append(stock)
                        if len(available_stocks) >= 5:  # 5개 찾으면 중단
                            break
                    except:
                        continue
            
            self.target_stocks = [stock['code'] for stock in available_stocks[:5]]
            
            print(f"\n모니터링 대상 {len(self.target_stocks)}개 종목 선정 완료 (보유 종목 {len(held_stocks)}개 제외)")
            print("-" * 115)
            print(f"{'순위':<4} {'종목명':<10} {'코드':<8} {'현재가':>12} {'매수신호가':>12} {'거래대금':>15} {'등락률':>8}")
            print("-" * 110)
            
            for i, stock in enumerate(available_stocks[:5], 1):
                # 매수신호 발생 가격 계산
                try:
                    daily_data = self.api.get_daily_data(stock['code'])
                    if daily_data and len(daily_data) >= 20:
                        buy_signal_price = self.strategy.get_buy_signal_price(daily_data)
                        if buy_signal_price:
                            signal_price_str = f"{buy_signal_price:,}원"
                        else:
                            signal_price_str = "계산실패"
                    else:
                        signal_price_str = "데이터부족"
                except Exception as e:
                    signal_price_str = "오류"
                    
                # 종목명을 10자리로 맞추기
                name_10char = (stock['name'][:10]).ljust(10)
                print(f"{i:<4} {name_10char} {stock['code']:<8} {stock['price']:>9,}원 {signal_price_str:>12} {stock['trade_amount']:>12,}원 {stock['change_rate']:>7.2f}%")
            print("-" * 115)
            
            # 디버깅: 에코프로 상세 정보 출력 (목록 출력 후)
            for stock in available_stocks[:5]:
                if stock['name'] == '에코프로':
                    try:
                        daily_data = self.api.get_daily_data(stock['code'])
                        if daily_data and len(daily_data) >= 20:
                            print(f"\n=== {stock['name']} 디버깅 ===")
                            print(f"일봉 데이터 개수: {len(daily_data)}")
                            print(f"최근 5일 종가: {[row[4] for row in daily_data[:5]]}")
                            
                            # 볼린저밴드 직접 계산
                            prices = [row[4] for row in daily_data]
                            prices.reverse()
                            recent_10_prices = prices[-10:]
                            avg_price = sum(recent_10_prices) / 10
                            std_dev = (sum([(p - avg_price) ** 2 for p in recent_10_prices]) / 10) ** 0.5
                            upper_band = avg_price + (std_dev * 1.5)
                            print(f"10일 평균: {avg_price:,.0f}원")
                            print(f"표준편차: {std_dev:,.0f}")
                            print(f"상단밴드: {upper_band:,.0f}원")
                            print(f"현재가: {stock['price']:,}원")
                            print("=" * 30)
                    except:
                        pass
                    break
                
        except Exception as e:
            print(f"종목 선정 실패: {e}")
            import traceback
            traceback.print_exc()
            self.target_stocks = []
            
    def check_buy_signals(self):
        """매수 신호 확인 (9:10-10:00만 매수)"""
        # 매수 시간 제한 확인
        # current_time = time.strftime("%H%M")
        # if not ("0910" <= current_time <= "1000"):
        #     return
            
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
    import argparse
    
    # 명령행 인수 처리
    parser = argparse.ArgumentParser(description='키움증권 트레이딩 봇')
    parser.add_argument('--strategy', type=int, choices=[1, 2], default=1,
                        help='매매전략 선택 (1: 볼린저밴드, 2: RSI)')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    bot = TradingBot()
    
    # 전략 설정
    if args.strategy != bot.strategy_type:
        bot.change_strategy(args.strategy)
    
    bot.run()
