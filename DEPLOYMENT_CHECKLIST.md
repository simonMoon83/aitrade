# 오라클 클라우드 배포 체크리스트

배포 전 반드시 확인해야 할 항목들입니다.

## 📋 배포 전 체크리스트

### 1. 로컬 테스트 완료
- [ ] 백테스트가 정상적으로 실행됨
- [ ] 페이퍼 트레이딩 테스트 완료
- [ ] 대시보드가 정상적으로 작동함
- [ ] 모든 API 키가 올바르게 설정됨

### 2. 파일 준비
- [ ] `.env` 파일에 실제 API 키 입력
- [ ] `config.py`에서 거래 파라미터 확인
- [ ] `requirements.txt` 최신 버전 확인
- [ ] 불필요한 파일 삭제 (test*, debug* 등)

### 3. 보안 설정
- [ ] `.env` 파일이 `.gitignore`에 포함됨
- [ ] API 키가 코드에 하드코딩되지 않음
- [ ] 강력한 대시보드 비밀번호 설정
- [ ] SSH 키 페어 준비됨

### 4. OCI 인스턴스 설정
- [ ] 인스턴스 생성 완료
- [ ] 공용 IP 할당됨
- [ ] 보안 규칙 설정 (포트 22, 5000)
- [ ] SSH 접속 테스트 완료

---

## 🚀 빠른 배포 가이드

### 단계 1: 로컬에서 서버로 업로드
```bash
# Windows PowerShell에서
scp -i path\to\key.pem -r C:\Project\aitrader ubuntu@YOUR_IP:~/

# 또는 Git 사용
git init
git add .
git commit -m "Initial commit"
git push origin main
```

### 단계 2: 서버 접속
```bash
ssh -i path\to\key.pem ubuntu@YOUR_IP
```

### 단계 3: 빠른 설치
```bash
cd ~/aitrader
chmod +x scripts/*.sh
./scripts/quick_start.sh
```

### 단계 4: API 키 설정
```bash
nano .env
```
실제 API 키 입력 후 저장 (Ctrl+O, Enter, Ctrl+X)

### 단계 5: 서비스 설정
```bash
./scripts/setup_services.sh
```

### 단계 6: 동작 확인
```bash
./scripts/monitor.sh
```

---

## 📊 배포 후 체크리스트

### 즉시 확인
- [ ] 서비스가 실행 중인지 확인
  ```bash
  sudo systemctl status aitrader-paper
  sudo systemctl status aitrader-dashboard
  ```
- [ ] 로그에 에러가 없는지 확인
  ```bash
  tail -f ~/aitrader/logs/paper_trading.log
  ```
- [ ] 대시보드 접속 가능한지 확인
  ```
  http://YOUR_IP:5000
  ```

### 1시간 후 확인
- [ ] 헬스 체크 실행
  ```bash
  ./scripts/health_check.sh
  ```
- [ ] 거래가 정상적으로 실행되는지 확인
- [ ] 메모리/CPU 사용률 확인

### 1일 후 확인
- [ ] 로그 파일 용량 확인
- [ ] 백업 설정 확인
- [ ] 크론잡 동작 확인

---

## 🔧 자주 사용하는 명령어

### 서비스 관리
```bash
# 시작
sudo systemctl start aitrader-paper

# 중지
sudo systemctl stop aitrader-paper

# 재시작
sudo systemctl restart aitrader-paper

# 상태 확인
sudo systemctl status aitrader-paper
```

### 로그 확인
```bash
# 실시간 로그
tail -f ~/aitrader/logs/paper_trading.log

# 에러 로그
tail -100 ~/aitrader/logs/paper_trading_error.log

# 시스템 로그
sudo journalctl -u aitrader-paper -f
```

### 모니터링
```bash
# 시스템 모니터링
./scripts/monitor.sh

# 헬스 체크
./scripts/health_check.sh

# 리소스 사용량
htop
```

### 백업
```bash
# 수동 백업
./scripts/backup.sh

# 백업 복원
tar -xzf ~/backups/aitrader_backup_YYYYMMDD_HHMMSS.tar.gz -C ~/
```

---

## ⚠️ 주의사항

### 보안
1. **절대 공개하지 말 것:**
   - `.env` 파일
   - API 키
   - 백업 파일 (API 키 포함)

2. **방화벽 설정:**
   - SSH(22) 포트는 본인 IP만 허용 권장
   - 대시보드(5000) 포트도 제한 권장

3. **정기 업데이트:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

### 실전 거래 전
1. **최소 1개월 페이퍼 트레이딩**
2. **수익률이 안정적으로 플러스**
3. **모든 에러 로그 확인**
4. **리스크 관리 파라미터 재확인**

---

## 🆘 문제 해결

### 서비스가 시작되지 않을 때
```bash
# 상세 로그 확인
sudo journalctl -u aitrader-paper -xe

# 수동 실행으로 에러 확인
cd ~/aitrader
source venv/bin/activate
python main.py --mode paper --symbols AAPL
```

### 메모리 부족 (1GB 인스턴스)
```bash
# 스왑 추가
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 포트 접근 불가
1. OCI 콘솔에서 보안 규칙 확인
2. Ubuntu 방화벽 확인: `sudo ufw status`
3. 서비스 포트 확인: `ss -tulpn | grep 5000`

---

## 📞 지원

문제 발생 시:
1. `./scripts/health_check.sh` 실행
2. 로그 파일 확인
3. GitHub Issues 등록

---

## ✅ 최종 체크

배포 완료 후:
- [ ] 모든 서비스 정상 작동
- [ ] 대시보드 접속 가능
- [ ] 백업 스크립트 설정됨
- [ ] 모니터링 도구 설정됨
- [ ] 긴급 연락처 저장됨
- [ ] 문서 읽음 (ORACLE_CLOUD_DEPLOYMENT.md)

**배포 성공을 축하합니다! 🎉**
