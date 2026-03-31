import re

# 로그 샘플 
log_lines = [
    "2026-03-31 14:22:41,171 fail2ban.filter         [815]: INFO    [sshd] Found 10.82.198.105 - 2026-03-31 14:22:40",
    "2026-03-31 14:22:41,825 fail2ban.actions        [815]: NOTICE  [sshd] Ban 10.82.198.105",
    "2026-03-31 14:23:41,085 fail2ban.actions        [815]: NOTICE  [sshd] Unban 10.82.198.105"
]

# 공통 정규식 구성 요소
ts_re = r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
jail_re = r'\[(?P<jail>\S+)\]'
ip_re = r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3})'

patterns = {
    "Found": re.compile(rf"{ts_re} fail2ban\.filter.*INFO\s+{jail_re} Found {ip_re}"),
    "Ban": re.compile(rf"{ts_re} fail2ban\.actions.*NOTICE\s+{jail_re} Ban {ip_re}"),
    "Unban": re.compile(rf"{ts_re} fail2ban\.actions.*NOTICE\s+{jail_re} Unban {ip_re}")
}

for line in log_lines:
    for event_type, p in patterns.items():
        match = p.search(line)
        if match:
            print(f"[{event_type}] 시간: {match.group('timestamp')}, 감옥: {match.group('jail')}, IP: {match.group('ip')}")