"""
웹 대시보드
Flask 기반 실시간 모니터링 대시보드
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pandas as pd
import yfinance as yf

import config
from config import *
from utils.logger import setup_logger
from utils.settings_manager import settings_manager

# pytz import (설치되지 않은 경우 대비)
try:
    import pytz
except ImportError:
    pytz = None

logger = setup_logger("web_dashboard")

# Flask 앱 초기화
app = Flask(__name__)

# Secret Key 설정 (보안 중요!)
# 1순위: 환경변수에서
# 2순위: config.py에서
# 3순위: 랜덤 생성 (재시작 시 세션 초기화됨)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or \
                 getattr(config, 'FLASK_SECRET_KEY', None) or \
                 os.urandom(24)

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 전역 변수 (실제로는 데이터베이스나 캐시 사용)
trader_instance = None
dashboard_data = {
    'portfolio_value': 100000,  # Paper Trading 기본 자본
    'cash': 100000,
    'positions': {},
    'trades': [],
    'signals': [],
    'is_running': False
}

def set_trader_instance(trader):
    """트레이더 인스턴스 설정"""
    global trader_instance
    trader_instance = trader
    logger.info("트레이더 인스턴스가 대시보드에 연결되었습니다")


def _normalize_symbol_list(symbols) -> List[str]:
    """문자열/리스트로 전달된 종목 목록을 정규화"""
    if symbols is None:
        return []

    if isinstance(symbols, str):
        raw_list = symbols.split(',')
    else:
        raw_list = symbols

    normalized = []
    seen = set()
    for item in raw_list:
        symbol = str(item).strip().upper()
        if symbol and symbol not in seen:
            normalized.append(symbol)
            seen.add(symbol)
    return normalized

class User(UserMixin):
    """사용자 클래스"""
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/')
@login_required
def index():
    """메인 대시보드"""
    return render_template('dashboard.html', active_page='dashboard')

@app.route('/history')
@login_required
def history():
    """거래 이력 페이지"""
    return render_template('history.html', active_page='history')

@app.route('/signals')
@login_required
def signals_page():
    """AI 신호 분석 페이지"""
    return render_template('signals.html', active_page='signals')

@app.route('/logs_page')
@login_required
def logs_page():
    """로그 뷰어 페이지"""
    return render_template('logs.html', active_page='logs')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 간단한 인증 (실제로는 더 안전한 방법 사용)
        if username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """로그아웃"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/reports')
@login_required
def reports_page():
    """일일 레포트 페이지"""
    return render_template('reports.html', active_page='reports')

@app.route('/settings')
@login_required
def settings_page():
    """설정 페이지"""
    return render_template('settings.html', active_page='settings')

@app.route('/api/portfolio')
@login_required
def get_portfolio():
    """포트폴리오 정보 API"""
    try:
        if trader_instance and hasattr(trader_instance, 'get_current_status'):
            status = trader_instance.get_current_status()
            return jsonify(status)
        else:
            return jsonify(dashboard_data)
    except Exception as e:
        logger.error(f"포트폴리오 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trades')
@login_required
def get_trades():
    """거래 내역 API (페이지네이션 및 필터링 지원)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        symbol = request.args.get('symbol', None)
        order_type = request.args.get('order_type', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        if trader_instance and hasattr(trader_instance, 'get_trade_history'):
            trade_history = trader_instance.get_trade_history()
            
            if not trade_history.empty:
                # 필터링
                if symbol:
                    trade_history = trade_history[trade_history['symbol'] == symbol]
                if order_type:
                    trade_history = trade_history[trade_history['order_type'] == order_type]
                if start_date:
                    trade_history = trade_history[trade_history['timestamp'] >= start_date]
                if end_date:
                    trade_history = trade_history[trade_history['timestamp'] <= end_date]
                
                # 정렬 (최신순 - 시간 역순)
                trade_history = trade_history.sort_values('timestamp', ascending=False)
                
                # 페이지네이션
                total = len(trade_history)
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                
                trades_data = trade_history.iloc[start_idx:end_idx].to_dict('records')
                
                return jsonify({
                    'trades': trades_data,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                })
        
        return jsonify({
            'trades': [],
            'total': 0,
            'page': 1,
            'per_page': per_page,
            'pages': 0
        })
    except Exception as e:
        logger.error(f"거래 내역 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals')
@login_required
def get_signals():
    """AI 신호 API (최근 신호 및 통계)"""
    try:
        # 로그에서 실시간 신호 로드
        signals = load_signals_from_logs()
        
        # 시간 역순 정렬 (최신순)
        signals.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 신호 통계 계산
        buy_signals = len([s for s in signals if 'BUY' in s.get('message', '').upper()])
        sell_signals = len([s for s in signals if 'SELL' in s.get('message', '').upper()])
        hold_signals = len([s for s in signals if 'HOLD' in s.get('message', '').upper()])
        
        return jsonify({
            'signals': signals[-20:],  # 최근 20개
            'total': len(signals),
            'buy_count': buy_signals,
            'sell_count': sell_signals,
            'hold_count': hold_signals,
            'no_signals': len(signals) == 0
        })
    except Exception as e:
        logger.error(f"신호 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals/history')
@login_required
def get_signals_history():
    """AI 신호 이력 API (페이지네이션 및 필터링)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        symbol = request.args.get('symbol', None)
        signal_type = request.args.get('signal_type', None)
        
        # 로그에서 신호 데이터 로드
        signals = load_signals_from_logs()
        
        # 시간 역순 정렬 (최신순)
        signals.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 필터링
        if symbol:
            signals = [s for s in signals if s.get('symbol') == symbol]
        if signal_type:
            signals = [s for s in signals if s.get('signal') == signal_type]
        
        # 페이지네이션
        total = len(signals)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        return jsonify({
            'signals': signals[start_idx:end_idx],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"신호 이력 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
@login_required
def get_performance():
    """성과 지표 API"""
    try:
        # 방법 1: trader_instance가 있으면 직접 사용
        if trader_instance and hasattr(trader_instance, 'get_current_status'):
            status = trader_instance.get_current_status()
            
            performance = {
                'total_return': status.get('total_return', 0),
                'portfolio_value': status.get('portfolio_value', 0),
                'cash': status.get('cash', 0),
                'num_positions': len(status.get('positions', {})),
                'daily_trades': status.get('daily_trades', 0),
                'is_running': status.get('is_running', False)
            }
            
            return jsonify(performance)
        
        # 방법 2: 상태 파일에서 읽기 (별도 프로세스)
        status_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trader_status.json')
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    status = json.load(f)
                    
                # systemctl로 실제 프로세스 실행 상태 확인
                import subprocess
                is_running = False
                try:
                    result = subprocess.run(
                        ['/usr/bin/systemctl', 'is-active', 'aitrader-paper'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    is_running = result.stdout.strip() == 'active'
                except:
                    pass
                
                performance = {
                    'total_return': status.get('total_return', 0),
                    'portfolio_value': status.get('portfolio_value', 0),
                    'cash': status.get('cash', 0),
                    'num_positions': len(status.get('positions', {})),
                    'daily_trades': status.get('daily_trades', 0),
                    'is_running': is_running  # systemctl 상태 사용
                }
                
                return jsonify(performance)
            except Exception as e:
                logger.error(f"상태 파일 읽기 오류: {str(e)}")
        
        # 방법 3: 기본값 반환 (is_running은 systemctl로 확인)
        is_running = False
        try:
            import subprocess
            result = subprocess.run(
                ['/usr/bin/systemctl', 'is-active', 'aitrader-paper'],
                capture_output=True,
                text=True,
                timeout=2
            )
            is_running = result.stdout.strip() == 'active'
        except:
            pass
        
        return jsonify({
            'total_return': 0,
            'portfolio_value': 100000,  # Paper Trading 기본 자본
            'cash': 100000,
            'num_positions': 0,
            'daily_trades': 0,
            'is_running': is_running
        })
    except Exception as e:
        logger.error(f"성과 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/control', methods=['POST'])
@login_required
def control_trader():
    """트레이더 제어 API (systemctl 사용)"""
    try:
        action = request.json.get('action')
        import subprocess
        
        if action == 'start':
            # systemctl로 서비스 시작
            try:
                result = subprocess.run(
                    ['/usr/bin/sudo', '/usr/bin/systemctl', 'start', 'aitrader-paper'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info("트레이더 서비스 시작 명령 전송")
                    return jsonify({'status': 'started', 'message': '트레이더를 시작했습니다'})
                else:
                    logger.error(f"서비스 시작 실패: {result.stderr}")
                    return jsonify({'error': result.stderr or '시작 실패'}), 500
            except Exception as e:
                logger.error(f"서비스 시작 오류: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        elif action == 'stop':
            # systemctl로 서비스 중지
            try:
                result = subprocess.run(
                    ['/usr/bin/sudo', '/usr/bin/systemctl', 'stop', 'aitrader-paper'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info("트레이더 서비스 중지 명령 전송")
                    return jsonify({'status': 'stopped', 'message': '트레이더를 중지했습니다'})
                else:
                    logger.error(f"서비스 중지 실패: {result.stderr}")
                    return jsonify({'error': result.stderr or '중지 실패'}), 500
            except Exception as e:
                logger.error(f"서비스 중지 오류: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        elif action == 'emergency_stop':
            # 긴급 정지 (강제 종료)
            try:
                subprocess.run(
                    ['/usr/bin/sudo', '/usr/bin/systemctl', 'kill', 'aitrader-paper'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                result = subprocess.run(
                    ['/usr/bin/sudo', '/usr/bin/systemctl', 'stop', 'aitrader-paper'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                logger.warning("트레이더 긴급 정지 명령 전송")
                return jsonify({'status': 'emergency_stopped', 'message': '트레이더를 긴급 정지했습니다'})
            except Exception as e:
                logger.error(f"긴급 정지 오류: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        return jsonify({'error': 'Invalid action'}), 400
        
    except Exception as e:
        logger.error(f"제어 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/chart')
@login_required
def get_performance_chart():
    """성과 차트 데이터 API"""
    try:
        days = request.args.get('days', 30, type=int)
        
        if trader_instance and hasattr(trader_instance, 'portfolio_manager'):
            # 포트폴리오 매니저에서 히스토리 가져오기
            portfolio_history = trader_instance.portfolio_manager.portfolio_history
            
            if portfolio_history:
                # 최근 N일 데이터
                recent_history = portfolio_history[-days:]
                
                dates = [h['timestamp'].strftime('%Y-%m-%d %H:%M') for h in recent_history]
                values = [h['total_value'] for h in recent_history]
                returns = [(v / 10000 - 1) * 100 for v in values]
                
                return jsonify({
                    'labels': dates,
                    'portfolio_values': values,
                    'returns': returns
                })
        
        return jsonify({
            'labels': [],
            'portfolio_values': [],
            'returns': []
        })
    except Exception as e:
        logger.error(f"차트 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/trades')
@login_required
def export_trades():
    """거래 내역 CSV Export"""
    try:
        if trader_instance and hasattr(trader_instance, 'get_trade_history'):
            trade_history = trader_instance.get_trade_history()
            
            if not trade_history.empty:
                # CSV 파일 생성
                os.makedirs('reports', exist_ok=True)
                csv_filename = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                csv_path = os.path.join('reports', csv_filename)
                trade_history.to_csv(csv_path, index=False, encoding='utf-8-sig')
                
                return send_file(csv_path, as_attachment=True, download_name='trades.csv')
        
        return jsonify({'error': 'No trades found'}), 404
    except Exception as e:
        logger.error(f"Export 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
@login_required
def get_logs():
    """로그 API (실시간 로그 조회) - 최근 로그 파일 자동 검색"""
    try:
        level = request.args.get('level', 'ALL')
        limit = request.args.get('limit', 100, type=int)
        log_type = request.args.get('type', 'paper_trader')
        
        logs = []
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        # 최근 7일간의 로그 파일 검색 (오늘부터 역순으로)
        found_logs = False
        for day_offset in range(7):
            date = (datetime.now() - timedelta(days=day_offset)).strftime('%Y%m%d')
            log_path = os.path.join(logs_dir, f'{log_type}_{date}.log')
            
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        for line in lines:
                            # 레벨 필터링
                            if level != 'ALL':
                                if f' - {level} - ' not in line:
                                    continue
                            
                            # 로그 파싱
                            parts = line.strip().split(' - ')
                            if len(parts) >= 3:
                                logs.append({
                                    'timestamp': parts[0],
                                    'level': parts[1],
                                    'message': ' - '.join(parts[2:]),
                                    'full': line.strip(),
                                    'date': date
                                })
                    found_logs = True
                except Exception as read_error:
                    logger.error(f"로그 파일 읽기 오류 ({log_path}): {str(read_error)}")
                    continue
        
        # 로그 파일을 찾지 못한 경우, logs 디렉토리에서 해당 타입의 최신 파일 검색
        if not found_logs:
            try:
                if os.path.exists(logs_dir):
                    # 해당 타입의 모든 로그 파일 찾기
                    pattern = f'{log_type}_*.log'
                    import glob
                    log_files = glob.glob(os.path.join(logs_dir, pattern))
                    
                    if log_files:
                        # 수정 시간 기준으로 정렬 (최신순)
                        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        # 가장 최신 파일 사용
                        log_path = log_files[0]
                        
                        try:
                            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()
                                for line in lines[-limit*2:]:  # 더 많이 읽어서 필터링 후 제한
                                    # 레벨 필터링
                                    if level != 'ALL':
                                        if f' - {level} - ' not in line:
                                            continue
                                    
                                    # 로그 파싱
                                    parts = line.strip().split(' - ')
                                    if len(parts) >= 3:
                                        logs.append({
                                            'timestamp': parts[0],
                                            'level': parts[1],
                                            'message': ' - '.join(parts[2:]),
                                            'full': line.strip(),
                                            'date': os.path.basename(log_path).replace(f'{log_type}_', '').replace('.log', '')
                                        })
                        except Exception as read_error:
                            logger.error(f"로그 파일 읽기 오류 ({log_path}): {str(read_error)}")
            except Exception as search_error:
                logger.error(f"로그 파일 검색 오류: {str(search_error)}")
        
        # 시간순 정렬 (최신순)
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 제한 적용
        logs = logs[:limit]
        
        return jsonify({
            'logs': logs,
            'total_found': len(logs),
            'message': f'최근 로그 {len(logs)}개를 찾았습니다.' if logs else '로그 파일을 찾을 수 없습니다.'
        })
    except Exception as e:
        logger.error(f"로그 API 오류: {str(e)}")
        return jsonify({'error': str(e), 'logs': []}), 500

@app.route('/api/diagnostics')
@login_required
def get_diagnostics():
    """시스템 진단 API - 거래 미발생 원인 분석"""
    try:
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'issues': [],
            'warnings': [],
            'info': [],
            'signal_analysis': {},
            'data_quality': {},
            'system_status': {}
        }
        
        # 1. 신호 생성 여부 확인
        signals = load_signals_from_logs(days=3)
        diagnostics['signal_analysis'] = {
            'total_signals': len(signals),
            'today_signals': len([s for s in signals if s['date'] == datetime.now().strftime('%Y%m%d')]),
            'buy_signals': len([s for s in signals if s['signal_type'] == 'BUY']),
            'sell_signals': len([s for s in signals if s['signal_type'] == 'SELL']),
            'hold_signals': len([s for s in signals if s['signal_type'] == 'HOLD'])
        }
        
        if diagnostics['signal_analysis']['today_signals'] == 0:
            diagnostics['issues'].append({
                'severity': 'HIGH',
                'category': 'SIGNALS',
                'message': '오늘 생성된 거래 신호가 없습니다',
                'suggestion': '전략 파라미터를 완화하거나 데이터 수집 상태를 확인하세요'
            })
        
        # 2. 데이터 수집 상태 확인
        today = datetime.now().strftime('%Y%m%d')
        data_collector_log = os.path.join('logs', f'data_collector_{today}.log')
        
        if os.path.exists(data_collector_log):
            with open(data_collector_log, 'r', encoding='utf-8') as f:
                log_content = f.read()
                if 'ERROR' in log_content:
                    diagnostics['issues'].append({
                        'severity': 'HIGH',
                        'category': 'DATA',
                        'message': '데이터 수집 중 오류 발생',
                        'suggestion': 'data_collector 로그를 확인하세요'
                    })
                else:
                    diagnostics['info'].append({
                        'category': 'DATA',
                        'message': '데이터 수집 정상'
                    })
        else:
            diagnostics['warnings'].append({
                'severity': 'MEDIUM',
                'category': 'DATA',
                'message': '오늘의 데이터 수집 로그가 없습니다',
                'suggestion': '시스템이 실행 중인지 확인하세요'
            })
        
        # 3. 트레이더 실행 상태 확인
        try:
            import subprocess
            result = subprocess.run(
                ['/usr/bin/systemctl', 'is-active', 'aitrader-paper'],
                capture_output=True,
                text=True,
                timeout=2
            )
            is_running = result.stdout.strip() == 'active'
            diagnostics['system_status']['trader_running'] = is_running
            
            if not is_running:
                diagnostics['issues'].append({
                    'severity': 'CRITICAL',
                    'category': 'SYSTEM',
                    'message': 'Paper Trading 서비스가 실행 중이 아닙니다',
                    'suggestion': '대시보드에서 거래를 시작하거나 systemctl로 서비스를 시작하세요'
                })
        except:
            diagnostics['system_status']['trader_running'] = None
            diagnostics['warnings'].append({
                'severity': 'LOW',
                'category': 'SYSTEM',
                'message': '서비스 상태를 확인할 수 없습니다',
                'suggestion': 'systemctl 접근 권한을 확인하세요'
            })
        
        # 4. 최근 거래 확인
        if trader_instance and hasattr(trader_instance, 'get_trade_history'):
            trade_history = trader_instance.get_trade_history()
            if not trade_history.empty:
                recent_trades = trade_history[trade_history['timestamp'] >= (datetime.now() - timedelta(days=1)).isoformat()]
                diagnostics['system_status']['trades_today'] = len(recent_trades)
                
                if len(recent_trades) == 0:
                    diagnostics['warnings'].append({
                        'severity': 'MEDIUM',
                        'category': 'TRADING',
                        'message': '최근 24시간 동안 거래가 없습니다',
                        'suggestion': '신호 생성 조건 또는 시장 상황을 확인하세요'
                    })
            else:
                diagnostics['system_status']['trades_today'] = 0
                diagnostics['info'].append({
                    'category': 'TRADING',
                    'message': '아직 거래 이력이 없습니다 (정상 - 신규 시작)'
                })
        
        # 5. 전략 설정 확인
        diagnostics['info'].append({
            'category': 'STRATEGY',
            'message': f'Paper Trading 모드 - 완화된 설정 (신뢰도: 0.35, BUY: 3.0, SELL: 2.5)'
        })
        
        # 6. 종합 상태
        if len(diagnostics['issues']) == 0:
            diagnostics['status'] = 'HEALTHY'
            diagnostics['summary'] = '시스템이 정상 작동 중입니다'
        elif any(issue['severity'] == 'CRITICAL' for issue in diagnostics['issues']):
            diagnostics['status'] = 'CRITICAL'
            diagnostics['summary'] = '긴급 조치가 필요합니다'
        elif any(issue['severity'] == 'HIGH' for issue in diagnostics['issues']):
            diagnostics['status'] = 'WARNING'
            diagnostics['summary'] = '일부 문제가 감지되었습니다'
        else:
            diagnostics['status'] = 'OK'
            diagnostics['summary'] = '경미한 경고가 있지만 정상 작동 중입니다'
        
        return jsonify(diagnostics)
        
    except Exception as e:
        logger.error(f"진단 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategy/parameters')
@login_required
def get_strategy_parameters():
    """전략 파라미터 조회 API"""
    try:
        # config.py에서 파라미터 읽기
        parameters = {
            'confidence_threshold': getattr(config, 'CONFIDENCE_THRESHOLD', 0.35),
            'buy_signal_threshold': getattr(config, 'BUY_SIGNAL_THRESHOLD', 3.0),
            'sell_signal_threshold': getattr(config, 'SELL_SIGNAL_THRESHOLD', 2.5),
            'rsi_oversold': getattr(config, 'RSI_OVERSOLD', 30),
            'rsi_overbought': getattr(config, 'RSI_OVERBOUGHT', 70),
            'volume_threshold': getattr(config, 'VOLUME_THRESHOLD', 1.3)
        }
        
        return jsonify(parameters)
    except Exception as e:
        logger.error(f"파라미터 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def handle_settings():
    """설정 조회 및 저장 API"""
    try:
        if request.method == 'GET':
            return jsonify(settings_manager.get_settings())
            
        elif request.method == 'POST':
            new_settings = request.json or {}
            current_settings = dict(settings_manager.get_settings())

            long_term_symbols_raw = new_settings.get('long_term_symbols', current_settings.get('long_term_symbols', []))
            long_term_symbols = _normalize_symbol_list(long_term_symbols_raw)

            short_term_candidates_raw = new_settings.get('short_term_candidates', current_settings.get('short_term_candidates', []))
            short_term_candidates = _normalize_symbol_list(short_term_candidates_raw)
            short_term_candidates = [s for s in short_term_candidates if s not in long_term_symbols]

            short_term_enabled = bool(new_settings.get('short_term_enabled', current_settings.get('short_term_enabled', False)))

            try:
                pool_size = int(new_settings.get('short_term_pool_size', current_settings.get('short_term_pool_size', 3)))
            except (ValueError, TypeError):
                pool_size = current_settings.get('short_term_pool_size', 3)
            pool_size = max(1, min(10, pool_size))

            updated_settings = {
                **current_settings,
                'long_term_symbols': long_term_symbols,
                'short_term_candidates': short_term_candidates,
                'short_term_enabled': short_term_enabled,
                'short_term_pool_size': pool_size
            }

            settings_manager.save_settings(updated_settings)
            logger.info(f"설정 변경됨: {updated_settings}")
            
            return jsonify({'status': 'success', 'message': '설정이 저장되었습니다', 'settings': updated_settings})
            
    except Exception as e:
        logger.error(f"설정 API 오류: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/market/quotes', methods=['POST'])
@login_required
def get_market_quotes():
    """실시간(지연) 시세 조회 API"""
    try:
        data = request.json
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({})
            
        # 대문자 변환 및 중복 제거
        symbols = list(set([s.upper() for s in symbols]))
        
        # yfinance로 데이터 조회 (최근 5일치 - 전일 대비 계산용)
        # progress=False로 로그 출력 억제
        try:
            df = yf.download(symbols, period="5d", progress=False)
        except Exception as e:
            logger.error(f"yfinance download error: {e}")
            return jsonify({})
        
        quotes = {}
        
        # 데이터가 없는 경우 빈 딕셔너리 반환
        if df.empty:
            return jsonify({})

        # 단일 종목인 경우 DataFrame 구조가 다름 (MultiIndex가 아님)
        if len(symbols) == 1:
            symbol = symbols[0]
            try:
                # 'Close' 컬럼이 있는지 확인
                if 'Close' in df.columns:
                    close_series = df['Close']
                else:
                    # 컬럼이 바로 Close일 수도 있음 (구조에 따라 다름)
                    close_series = df
                
                if not close_series.empty:
                    current_price = float(close_series.iloc[-1])
                    prev_close = float(close_series.iloc[-2]) if len(close_series) >= 2 else current_price
                    
                    change = current_price - prev_close
                    change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
                    
                    quotes[symbol] = {
                        'price': round(current_price, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2)
                    }
            except Exception as e:
                logger.error(f"Error parsing quote for {symbol}: {e}")
        else:
            # 다중 종목 (MultiIndex: (Price, Symbol))
            # yfinance 최신 버전에서는 'Close' 컬럼 아래에 심볼들이 있음
            if 'Close' in df:
                close_data = df['Close']
                
                for symbol in symbols:
                    try:
                        if symbol in close_data:
                            series = close_data[symbol].dropna()
                            if not series.empty:
                                current_price = float(series.iloc[-1])
                                prev_close = float(series.iloc[-2]) if len(series) >= 2 else current_price
                                
                                change = current_price - prev_close
                                change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
                                
                                quotes[symbol] = {
                                    'price': round(current_price, 2),
                                    'change': round(change, 2),
                                    'change_percent': round(change_percent, 2)
                                }
                    except Exception as e:
                        logger.error(f"Error parsing quote for {symbol}: {e}")
                        continue

        return jsonify(quotes)
        
    except Exception as e:
        logger.error(f"Market quotes API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/status')
@login_required
def get_market_status():
    """시장 상태 및 거래 시간 확인 API"""
    try:
        if pytz:
            # 미국 동부 시간
            us_tz = pytz.timezone('US/Eastern')
            us_time = datetime.now(us_tz)
        else:
            # pytz가 없으면 한국 시간 기준으로 계산 (한국시간 - 14시간 = 미국 동부시간, 서머타임 시)
            kr_time = datetime.now()
            us_time = kr_time - timedelta(hours=14)
        
        # 거래 시간 확인 (9:30 AM - 4:00 PM ET)
        market_open_time = us_time.replace(hour=9, minute=30, second=0)
        market_close_time = us_time.replace(hour=16, minute=0, second=0)
        
        is_market_open = market_open_time <= us_time <= market_close_time
        is_weekend = us_time.weekday() >= 5  # 토요일(5), 일요일(6)
        
        status = {
            'us_time': us_time.strftime('%Y-%m-%d %H:%M:%S EST/EDT'),
            'korea_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S KST'),
            'is_market_open': is_market_open and not is_weekend,
            'is_weekend': is_weekend,
            'market_open': market_open_time.strftime('%H:%M'),
            'market_close': market_close_time.strftime('%H:%M'),
            'time_to_open': None,
            'time_to_close': None
        }
        
        if not is_market_open and not is_weekend:
            if us_time < market_open_time:
                delta = market_open_time - us_time
                status['time_to_open'] = str(delta).split('.')[0]
            elif us_time > market_close_time:
                next_open = (us_time + timedelta(days=1)).replace(hour=9, minute=30, second=0)
                delta = next_open - us_time
                status['time_to_open'] = str(delta).split('.')[0]
        
        if is_market_open:
            delta = market_close_time - us_time
            status['time_to_close'] = str(delta).split('.')[0]
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"시장 상태 API 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_html_templates():
    """
    HTML 템플릿 생성 (더 이상 사용 안 함)
    개선된 템플릿은 templates/ 폴더에 별도 파일로 관리됨
    """
    # 이 함수는 더 이상 사용하지 않습니다.
    # templates/ 폴더의 파일들을 직접 관리합니다.
    pass
    
def _create_html_templates_deprecated():
    """
    구버전 HTML 템플릿 생성 (deprecated)
    참고용으로만 남겨둠
    """
    import os
    # dashboard 폴더 내에 templates 폴더 생성
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(dashboard_dir, 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # 로그인 템플릿
    login_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 트레이더 로그인</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }
            .login-container { max-width: 400px; margin: 100px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .login-header { text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .login-btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .login-btn:hover { background: #0056b3; }
            .error { color: red; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>AI 주식 트레이더</h1>
                <p>로그인이 필요합니다</p>
            </div>
            <form method="POST">
                <div class="form-group">
                    <label for="username">사용자명:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">비밀번호:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="login-btn">로그인</button>
                {% if error %}
                <div class="error">{{ error }}</div>
                {% endif %}
            </form>
        </div>
    </body>
    </html>
    """
    
    # 대시보드 템플릿
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 트레이더 대시보드</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial, sans-serif; background: #f5f5f5; }
            .header { background: #2c3e50; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
            .header h1 { font-size: 24px; }
            .logout-btn { background: #e74c3c; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .card h3 { margin-bottom: 15px; color: #2c3e50; }
            .metric { display: flex; justify-content: space-between; margin-bottom: 10px; }
            .metric-value { font-weight: bold; }
            .positive { color: #27ae60; }
            .negative { color: #e74c3c; }
            .control-panel { display: flex; gap: 10px; margin-bottom: 20px; }
            .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
            .btn-start { background: #27ae60; color: white; }
            .btn-stop { background: #e74c3c; color: white; }
            .btn-emergency { background: #f39c12; color: white; }
            .status { padding: 10px; border-radius: 4px; margin-bottom: 20px; }
            .status.running { background: #d4edda; color: #155724; }
            .status.stopped { background: #f8d7da; color: #721c24; }
            .table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            .table th, .table td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            .table th { background-color: #f8f9fa; }
            .refresh-btn { background: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AI 주식 트레이더 대시보드</h1>
            <button class="logout-btn" onclick="logout()">로그아웃</button>
        </div>
        
        <div class="container">
            <div class="control-panel">
                <button class="btn btn-start" onclick="controlTrader('start')">거래 시작</button>
                <button class="btn btn-stop" onclick="controlTrader('stop')">거래 중지</button>
                <button class="btn btn-emergency" onclick="controlTrader('emergency_stop')">긴급 정지</button>
                <button class="refresh-btn" onclick="refreshData()">새로고침</button>
            </div>
            
            <div id="status" class="status stopped">상태: 중지됨</div>
            
            <div class="dashboard-grid">
                <div class="card">
                    <h3>포트폴리오 현황</h3>
                    <div id="portfolio-info">
                        <div class="metric">
                            <span>포트폴리오 가치:</span>
                            <span class="metric-value" id="portfolio-value">$0</span>
                        </div>
                        <div class="metric">
                            <span>현금:</span>
                            <span class="metric-value" id="cash">$0</span>
                        </div>
                        <div class="metric">
                            <span>총 수익률:</span>
                            <span class="metric-value" id="total-return">0%</span>
                        </div>
                        <div class="metric">
                            <span>보유 포지션:</span>
                            <span class="metric-value" id="num-positions">0개</span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>거래 현황</h3>
                    <div id="trading-info">
                        <div class="metric">
                            <span>일일 거래:</span>
                            <span class="metric-value" id="daily-trades">0회</span>
                        </div>
                        <div class="metric">
                            <span>거래 상태:</span>
                            <span class="metric-value" id="trading-status">중지</span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>보유 포지션</h3>
                    <div id="positions-table">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>종목</th>
                                    <th>수량</th>
                                    <th>평균가</th>
                                    <th>현재가</th>
                                    <th>손익</th>
                                </tr>
                            </thead>
                            <tbody id="positions-tbody">
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="card">
                    <h3>최근 거래</h3>
                    <div id="trades-table">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>시간</th>
                                    <th>종목</th>
                                    <th>거래</th>
                                    <th>수량</th>
                                    <th>가격</th>
                                    <th>손익</th>
                                </tr>
                            </thead>
                            <tbody id="trades-tbody">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let refreshInterval;
            
            function logout() {
                window.location.href = '/logout';
            }
            
            function controlTrader(action) {
                fetch('/api/control', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({action: action})
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Control response:', data);
                    refreshData();
                })
                .catch(error => {
                    console.error('Control error:', error);
                });
            }
            
            function refreshData() {
                // 포트폴리오 정보 업데이트
                fetch('/api/portfolio')
                    .then(response => response.json())
                    .then(data => {
                        updatePortfolioInfo(data);
                    })
                    .catch(error => console.error('Portfolio error:', error));
                
                // 거래 내역 업데이트
                fetch('/api/trades')
                    .then(response => response.json())
                    .then(data => {
                        updateTradesTable(data);
                    })
                    .catch(error => console.error('Trades error:', error));
                
                // 성과 정보 업데이트
                fetch('/api/performance')
                    .then(response => response.json())
                    .then(data => {
                        updatePerformanceInfo(data);
                    })
                    .catch(error => console.error('Performance error:', error));
            }
            
            function updatePortfolioInfo(data) {
                document.getElementById('portfolio-value').textContent = '$' + (data.portfolio_value || 0).toLocaleString();
                document.getElementById('cash').textContent = '$' + (data.cash || 0).toLocaleString();
                
                const totalReturn = (data.total_return || 0) * 100;
                const returnElement = document.getElementById('total-return');
                returnElement.textContent = totalReturn.toFixed(2) + '%';
                returnElement.className = 'metric-value ' + (totalReturn >= 0 ? 'positive' : 'negative');
                
                document.getElementById('num-positions').textContent = Object.keys(data.positions || {}).length + '개';
                
                // 포지션 테이블 업데이트
                updatePositionsTable(data.positions || {});
            }
            
            function updatePositionsTable(positions) {
                const tbody = document.getElementById('positions-tbody');
                tbody.innerHTML = '';
                
                for (const [symbol, pos] of Object.entries(positions)) {
                    const row = tbody.insertRow();
                    row.insertCell(0).textContent = symbol;
                    row.insertCell(1).textContent = pos.quantity;
                    row.insertCell(2).textContent = '$' + pos.avg_price.toFixed(2);
                    row.insertCell(3).textContent = '$' + pos.current_price.toFixed(2);
                    
                    const pnlCell = row.insertCell(4);
                    pnlCell.textContent = '$' + pos.unrealized_pnl.toFixed(2);
                    pnlCell.className = pos.unrealized_pnl >= 0 ? 'positive' : 'negative';
                }
            }
            
            function updateTradesTable(trades) {
                const tbody = document.getElementById('trades-tbody');
                tbody.innerHTML = '';
                
                trades.slice(-10).reverse().forEach(trade => {
                    const row = tbody.insertRow();
                    row.insertCell(0).textContent = new Date(trade.timestamp).toLocaleString();
                    row.insertCell(1).textContent = trade.symbol;
                    row.insertCell(2).textContent = trade.order_type;
                    row.insertCell(3).textContent = trade.quantity;
                    row.insertCell(4).textContent = '$' + trade.price.toFixed(2);
                    
                    const pnlCell = row.insertCell(5);
                    pnlCell.textContent = '$' + (trade.pnl || 0).toFixed(2);
                    pnlCell.className = (trade.pnl || 0) >= 0 ? 'positive' : 'negative';
                });
            }
            
            function updatePerformanceInfo(data) {
                document.getElementById('daily-trades').textContent = (data.daily_trades || 0) + '회';
                document.getElementById('trading-status').textContent = data.is_running ? '실행 중' : '중지';
                
                // 상태 표시 업데이트
                const statusElement = document.getElementById('status');
                statusElement.textContent = '상태: ' + (data.is_running ? '실행 중' : '중지됨');
                statusElement.className = 'status ' + (data.is_running ? 'running' : 'stopped');
            }
            
            // 초기 로드
            document.addEventListener('DOMContentLoaded', function() {
                refreshData();
                
                // 30초마다 자동 새로고침
                refreshInterval = setInterval(refreshData, 30000);
            });
            
            // 페이지 언로드 시 인터벌 정리
            window.addEventListener('beforeunload', function() {
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                }
            });
        </script>
    </body>
    </html>
    """
    
    # 템플릿 파일 저장
    with open(os.path.join(templates_dir, 'login.html'), 'w', encoding='utf-8') as f:
        f.write(login_html)
    
    with open(os.path.join(templates_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(dashboard_html)

def set_trader_instance(trader):
    """트레이더 인스턴스 설정"""
    global trader_instance
    trader_instance = trader
    logger.info("트레이더 인스턴스 설정 완료")

def load_signals_from_logs(days=1) -> List[Dict]:
    """로그 파일에서 신호 데이터 로드 (개선된 버전)"""
    signals = []
    try:
        # 최근 N일간의 로그 확인
        for day_offset in range(days):
            date = (datetime.now() - timedelta(days=day_offset)).strftime('%Y%m%d')
            log_files = [
                f'paper_trader_{date}.log',
                f'improved_buy_low_sell_high_{date}.log',
                f'market_analyzer_{date}.log'
            ]
            
            for log_file in log_files:
                log_path = os.path.join('logs', log_file)
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            # 신호 관련 로그 찾기 (더 상세하게)
                            line_upper = line.upper()
                            if any(keyword in line_upper for keyword in ['신호', 'SIGNAL', '매수', '매도', 'BUY', 'SELL', 'HOLD']):
                                try:
                                    parts = line.strip().split(' - ')
                                    if len(parts) >= 3:
                                        # 신호 타입 파싱
                                        message = ' - '.join(parts[2:])
                                        signal_type = 'UNKNOWN'
                                        
                                        if 'BUY' in line_upper or '매수' in line:
                                            signal_type = 'BUY'
                                        elif 'SELL' in line_upper or '매도' in line:
                                            signal_type = 'SELL'
                                        elif 'HOLD' in line_upper or '보유' in line:
                                            signal_type = 'HOLD'
                                        
                                        # 종목 추출 시도
                                        symbol = None
                                        for stock in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']:
                                            if stock in line:
                                                symbol = stock
                                                break
                                        
                                        signals.append({
                                            'timestamp': parts[0],
                                            'level': parts[1],
                                            'message': message,
                                            'signal_type': signal_type,
                                            'symbol': symbol,
                                            'source': log_file,
                                            'date': date
                                        })
                                except:
                                    continue
    except Exception as e:
        logger.error(f"신호 로드 오류: {str(e)}")
    
    return signals

# =============================================================================
# 일일 레포트 API
# =============================================================================

@app.route('/api/reports/list')
@login_required
def get_reports_list():
    """일일 레포트 목록 조회 API"""
    try:
        from utils.daily_report_generator import report_generator

        limit = request.args.get('limit', 30, type=int)
        reports = report_generator.list_reports(limit=limit)

        return jsonify({
            'reports': reports,
            'total': len(reports)
        })
    except Exception as e:
        logger.error(f"레포트 목록 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/<report_date>')
@login_required
def get_report(report_date):
    """특정 날짜 레포트 조회 API"""
    try:
        from utils.daily_report_generator import report_generator
        from datetime import datetime

        # 날짜 파싱 (YYYYMMDD 형식)
        try:
            date_obj = datetime.strptime(report_date, '%Y%m%d').date()
        except ValueError:
            return jsonify({'error': '잘못된 날짜 형식입니다. YYYYMMDD 형식을 사용하세요.'}), 400

        report = report_generator.get_report(report_date=date_obj)

        if not report:
            return jsonify({'error': '해당 날짜의 레포트를 찾을 수 없습니다.'}), 404

        return jsonify(report)
    except Exception as e:
        logger.error(f"레포트 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report_now():
    """즉시 레포트 생성 API"""
    try:
        from utils.daily_report_generator import report_generator
        from datetime import datetime

        # 방법 1: trader_instance가 있으면 직접 사용
        status = None
        if trader_instance and hasattr(trader_instance, 'get_current_status'):
            status = trader_instance.get_current_status()
        else:
            # 방법 2: 상태 파일에서 읽기 (별도 프로세스)
            status_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trader_status.json')
            if os.path.exists(status_file):
                try:
                    with open(status_file, 'r') as f:
                        status = json.load(f)
                except Exception as e:
                    logger.error(f"상태 파일 읽기 오류: {str(e)}")

        # 상태 정보를 가져올 수 없는 경우
        if not status:
            return jsonify({'error': '거래자 상태 정보를 찾을 수 없습니다. Paper Trader가 실행 중인지 확인하세요.'}), 500

        # 포트폴리오 데이터
        portfolio_data = {
            'portfolio_value': status.get('portfolio_value', 0),
            'cash': status.get('cash', 0),
            'positions': status.get('positions', {}),
            'total_return': status.get('total_return', 0),
            'daily_return': status.get('daily_return', 0)
        }

        # 거래 내역 수집
        trades = []

        # 방법 1: trader_instance가 있으면 직접 사용
        if trader_instance and hasattr(trader_instance, 'get_trade_history'):
            trade_history = trader_instance.get_trade_history()

            if not trade_history.empty:
                # 오늘 거래만 필터링
                today = datetime.now().date()
                if 'timestamp' in trade_history.columns:
                    today_trades = trade_history[
                        pd.to_datetime(trade_history['timestamp']).dt.date == today
                    ]

                    # Dict 리스트로 변환
                    trades = today_trades.to_dict('records')
        else:
            # 방법 2: 로그에서 거래 내역 파싱
            today = datetime.now().strftime('%Y%m%d')
            log_path = os.path.join('logs', f'paper_trader_{today}.log')

            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if any(keyword in line for keyword in ['매수 주문 제출', '매도 주문 제출', 'BUY', 'SELL']):
                                # 간단한 거래 정보 추가 (상세 파싱은 생략)
                                trades.append({
                                    'timestamp': datetime.now().isoformat(),
                                    'type': 'trade',
                                    'log': line.strip()
                                })
                except Exception as e:
                    logger.error(f"로그 파싱 오류: {str(e)}")

        # 신호 내역
        signals = []

        # 시장 데이터
        market_data = None

        # 레포트 생성
        result = report_generator.generate_daily_report(
            portfolio_data=portfolio_data,
            trades=trades,
            signals=signals,
            market_data=market_data,
            report_date=datetime.now().date()
        )

        if result['success']:
            return jsonify({
                'success': True,
                'message': '레포트가 생성되었습니다.',
                'report_path': result['report_path'],
                'metadata': result['metadata']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '알 수 없는 오류')
            }), 500

    except Exception as e:
        logger.error(f"레포트 생성 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """대시보드 실행"""
    # HTML 템플릿 생성 - 이미 templates 폴더에 개선된 파일들이 있으므로 비활성화
    # create_html_templates()
    
    logger.info(f"웹 대시보드 시작: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    run_dashboard()

