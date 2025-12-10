import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop
import time


class KiwoomAPI:
    def __init__(self):
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self._event_connect)
        self.ocx.OnReceiveTrData.connect(self._receive_tr_data)
        self.ocx.OnReceiveChejanData.connect(self._receive_chejan_data)
        
        self.login_event_loop = QEventLoop()
        self.tr_event_loop = QEventLoop()
        
        self.account_num = None
        self.tr_data = {}
        
    def comm_connect(self):
        """로그인"""
        self.ocx.dynamicCall("CommConnect()")
        self.login_event_loop.exec_()
        
    def _event_connect(self, err_code):
        if err_code == 0:
            print("로그인 성공")
            self.account_num = self.get_login_info("ACCNO").split(';')[0]
            print(f"계좌번호: {self.account_num}")
        else:
            print("로그인 실패")
        self.login_event_loop.exit()
        
    def get_login_info(self, tag):
        return self.ocx.dynamicCall("GetLoginInfo(QString)", tag)
    
    def set_input_value(self, id, value):
        self.ocx.dynamicCall("SetInputValue(QString, QString)", id, value)
        
    def comm_rq_data(self, rqname, trcode, next, screen_no):
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)", 
                            rqname, trcode, next, screen_no)
        self.tr_event_loop.exec_()
        
    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        if rqname == "주식기본정보":
            cnt = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
            for i in range(cnt):
                code = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                           trcode, rqname, i, "종목코드").strip()
                name = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                           trcode, rqname, i, "종목명").strip()
                self.tr_data[code] = name
                
        elif rqname == "일봉데이터":
            cnt = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
            data = []
            for i in range(cnt):
                date = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                           trcode, rqname, i, "일자").strip()
                open_price = int(self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                                      trcode, rqname, i, "시가").strip())
                high = int(self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                                trcode, rqname, i, "고가").strip())
                low = int(self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                               trcode, rqname, i, "저가").strip())
                close = int(self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                                 trcode, rqname, i, "현재가").strip())
                volume = int(self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                                  trcode, rqname, i, "거래량").strip())
                data.append([date, open_price, high, low, close, volume])
            self.tr_data = data
            
        elif rqname == "현재가":
            current_price = int(self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", 
                                                     trcode, rqname, 0, "현재가").strip())
            self.tr_data = current_price
            
        elif rqname == "계좌평가잔고내역요청":
            deposit = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "예수금").strip()
            if not deposit:
                deposit = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "d+2예수금").strip()
            total_buy = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "총매입금액").strip()
            total_eval = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "총평가금액").strip()
            total_profit = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "총평가손익금액").strip()
            total_profit_rate = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "총수익률(%)").strip()
            
            cnt = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
            stocks = []
            for i in range(cnt):
                code = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목번호").strip()
                name = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목명").strip()
                quantity = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "보유수량").strip()
                buy_price = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "매입가").strip()
                current_price = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가").strip()
                profit = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "평가손익").strip()
                profit_rate = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "수익률(%)").strip()
                
                stocks.append({
                    'code': code,
                    'name': name,
                    'quantity': int(quantity) if quantity else 0,
                    'buy_price': int(buy_price) if buy_price else 0,
                    'current_price': abs(int(current_price)) if current_price else 0,
                    'profit': int(profit) if profit else 0,
                    'profit_rate': float(profit_rate) if profit_rate else 0.0
                })
            
            try:
                deposit_val = int(deposit) if deposit else 0
                total_buy_val = abs(int(total_buy)) if total_buy else 0
                total_eval_val = abs(int(total_eval)) if total_eval else 0
                total_profit_val = int(total_profit) if total_profit else 0
                total_profit_rate_val = float(total_profit_rate) if total_profit_rate else 0.0
            except:
                deposit_val = 0
                total_buy_val = 0
                total_eval_val = 0
                total_profit_val = 0
                total_profit_rate_val = 0.0
            
            self.tr_data = {
                'deposit': deposit_val,
                'total_buy': total_buy_val,
                'total_eval': total_eval_val,
                'total_profit': total_profit_val,
                'total_profit_rate': total_profit_rate_val,
                'stocks': stocks
            }
            
        elif rqname == "거래대금상위":
            cnt = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
            stocks = []
            for i in range(cnt):
                code = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목코드").strip()
                name = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목명").strip()
                current_price = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가").strip()
                trade_amount = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "거래대금").strip()
                change_rate = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "등락률").strip()
                
                stocks.append({
                    'code': code,
                    'name': name,
                    'price': abs(int(current_price)) if current_price else 0,
                    'trade_amount': int(trade_amount) if trade_amount else 0,
                    'change_rate': float(change_rate) if change_rate else 0.0
                })
            self.tr_data = stocks
            
        self.tr_event_loop.exit()
        
    def get_kosdaq_codes(self):
        """코스닥 종목 코드 리스트"""
        codes = self.ocx.dynamicCall("GetCodeListByMarket(QString)", "10")
        return codes.split(';')[:-1]
    
    def get_stock_name(self, code):
        """종목명 조회"""
        return self.ocx.dynamicCall("GetMasterCodeName(QString)", code)
    
    def get_daily_data(self, code, days=100):
        """일봉 데이터 조회"""
        self.set_input_value("종목코드", code)
        self.set_input_value("기준일자", time.strftime("%Y%m%d"))
        self.set_input_value("수정주가구분", "1")
        self.comm_rq_data("일봉데이터", "opt10081", 0, "0101")
        time.sleep(1.0)
        return self.tr_data
    
    def get_current_price(self, code):
        """현재가 조회"""
        self.set_input_value("종목코드", code)
        self.comm_rq_data("현재가", "opt10001", 0, "0102")
        time.sleep(1.0)
        return self.tr_data
    
    def send_order(self, rqname, screen_no, acc_no, order_type, code, qty, price, hoga, order_no=""):
        """주문 전송
        order_type: 1-신규매수, 2-신규매도, 3-매수취소, 4-매도취소, 5-매수정정, 6-매도정정
        hoga: 00-지정가, 03-시장가
        """
        ret = self.ocx.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                   [rqname, screen_no, acc_no, order_type, code, qty, price, hoga, order_no])
        return ret
    
    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        """체결/잔고 데이터 수신"""
        if gubun == "0":  # 체결
            print("=== 체결 통보 ===")
            code = self.ocx.dynamicCall("GetChejanData(int)", 9001).strip()
            order_status = self.ocx.dynamicCall("GetChejanData(int)", 913).strip()
            order_qty = self.ocx.dynamicCall("GetChejanData(int)", 900).strip()
            order_price = self.ocx.dynamicCall("GetChejanData(int)", 901).strip()
            print(f"종목코드: {code}, 상태: {order_status}, 수량: {order_qty}, 가격: {order_price}")
            
    def get_balance(self):
        """잔고 조회
            password:모의투자는 0000
        """
        self.set_input_value("계좌번호", self.account_num)
        self.set_input_value("비밀번호", "")  # 빈 문자열 = 저장된 비밀번호 사용
        self.set_input_value("비밀번호입력매체구분", "00")
        self.set_input_value("조회구분", "1")
        self.comm_rq_data("계좌평가잔고내역요청", "opw00018", 0, "0103")
        time.sleep(1.0)
        return self.tr_data
    
    def get_volume_rank(self, market="101"):
        """거래대금 상위 종목 조회 (opt10032)
        market: 000-전체, 001-코스피, 101-코스닥
        """
        self.set_input_value("시장구분", market)
        self.set_input_value("관리종목포함", "0")
        self.set_input_value("거래소구분", "1")
        self.comm_rq_data("거래대금상위", "opt10032", 0, "0104")
        time.sleep(1.0)
        return self.tr_data
