# AWS Bedrock Haiku 실호출 사전 점검

* 작업 ID: `DOC-BEDROCK-LIVE-CHECK-001`
* 문서화 작업 상태: `COMPLETED`
* Bedrock 실제 권한 및 응답 검증 상태: `PARTIAL` (권한 및 응답 미검증)

## 2026-07-21 로컬 테스트

### 테스트 대상

* 리전: `us-east-1`
* Inference profile: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
* API: Amazon Bedrock Runtime `Converse`

### 수행 내용과 결과

* 시스템 Python에 설치된 `boto3 1.43.22`로 위 inference profile에 `Converse` 호출을 시도했다.
* AWS 자격 증명을 찾지 못해 `NoCredentialsError: Unable to locate credentials`가 발생했다.
* 이 오류는 Bedrock 서비스가 반환한 응답이 아니라 로컬 boto3 자격 증명 탐색 단계에서 발생했다. 따라서 네트워크 요청은 전송되지 않았고 Bedrock 모델 접근 권한과 실제 응답 동작은 확인되지 않았다.
* 로컬 환경에는 사용할 수 있는 AWS profile, `AWS_*` 자격 증명 환경 변수, `~/.aws/credentials`, `~/.aws/config`가 없었다. 자격 증명 값은 생성하거나 기록하지 않았다.
* 백엔드 가상환경과 `backend/requirements.txt`에는 `boto3`가 없었다.
* Docker daemon이 실행 중이지 않아 백엔드 컨테이너 환경에서는 검증하지 못했다.

### 현재 판정

* 로컬 호출: `FAIL` (`NoCredentialsError`)
* Bedrock 서비스 도달 여부: `미검증`
* Haiku inference profile 호출 권한: `미검증`
* Haiku 응답 정상 수신: `미검증`

### EC2 후속 확인

EC2 instance role이 연결된 실제 백엔드 실행 환경에서 동일한 리전과 inference profile로 `Converse` smoke test를 다시 수행한다.

1. 실제 백엔드 실행 환경에서 `boto3`를 사용할 수 있는지 확인한다.
2. 리전을 `us-east-1`로 지정한다.
3. `us.anthropic.claude-haiku-4-5-20251001-v1:0`에 짧은 입력으로 `Converse`를 호출한다.
4. 응답 본문을 정상 수신해야 Haiku 동작과 권한을 확인한 것으로 판정한다. `AccessDeniedException` 등 오류가 발생하면 오류 유형을 기록하고 instance role 정책과 inference profile 권한을 확인한다.
5. Haiku 호출 성공을 확인한 뒤 별도로 승인된 Sonnet inference profile로 모델 설정을 변경한다.

### 알려진 위험 및 후속 정보

* Sonnet inference profile ID가 아직 제공되지 않아 Haiku 검증 후 전환할 대상을 확정할 수 없다.

프로덕션 Bedrock 클라이언트와 스트리밍 클라이언트 구현, 의존성 변경, EC2 원격 테스트는 이 점검 범위에 포함하지 않았다.
