## Fail2Ban 로그 분석용 정규식 패턴
이 패턴들은 fail2ban.log에 기록된 Found, Ban, Unban 이벤트를 추출하기 위해 작성되었습니다. 

1. Found 패턴

용도: 침입 시도가 감지되었을 때 기록되는 로그 추출 

정규식: (?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) fail2ban\.filter\s+\[\d+\]: INFO\s+\[(?P<jail>\S+)\] Found (?P<ip>\d{1,3}(?:\.\d{1,3}){3})


매칭 예시: 2026-03-31 14:22:41,171 ... Found 10.82.198.105 

2. Ban/Unban 패턴

용도: 실제로 IP가 차단되거나 해제된 이벤트 추출 

정규식: (?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) fail2ban\.actions\s+\[\d+\]: NOTICE\s+\[(?P<jail>\S+)\] (?P<action>Ban|Unban) (?P<ip>\d{1,3}(?:\.\d{1,3}){3})

매칭 예시:


Ban: 2026-03-31 14:22:41,825 ... Ban 10.82.198.105 


Unban: 2026-03-31 14:23:41,085 ... Unban 10.82.198.105