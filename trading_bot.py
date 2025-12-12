import sys
import time
from PyQt5.QtWidgets import QApplication
from kiwoom_api import KiwoomAPI
from strategy import BollingerBandStrategy, RSIStrategy, ScalpingStrategy, VolatilityBreakoutStrategy, PositionManager


class TradingBot:
    def adjust_to_tick_size(self, price):
        """호가 단위에 맞춰 가격 조정"""
        if price < 1000:
            return (price // 1) * 1  # 1원 단위
        elif price < 5000:
            return (price // 5) * 5  # 5원 단위
        elif price < 10000:
            return (price // 10) * 10  # 10원 단위
        elif price < 50000:
            return (price // 50) * 50  # 50원 단위
        elif price < 100000:
            return (price // 100) * 100  # 100원 단위
        elif price < 500000:
            return (price // 500) * 500  # 500원 단위
        else:
            return (price // 1000) * 1000  # 1000원 단위
    
    def __init__(self):
        self.api = KiwoomAPI()
        self.position_manager = PositionManager()
        
        # 설정
        self.target_stocks = []  # 모니터링 종목
        self.max_stocks = 8  # 최대 보유 종목 수
        self.investment_per_stock = 1000000  # 종목당 투자금액 (100만원)
        
        # 수익률 설정
        self.profit_target_half = 1.0  # 1% 도달 시 50% 매도
        self.profit_target_full = 1.5  # 1.5% 도달 시 전량 매도
        self.stop_loss = -1.5  # -1.5% 손절
        
        # 매매전략 설정 (1: 볼린저밴드, 2: RSI, 3: 단타, 4: 변동성돌파)
        self.strategy_type = 4  # 기본: 변동성돌파전략 (여기서 변경 가능)
        self.setup_strategy()
        
    def setup_strategy(self):
        """전략 설정"""
        if self.strategy_type == 1:
            self.strategy = BollingerBandStrategy(period=10, std_dev=1.5)
            print("선택된 전략: 볼린저밴드 상단 돌파")
        elif self.strategy_type == 2:
            self.strategy = RSIStrategy(period=14, oversold=30, overbought=70)
            print("선택된 전략: RSI 과매도 반등")
        elif self.strategy_type == 3:
            self.strategy = ScalpingStrategy(volume_threshold=1000000000, price_change_threshold=3.0)
            print("선택된 전략: 단타 전략 (거래대금 급증 + 3% 상승)")
        elif self.strategy_type == 4:
            self.strategy = VolatilityBreakoutStrategy(k_ratio=0.5, volume_multiplier=1.5)
            print("선택된 전략: 래리 윌리엄스 변동성 돌파 (개선버전 - 적응K + 거래량필터 + 트레일링스톱)")
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
        # if self.strategy_type == 3:  # 단타전략은 코스피+코스닥 모두
        #     print("코스피+코스닥 거래대금 상위 종목 조회 중...")
        #     all_stocks = self.api.get_volume_rank(market="000")  # 000 = 전체
        # else:
        print("코스닥 거래대금 상위 종목 조회 중...")
        all_stocks = self.api.get_volume_rank(market="101")  # 101 = 코스닥
        
        try:
            
            # 이미 보유한 종목 및 매수 미체결 종목 제외
            try:
                balance = self.api.get_balance()
                held_stocks = set([stock['code'].replace('A', '') for stock in balance['stocks'] if stock['quantity'] > 0])
                print(f"디버그 - 실제 보유 종목: {held_stocks}")
                
                # 매수 미체결 주문 조회
                buy_orders = self.api.get_not_concluded_orders("2")  # 2:매수
                buy_pending_stocks = set([order['code'].replace('A', '') for order in buy_orders if order.get('code')])
                print(f"디버그 - 매수 미체결 종목: {buy_pending_stocks}")
                
                # 보유 + 미체결 종목 합침
                excluded_stocks = held_stocks | buy_pending_stocks
                print(f"디버그 - 제외 종목 총 {len(excluded_stocks)}개: {excluded_stocks}")
            except:
                held_stocks = set(self.position_manager.get_all_positions().keys())
                excluded_stocks = held_stocks
                print(f"디버그 - 포지션 매니저 보유 종목: {excluded_stocks}")
            
            # 보유하지 않은 종목 중 일봉 데이터가 충분하고 전략 조건을 만족하는 종목만 필터링
            available_stocks = []
            print(f"디버그 - 전체 조회 종목 수: {len(all_stocks)}")
            
            for i, stock in enumerate(all_stocks):
                if i >= 50:  # 상위 50개까지 검사 (더 많은 종목 확인)
                    break
                    
                stock_code = stock['code'].replace('A', '')  # A 접두사 제거
                print(f"디버그 - 검사: {stock['name']}({stock_code}), 거래대금: {stock['trade_amount']:,}")
                
                if stock_code not in excluded_stocks:
                    try:
                        daily_data = self.api.get_daily_data(stock_code)
                        if daily_data and len(daily_data) >= 3:  # 단타는 3일만 필요
                            if self.strategy_type == 3:  # 단타전략
                                # 거래대금 조건 완화 - 상위 20개 중에서 선정
                                stock['code'] = stock_code
                                available_stocks.append(stock)
                                print(f"디버그 - 선정됨: {stock['name']}({stock_code}), 거래대금: {stock['trade_amount']:,}")
                            else:  # 기존 전략
                                if len(daily_data) >= 20:
                                    middle_band = self.strategy.get_buy_signal_price(daily_data)
                                    if middle_band and stock['price'] >= middle_band:
                                        stock['code'] = stock_code
                                        available_stocks.append(stock)
                                        print(f"디버그 - 선정됨: {stock['name']}({stock_code})")
                        if len(available_stocks) >= 20:  # 20개 찾으면 중단
                            break
                    except Exception as e:
                        print(f"디버그 - 오류: {stock['name']} - {e}")
                        continue
                else:
                    if stock_code in held_stocks:
                        print(f"디버그 - 보유중 제외: {stock['name']}({stock_code})")
                    else:
                        print(f"디버그 - 매수미체결 제외: {stock['name']}({stock_code})")
            
            self.target_stocks = [stock['code'] for stock in available_stocks[:20]]
            
            print(f"\n모니터링 대상 {len(self.target_stocks)}개 종목 선정 완료 (제외 종목 {len(excluded_stocks)}개: 보유 {len(held_stocks)}개 + 미체결 {len(excluded_stocks) - len(held_stocks)}개)")
            print("-" * 115)
            print(f"{'순위':<4} {'종목명':<10} {'코드':<8} {'현재가':>12} {'매수신호가':>12} {'거래대금':>15} {'등락률':>8}")
            print("-" * 110)
            
            for i, stock in enumerate(available_stocks[:20], 1):
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
            for stock in available_stocks[:20]:
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
            
        # 실제 계좌 보유 종목 수 확인
        positions = self.position_manager.get_all_positions()  # 기본값 설정
        try:
            balance = self.api.get_balance()
            actual_holdings = len([s for s in balance.get('stocks', []) if s.get('quantity', 0) > 0])
            print(f"디버그 - 실제 보유 종목 수: {actual_holdings}, 최대 보유: {self.max_stocks}")
            if actual_holdings >= self.max_stocks:
                print(f"최대 보유 종목 수 도달 ({actual_holdings}/{self.max_stocks}) - 매수 중단")
                return
        except:
            # 오류 시 기존 방식 사용
            if len(positions) >= self.max_stocks:
                return
            
        for code in self.target_stocks:
            if isinstance(positions, dict) and code in positions:
                continue
                
            try:
                daily_data = self.api.get_daily_data(code)
                if daily_data and self.strategy.check_buy_signal(daily_data):
                    current_price = self.api.get_current_price(code)
                    if current_price > 0:  # 0으로 나누기 방지
                        # 매수 가격을 현재가의 99%로 설정 후 호가단위 조정
                        target_price = int(current_price * 0.99)
                        buy_price = self.adjust_to_tick_size(target_price)
                        quantity = int(self.investment_per_stock / buy_price)
                        
                        if quantity > 0:
                            name = self.api.get_stock_name(code)
                            print(f"\n[매수 신호] {name}({code}): 현재가 {current_price:,}원, 매수가 {buy_price:,}원, {quantity}주")
                            
                            # 매수 주문 (지정가)
                            ret = self.api.send_order("신규매수", "0101", self.api.account_num, 
                                                      1, code, quantity, buy_price, "00")
                            if ret == 0:
                                print("매수 주문 성공")
                                self.position_manager.add_position(code, buy_price, quantity)
                            else:
                                print(f"매수 주문 실패: {ret}")
                            
            except Exception as e:
                print(f"매수 신호 확인 실패 ({code}): {e}")
                
    def show_account_info(self):
        """계좌 정보 출력"""
        try:
            balance = self.api.get_balance()
            
            # 추정자산 계산 (예수금 + 총 평가금액)
            estimated_assets = balance['deposit'] + balance['total_eval']
            
            print("\n" + "="*60)
            print("현재 계좌 상태")
            print("="*60)
            print(f"예수금: {balance['deposit']:,}원")
            print(f"총 평가금액: {balance['total_eval']:,}원")
            print(f"추정자산: {estimated_assets:,}원")
            print(f"총 수익: {balance['total_profit']:,}원 ({balance['total_profit_rate']:.2f}%)")
            print(f"보유 종목 수: {len(balance['stocks'])}개")
            
            if balance['stocks']:
                print("\n[보유 종목]")
                for stock in balance['stocks']:
                    print(f"  {stock['name']}({stock['code']}): {stock['quantity']}주, "
                          f"매수가 {stock['buy_price']:,}원, 현재가 {stock['current_price']:,}원, "
                          f"수익률 {stock['profit_rate']:.2f}%")
            
            # 매수 미체결 주문 표시
            self.api.show_buy_orders()
            
            print("="*60 + "\n")
        except Exception as e:
            print(f"계좌 정보 조회 실패: {e}")
    
    def sell_all_at_close(self):
        """마감 전 모든 보유 종목 매도 (15:18)"""
        try:
            balance = self.api.get_balance()
            if not balance or 'stocks' not in balance:
                return
                
            held_stocks = balance['stocks']
            if not held_stocks:
                print("마감 매도: 보유 종목이 없습니다.")
                return
                
            print(f"\n=== 마감 전 전체 매도 (15:18) ===")
            print(f"보유 종목 {len(held_stocks)}개 전체 매도 시작...")
            
            for stock in held_stocks:
                try:
                    if not isinstance(stock, dict) or stock.get('quantity', 0) <= 0:
                        continue
                        
                    code = str(stock.get('code', '')).replace('A', '')  # A 접두사 제거
                    quantity = stock.get('quantity', 0)
                    name = stock.get('name', '')
                    profit_rate = stock.get('profit_rate', 0)
                    
                    if not code:
                        continue
                        
                    print(f"[마감매도] {name}({code}): {quantity}주, 수익률 {profit_rate:.2f}%")
                    
                    # 시장가 매도 주문
                    ret = self.api.send_order("마감매도", "0102", self.api.account_num,
                                              2, code, quantity, 0, "03")  # 시장가
                    if ret == 0:
                        print(f"마감 매도 주문 성공: {name}")
                        # 포지션 매니저에서 제거
                        self.position_manager.remove_position(code)
                    else:
                        print(f"마감 매도 주문 실패: {name} - 오류코드: {ret}")
                    
                    time.sleep(0.2)  # 주문 간격
                    
                except Exception as stock_error:
                    print(f"마감 매도 오류: {stock_error}")
                    continue
                    
            print("=== 마감 전 전체 매도 완료 ===")
            
        except Exception as e:
            print(f"마감 매도 실패: {e}")
    
    def check_sell_signals(self):
        """매도 신호 확인 - 실제 계좌 보유 종목 기준"""
        # 15:18분에 모든 종목 매도
        current_time = time.strftime("%H%M")
        if current_time == "1525":
            self.sell_all_at_close()
            return
            
        try:
            # 실제 계좌에서 보유 종목 조회
            balance = self.api.get_balance()
            if not balance or 'stocks' not in balance:
                return
                
            held_stocks = balance['stocks']
            if not held_stocks:
                return
                
            print(f"\n[매도 신호 확인] 보유 종목 {len(held_stocks)}개")
            
            for stock in held_stocks:
                try:
                    if not isinstance(stock, dict) or stock.get('quantity', 0) <= 0:
                        continue
                        
                    code = str(stock.get('code', '')).replace('A', '')  # A 접두사 제거
                    current_price = stock.get('current_price', 0)
                    buy_price = stock.get('buy_price', 0)
                    quantity = stock.get('quantity', 0)
                    profit_rate = stock.get('profit_rate', 0)
                    name = stock.get('name', '')
                    
                    if not code or buy_price <= 0:
                        continue
                
                    print(f"{name}({code}): 매수가 {buy_price:,}원, 현재가 {current_price:,}원, 수익률 {profit_rate:.2f}%")
                    print(f"디버그 - 손절기준: {self.stop_loss}%, 현재수익률: {profit_rate:.2f}%, 조건만족: {profit_rate <= self.stop_loss}")
                
                    # 트레일링 스톱 또는 고정 손절
                    try:
                        positions = self.position_manager.get_all_positions()
                        pos = positions.get(code) if isinstance(positions, dict) else None
                    except:
                        pos = None
                    
                    # 트레일링 스톱 로직 (전략-4에만 적용)
                    if self.strategy_type == 4 and pos and profit_rate > 0:
                        # 수익이 날 때 손절선을 올려서 수익 보호
                        trailing_stop = max(self.stop_loss, profit_rate - 2.0)  # 최대 2% 하락 허용
                        if profit_rate <= trailing_stop:
                            print(f"[트레일링 스톱] {name}({code}): {profit_rate:.2f}% (손절선: {trailing_stop:.2f}%)")
                            ret = self.api.send_order("트레일링매도", "0102", self.api.account_num,
                                                      2, code, quantity, 0, "03")  # 시장가
                            if ret == 0:
                                print("트레일링 스톱 매도 성공")
                            continue
                    
                    # 기본 손절: -1.5%
                    if profit_rate <= self.stop_loss:
                        print(f"[손절 매도] {name}({code}): {profit_rate:.2f}%")
                        ret = self.api.send_order("손절매도", "0102", self.api.account_num,
                                                  2, code, quantity, 0, "03")  # 시장가
                        print(f"  디버그 - 손절 주문 결과: {ret}")
                        if ret == 0:
                            print("손절 매도 주문 성공")
                        else:
                            print(f"손절 매도 주문 실패: {ret}")
                            
                    # 전량 매도: +1.5%
                    elif profit_rate >= self.profit_target_full:
                        print(f"[전량 매도] {name}({code}): {profit_rate:.2f}%")
                        ret = self.api.send_order("익절매도", "0102", self.api.account_num,
                                                  2, code, quantity, current_price, "00")
                        if ret == 0:
                            print("전량 매도 주문 성공")
                            
                    # 50% 매도: +1.0% (포지션 매니저에서 이미 50% 매도했는지 확인)
                    elif profit_rate >= self.profit_target_half:
                        # pos가 없을 때만 다시 조회 (이미 위에서 positions를 정의했음)
                        pass  # pos는 이미 위에서 정의됨
                        
                        # 포지션 매니저에 없거나 아직 50% 매도하지 않은 경우
                        if not pos or not pos.get('half_sold', False):
                            half_qty = quantity // 2
                            if half_qty > 0:
                                print(f"[50% 매도] {name}({code}): {profit_rate:.2f}%, {half_qty}주")
                                ret = self.api.send_order("부분매도", "0102", self.api.account_num,
                                                          2, code, half_qty, current_price, "00")
                                if ret == 0:
                                    print("50% 매도 주문 성공")
                                    # 포지션 매니저에 50% 매도 기록
                                    if pos:
                                        self.position_manager.update_half_sold(code)
                                    else:
                                        # 포지션 매니저에 없으면 새로 추가하고 50% 매도 표시
                                        self.position_manager.add_position(code, buy_price, quantity)
                                        self.position_manager.update_half_sold(code)
                                        
                except Exception as stock_error:
                    print(f"종목 처리 오류 ({name if 'name' in locals() else 'Unknown'}): {stock_error}")
                    import traceback
                    traceback.print_exc()
                    continue
                        
        except Exception as e:
            print(f"매도 신호 확인 실패: {e}")
                
    def run(self):
        """트레이딩 봇 실행"""
        print("=" * 50)
        print("키움증권 시스템 트레이딩 봇 시작")
        print("=" * 50)
        
        self.login()
        time.sleep(2)
        
        # 매도 미체결 주문 취소
        self.api.cancel_sell_orders()
        time.sleep(1)
        
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
    parser.add_argument('--strategy', type=int, choices=[1, 2, 3, 4], default=4,
                        help='매매전략 선택 (1: 볼린저밴드, 2: RSI, 3: 단타, 4: 변동성돌파)')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    bot = TradingBot()
    
    # 전략 설정
    if args.strategy != bot.strategy_type:
        bot.change_strategy(args.strategy)
    
    bot.run()
