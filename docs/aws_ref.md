# Amazon Bedrock / AWS 연동 참고서

> 기준일: 2026-07-21
>
> 목적: Polylog에서 Bedrock을 붙이며 확인한 문제와 결정을 다른 프로젝트에서 재사용하기 위한 실전 메모
>
> 주의: 모델 ID, 지원 리전, 요금, 쿼터, 모델 액세스 절차는 자주 바뀐다. 새 프로젝트에서는 반드시 [AWS 모델 카탈로그](https://docs.aws.amazon.com/bedrock/latest/userguide/models.html)와 대상 모델의 상세 페이지를 다시 확인한다.

## 1. 먼저 기억할 결론

1. **리전, 모델 ID, 호출 방식은 한 묶음으로 검증한다.** 모델 이름만 바꾸면 끝나지 않는다. 해당 리전에서 모델이 지원되는지, 직접 호출 가능한지, inference profile이 필요한지까지 확인해야 한다.
2. **`AccessDeniedException`은 IAM 문제만 뜻하지 않는다.** 실행 역할, AWS Marketplace 구독 권한, Anthropic 최초 사용 양식(FTU), inference profile의 목적지 리전, Organizations SCP를 함께 확인한다.
3. **최신 모델은 foundation model ID 직접 호출 대신 inference profile ID가 필요할 수 있다.** Polylog의 Sonnet 4.6은 `us.anthropic.claude-sonnet-4-6`을 `modelId`로 사용한다.
4. **LLM 호출 실패를 조용히 삼키지 않는다.** 사용자에게는 안전하게 폴백하더라도 CloudWatch에는 오류 코드, 모델 ID, 리전, request ID를 남겨야 한다.
5. **동기 API의 시간 예산을 먼저 정한다.** Bedrock 2회와 외부 API를 한 요청에 직렬로 묶으면 API Gateway 제한에 쉽게 닿는다. 오래 걸리는 작업은 비동기화하거나 빠른 CRUD와 함수를 분리한다.
6. **모델 출력은 항상 불신한다.** JSON만 요청해도 코드펜스나 설명이 섞일 수 있으므로 파싱, 스키마 검증, 값 범위 제한, 폴백이 필요하다.
7. **비전 모델은 OCR 전용 도구의 완전한 대체재가 아니다.** 정형 영수증에는 유용했지만, 밀도 높은 메뉴판의 판독·번역·추천을 작은 모델 한 번에 맡기자 품질이 불안정했다.
8. **AWS 서비스의 숨은 의존 권한을 실제 실행 역할로 검증한다.** Polylog에서는 Translate의 자동 언어 감지가 Comprehend 권한을 필요로 해 전체 번역이 실패했다.

---

## 2. Polylog에서 실제로 사용한 구조

```text
Client
  -> API Gateway REST API (ap-northeast-2)
  -> Lambda (ap-northeast-2)
       -> Bedrock Runtime (us-east-1)
       -> DynamoDB / S3 (ap-northeast-2)
       -> 필요 시 외부 API
```

- 일반 AWS 자원은 서울(`ap-northeast-2`), Bedrock만 버지니아 북부(`us-east-1`)를 명시해 호출했다.
- 빠른 의도 분류는 Claude 3 Haiku, 복잡한 동선 큐레이션은 Sonnet을 사용했다.
- 추천·플래너·영수증은 최대 30초 Lambda로 구성했다.
- 이미지 처리 함수는 256MB, 일반 텍스트 함수는 128MB로 시작했다.
- 공용 교육 계정 제약 때문에 모든 Lambda가 `SafeRole-polylog`를 공유했다. 이는 **이 프로젝트의 예외**이며, 새 운영 프로젝트에서는 함수별 최소 권한 역할을 권장한다.

관련 구현:

- `backend/src/handlers/recommend/app.py`
- `backend/src/handlers/planner/app.py`
- `backend/src/handlers/receipt/app.py`
- `backend/template.yaml`
- `scripts/deploy.sh`
- `docs/ADR.md`의 ADR-004, 009, 012, 013, 016~018

---

## 3. 트러블 이슈와 교훈

### 3.1 Bedrock 리전과 서비스 리전이 달랐다

**증상**

- 기본 리전인 서울에서 모델을 찾지 못하거나 호출이 거부됨
- 같은 모델 ID인데 콘솔에서 보이는 리전과 Lambda가 호출하는 리전이 다름

**Polylog의 처리**

```python
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
```

S3와 DynamoDB 클라이언트는 `ap-northeast-2`, Bedrock Runtime만 `us-east-1`로 분리했다.

**다른 프로젝트의 권장안**

- 리전을 코드 곳곳에 하드코딩하지 말고 `BEDROCK_REGION`으로 분리한다.
- 배포 전에 대상 모델 상세 페이지에서 다음 네 가지를 함께 확인한다.
  - 모델의 in-region 지원 여부
  - source region에서 사용할 수 있는 geo/global inference profile
  - 정확한 model/profile ID
  - 데이터가 라우팅될 수 있는 destination region
- 데이터 레지던시 요구가 있으면 global profile을 무심코 선택하지 않는다. Geo profile도 프롬프트와 응답이 같은 지리권 내 다른 리전에서 처리될 수 있다.

공식 문서: [Inference profile 지원 리전과 모델](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html), [Cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)

### 3.2 Sonnet 직접 호출이 아니라 inference profile이 필요했다

**증상**

- 모델 자체 ID를 `modelId`에 넣었을 때 on-demand throughput 관련 `ValidationException` 발생
- 다른 모델은 되는데 최신 Sonnet만 실패

**해결**

Polylog의 현재 기본값은 다음과 같다.

```python
INTENT_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
PLANNER_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
```

Sonnet 4.6은 US geographic inference profile ID를 사용한다. 모델 교체가 배포 없이 가능하도록 실제 코드에서는 환경변수로 덮어쓸 수 있게 했다.

```python
model_id = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-sonnet-4-6",
)
```

**주의**

- `anthropic...`은 foundation model ID이고 `us.anthropic...`, `eu.anthropic...`, `global.anthropic...` 등은 inference profile ID다.
- profile을 호출하려면 profile 자체뿐 아니라 profile이 라우팅할 수 있는 모든 destination foundation model에 대한 IAM/SCP 허용이 필요할 수 있다.
- profile의 목적지 목록은 바뀔 수 있으므로 배포 시점에 `GetInferenceProfile`로 확인한다.

공식 문서: [Claude Sonnet 4.6 모델 정보와 ID](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-6.html), [Geographic cross-Region inference의 IAM 요구사항](https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html)

### 3.3 모델 액세스 실패를 단순 IAM 문제로 오해하기 쉽다

2026년 현재 상용 리전의 foundation model은 필요한 AWS Marketplace 권한이 있으면 기본적으로 액세스가 활성화된다. 다만 다음 조건이 남아 있다.

- 최초 third-party model 사용 시 Marketplace 구독 처리가 진행될 수 있다.
- 호출 주체에 `aws-marketplace:Subscribe`, `Unsubscribe`, `ViewSubscriptions`가 없으면 자동 구독이 실패할 수 있다.
- Anthropic 모델은 계정 또는 Organizations 관리 계정에서 최초 1회 use-case 양식 제출이 필요하다.
- 구독 직후 전파 중에는 잠시 `AccessDeniedException`이 날 수 있다.
- 실제 Lambda 실행 역할에는 별도로 `bedrock:InvokeModel` 권한이 있어야 한다.

따라서 `AccessDeniedException`은 다음 순서로 확인한다.

1. `aws sts get-caller-identity`로 지금 테스트하는 주체가 누구인지 확인
2. 콘솔 사용자/CloudShell 역할과 Lambda 실행 역할을 혼동하지 않았는지 확인
3. Anthropic FTU와 model availability 확인
4. 실행 역할의 `bedrock:InvokeModel` 확인
5. inference profile 및 모든 destination model ARN 허용 확인
6. permission boundary와 Organizations SCP의 리전 제한 확인

공식 문서: [모델 액세스 요청 및 Anthropic FTU](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)

### 3.4 오류를 삼키자 “AI가 이상하다”로만 보였다

초기 코드는 Bedrock 예외를 빈 문자열로 바꿔 서비스가 죽지 않게 했지만, 로그까지 남기지 않아 모델 액세스와 payload 오류를 구분하기 어려웠다. 이후 사용자 응답은 폴백하되 CloudWatch에는 원인을 남기도록 변경했다.

```python
try:
    return invoke_bedrock(...)
except Exception as exc:
    logger.warning(
        "Bedrock invocation failed (region=%s, model=%s): %s",
        region,
        model_id,
        exc,
    )
    return ""
```

새 프로젝트에서는 `botocore.exceptions.ClientError`를 먼저 잡아 최소한 아래를 구조화 로그로 남기는 편이 좋다.

- `Error.Code`: `AccessDeniedException`, `ValidationException`, `ThrottlingException` 등
- `Error.Message`
- `ResponseMetadata.RequestId`
- 호출 리전, 모델/profile ID, 기능명, 소요 시간
- 민감한 원문 프롬프트나 이미지는 기본 로그에 남기지 않음

사용자에게도 정상 결과와 폴백 결과를 구분할 수 있는 `degraded`, `reason`, `retryable` 같은 신호를 주는 것이 좋다.

### 3.5 30초짜리 Lambda가 곧 30초짜리 API는 아니다

Polylog 플래너는 Bedrock 2회와 Places API를 순차 호출해 10초 Lambda 제한을 넘겼고, 30초로 올린 뒤 빠른 일정 CRUD와 별도 `fn-planner`로 분리했다.

여기서 중요한 점은 **Lambda timeout과 API Gateway integration timeout이 별개**라는 것이다.

- HTTP API integration timeout은 최대 30초다.
- REST API의 기본 integration timeout은 29초다.
- Regional/private REST API는 계정 쿼터 조정으로 29초보다 늘릴 수 있지만, account-level throttle quota 감소가 필요할 수 있다.
- Lambda가 30초여도 Gateway가 먼저 끊으면 클라이언트는 5xx를 받고 Lambda는 뒤에서 계속 실행될 수 있다.

동기 요청이라면 보통 다음처럼 바깥 계층보다 안쪽 계층이 먼저 통제된 실패를 반환하도록 시간 예산을 잡는다.

```text
Bedrock SDK read timeout < Lambda timeout < API Gateway timeout < client timeout
```

30초 안에 안정적으로 끝난다는 보장이 없으면 다음 구조가 낫다.

```text
POST /jobs -> 202 + job_id
             -> SQS / Step Functions / 비동기 Lambda
GET /jobs/{id} -> 상태와 결과 조회
```

공식 문서: [HTTP API 쿼터](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html), [REST API 쿼터](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html)

### 3.6 분류와 생성에 같은 temperature를 쓰면 결과가 흔들렸다

플래너의 의도 분류를 `temperature=0.5`로 호출했을 때 같은 발화에서도 검색 여부가 간헐적으로 달라졌다. 분류 호출은 `0.1`, 동선 큐레이션은 `0.5`로 분리했다.

교훈:

- 분류, 라우팅, JSON 추출: 낮은 temperature
- 문구 생성, 추천 설명: 조금 높은 temperature 허용
- LLM의 분류 결과 하나만 믿지 말고 중요한 라우팅에는 규칙 기반 안전망을 둠
- 프롬프트 변경은 몇 개의 고정 예제가 아니라 작은 회귀 eval set으로 검증

### 3.7 JSON만 요청해도 JSON만 오지 않았다

Polylog는 첫 `{`부터 마지막 `}`까지 잘라 파싱하는 방어 로직을 사용했다.

```python
def safe_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        value = json.loads(text[start:end + 1])
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}
```

이것은 최소 방어일 뿐이다. 새 프로젝트에서는 가능하면 지원 모델의 structured outputs 또는 tool schema를 사용하고, 애플리케이션 경계에서 JSON Schema/Pydantic 등으로 다음까지 검증한다.

- 필수 필드 존재 여부
- 문자열 길이와 배열 개수 상한
- enum과 숫자 범위
- 외부 ID가 실제 후보 목록에 있는지
- 모델이 만든 URL, 파일 경로, 명령을 곧바로 실행하지 않는지

### 3.8 Textract는 CJK 시나리오에 맞지 않았다

실기기 테스트에서 한글 영수증과 일본어 메뉴판이 제대로 인식되지 않았다. AWS 문서상 Textract text detection 지원 언어는 영어, 프랑스어, 독일어, 이탈리아어, 포르투갈어, 스페인어이며 일본어·중국어에 흔한 세로쓰기 역시 지원하지 않는다.

Polylog는 영수증을 Claude Haiku 비전으로 직접 읽게 해 판독, 통화, 항목, 카테고리 구조화를 한 번에 처리했다. 정형 영수증에는 충분했지만, 메뉴판에서는 다음 문제가 있었다.

- 글자 밀도와 사진 품질에 따라 결과 편차가 큼
- 작은 모델 한 번에 OCR, 번역, 설명, 추천을 모두 맡기면 한 작업의 오류가 다음 작업으로 전파됨
- 메뉴판만으로 알레르기 정보를 확정할 수 없어 추천이 추측이 됨

결국 메뉴 번역은 Google Lens에 위임하고, 정형 영수증만 Bedrock 비전을 유지했다.

교훈은 “Bedrock 비전이 Textract보다 항상 낫다”가 아니라 **실제 언어, 문서 형태, 촬영 환경으로 평가한 뒤 전용 OCR/비전 모델/외부 도구를 선택하라**는 것이다.

공식 문서: [Textract 지원 언어와 제한](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html)

### 3.9 Translate 자동 감지의 숨은 권한 때문에 전 항목이 실패했다

초기 메뉴 번역에서 `SourceLanguageCode="auto"`를 사용했다. 자동 감지는 내부적으로 Amazon Comprehend의 `DetectDominantLanguage` 권한을 필요로 했지만 공용 실행 역할에 권한이 없었다. 번역 예외를 원문 폴백으로 바꾸고 있었기 때문에 겉으로는 “번역 결과가 원문과 같다”만 보였다.

교훈:

- 서비스 A의 편의 옵션이 서비스 B 권한을 요구할 수 있다.
- 콘솔 사용자로 성공한 테스트는 Lambda 실행 역할의 성공을 보장하지 않는다.
- 최소 권한 환경에서는 실제 실행 역할로 happy path와 permission failure를 모두 테스트한다.
- 폴백을 쓰더라도 폴백 횟수와 원인을 metric/log로 남긴다.

### 3.10 이미지 base64는 크기와 비용을 동시에 키운다

Polylog는 원본 이미지 5MB 상한을 두고 API에 base64로 전달했다. base64는 원본보다 대략 33% 커지고 JSON 오버헤드가 추가된다. API Gateway payload 제한도 있으므로 원본 파일 제한만 보면 안 된다.

권장 구조:

- 작은 PoC: 클라이언트 리사이즈/압축 -> MIME type과 byte 상한 검증 -> Bedrock 호출
- 운영: presigned URL로 S3 직접 업로드 -> 백엔드는 객체 크기/MIME/magic bytes 검증 -> 필요 시 리사이즈 -> 추론
- 개인정보 이미지: 짧은 보존 기간, S3 Block Public Access, SSE, lifecycle 삭제, 로그 제외
- 모델 invocation logging을 켜면 입력/출력과 이미지가 S3/CloudWatch에 저장될 수 있으므로 개인정보 정책을 먼저 정함

API Gateway HTTP API의 payload 한도는 10MB이며 증가할 수 없다. 공식 문서: [HTTP API 쿼터](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html), [Bedrock model invocation logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)

---

## 4. 새 프로젝트 권장 구성

### 4.1 환경변수

```text
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
BEDROCK_MAX_TOKENS=1024
BEDROCK_READ_TIMEOUT_SECONDS=25
```

- 모델과 리전은 환경별 설정으로 둔다.
- 실제 secret이 아니므로 모델 ID를 Secrets Manager에 넣을 필요는 없다.
- API 키나 외부 서비스 secret은 코드, SAM 파라미터 기본값, 로그에 넣지 않는다. 운영에서는 Secrets Manager/SSM Parameter Store를 검토한다.

### 4.2 IAM

PoC 확인용 최소 동작은 다음 action에서 시작할 수 있다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

운영에서는 `Resource: "*"`를 그대로 두지 말고 다음으로 좁힌다.

- 허용할 inference profile ARN
- profile이 사용할 수 있는 모든 destination foundation model ARN
- 필요하면 `bedrock:InferenceProfileArn` 조건
- 호출하지 않는 모델/provider에 대한 명시적 제한

그리고 함수별로 역할을 분리한다. Polylog의 공용 `SafeRole-polylog`는 교육용 공용 계정에서 `iam:CreateRole`이 막혀 선택한 타협이다.

### 4.3 Boto3 호출 골격

신규 텍스트/대화 기능은 모델 간 인터페이스를 통일하기 쉬운 `Converse`를 우선 검토한다. provider 고유 파라미터나 기존 Anthropic Messages payload가 필요하면 `InvokeModel`을 사용한다.

```python
import logging
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ["BEDROCK_REGION"]
MODEL_ID = os.environ["BEDROCK_MODEL_ID"]

client = boto3.client(
    "bedrock-runtime",
    region_name=REGION,
    config=Config(
        connect_timeout=3,
        read_timeout=int(os.environ.get("BEDROCK_READ_TIMEOUT_SECONDS", "25")),
        retries={"mode": "standard", "max_attempts": 3},
    ),
)


def ask(prompt: str) -> str:
    try:
        response = client.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": int(os.environ.get("BEDROCK_MAX_TOKENS", "1024")),
                "temperature": 0.1,
            },
        )
        return "".join(
            block.get("text", "")
            for block in response["output"]["message"]["content"]
        ).strip()
    except ClientError as exc:
        error = exc.response.get("Error", {})
        meta = exc.response.get("ResponseMetadata", {})
        logger.warning(
            "bedrock_failed code=%s request_id=%s region=%s model=%s",
            error.get("Code"),
            meta.get("RequestId"),
            REGION,
            MODEL_ID,
        )
        raise
```

AWS 공식 API 비교: [Bedrock에서 지원하는 API](https://docs.aws.amazon.com/bedrock/latest/userguide/apis.html)

### 4.4 재시도

- `ThrottlingException`, 일시적 5xx, 연결 reset에는 exponential backoff와 jitter를 사용한다.
- `AccessDeniedException`, 잘못된 payload의 `ValidationException`은 재시도로 해결되지 않는다.
- 동기 API에서 재시도 횟수를 크게 잡으면 Gateway timeout을 먼저 소진할 수 있다.
- 쓰기 작업이나 tool 호출을 재시도한다면 idempotency key를 둔다.

공식 문서: [Bedrock 오류 코드](https://docs.aws.amazon.com/bedrock/latest/userguide/troubleshooting-api-error-codes.html), [Boto3 retries](https://docs.aws.amazon.com/boto3/latest/guide/retries.html)

### 4.5 관측성과 비용

최소 대시보드/알람:

- `Invocations`
- `InvocationLatency` p50/p95/p99
- `InvocationClientErrors`, `InvocationServerErrors`
- `InvocationThrottles`
- `InputTokenCount`, output token 관련 지표
- 애플리케이션의 fallback 비율과 빈 응답 비율

Bedrock model invocation logging은 기본 비활성화다. 켜면 디버깅에 유용하지만 전체 prompt/response와 이미지가 저장될 수 있으므로 운영에서는 마스킹, 보존 기간, 접근 권한을 먼저 결정한다.

프로젝트/팀별 비용 분리가 필요하면 application inference profile에 cost allocation tag를 붙이는 방식을 검토한다. 단, 비용 태그는 활성화 이후부터 적용되고 소급되지 않는다.

공식 문서: [Bedrock CloudWatch metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-metrics.html), [Application inference profiles와 비용 추적](https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html)

---

## 5. 배포와 AWS 운영에서 주의할 점

### 5.1 코드 업데이트와 설정 업데이트는 별개다

`aws lambda update-function-code`는 코드만 바꾼다. timeout, memory, environment variable, role은 자동으로 갱신되지 않는다. Polylog 배포 스크립트도 코드 업데이트 뒤 `update-function-configuration`을 별도로 실행한다.

또한 CLI의 `--environment "Variables={...}"`는 기존 환경변수에 한 키를 추가하는 merge가 아니라 전체 map 교체로 사용할 수 있으므로, 여러 변수가 있는 함수에서는 기존 값을 조회해 함께 전달하거나 SAM/CloudFormation을 정본으로 삼는다.

### 5.2 IaC를 정본으로 유지한다

Polylog는 계정 정책상 `lambda:TagResource`가 막혀 CloudFormation의 생성 직후 조회가 실패했고, 관리자 자동 태깅을 기다리는 별도 배포 스크립트를 사용했다. 이것도 일반적인 AWS 요구사항이 아니라 해당 공용 계정의 특수 제약이다.

새 프로젝트에서는 가능하면 다음을 한 템플릿에서 관리한다.

- Lambda 코드 위치, runtime, handler
- timeout, memory, architecture
- 함수별 execution role
- 환경변수와 secret 참조
- API Gateway route와 integration timeout
- 로그 보존 기간과 alarm
- 리소스 태그

수동 콘솔 변경은 다음 배포에서 되돌아가거나 drift가 생긴다.

### 5.3 Polylog 공용 계정에서만 적용된 제약

아래를 새 프로젝트의 AWS 일반 규칙으로 오해하지 않는다.

- 모든 리소스 이름에 `polylog-` prefix 강제
- `group=polylog` 태그가 없으면 explicit deny
- `iam:CreateRole`, `lambda:TagResource` 차단
- Access Key 미발급으로 CloudShell 전용 배포
- 모든 Lambda가 `SafeRole-polylog` 공유
- Cognito, CloudFront 사용 제한

새 계정에서는 IAM Identity Center/단기 자격증명, 함수별 최소 권한, CI/CD의 OIDC role assumption을 우선 검토한다. 장기 access key를 CI secret으로 만드는 것은 피한다.

### 5.4 현재 템플릿을 복사할 때의 추가 주의

현재 `backend/template.yaml`에는 `FnAuthorizer` logical ID가 두 번 선언돼 있다. 일부 YAML 파서는 중복 키를 오류로 내지 않고 뒤 정의로 덮어쓸 수 있다. 다른 프로젝트로 복사하기 전에 중복 logical ID 검사와 `sam validate --lint`를 CI에 넣는다.

---

## 6. 오류별 빠른 진단표

| 증상/오류 | 우선 확인 | 흔한 원인 | 조치 |
|---|---|---|---|
| `AccessDeniedException` | caller ARN, Lambda role, FTU, Marketplace, IAM/SCP | 테스트 주체 혼동, 모델 구독 미완료, destination region 차단 | 실제 실행 역할로 재현하고 권한 계층별 확인 |
| `ValidationException` | model/profile ID와 payload | 직접 호출 불가 모델, provider payload 불일치, 토큰/이미지 제한 | 모델 상세 페이지의 API와 정확한 ID 확인 |
| `ResourceNotFoundException` | endpoint region과 ID | 다른 리전의 모델/profile ARN 사용 | control plane과 runtime 리전 확인 |
| `ThrottlingException` | Service Quotas, `InvocationThrottles` | RPM/TPM 초과, 동시 버스트 | 표준 retry+jitter, 요청 평탄화, quota/profile 검토 |
| `ServiceUnavailableException`/5xx | AWS 상태, retry 횟수 | 일시 장애/용량 부족 | 제한된 retry, cross-region profile, 폴백 |
| API Gateway 5xx/504 | Gateway integration timeout, Lambda duration | Lambda 30초와 Gateway 29초 불일치 | 시간 예산 재설계 또는 비동기화 |
| 200인데 AI 결과가 비어 있음 | Lambda application log | catch-all이 예외를 빈 문자열로 변환 | 오류 코드 로깅, degraded 응답 추가 |
| JSON 파싱 실패 | 원문 응답의 앞뒤 텍스트 | 코드펜스/설명/잘린 출력 | structured output, max tokens, schema 검증 |
| 이미지 요청 413 | 원본과 base64 후 크기 | base64 팽창, Gateway payload 제한 | 클라이언트 압축 또는 S3 직접 업로드 |
| 로컬 성공/Lambda 실패 | `sts get-caller-identity` | 서로 다른 IAM principal과 리전 | Lambda 역할로 배포한 진단 호출 수행 |

---

## 7. 배포 전 체크리스트

### 계정과 모델

- [ ] 대상 계정/리전에서 모델 availability 확인
- [ ] Anthropic FTU 제출 확인
- [ ] foundation model ID인지 inference profile ID인지 확인
- [ ] profile의 source/destination region과 데이터 레지던시 확인
- [ ] Marketplace/IAM/SCP/permission boundary 확인

### 코드

- [ ] `BEDROCK_REGION`, `BEDROCK_MODEL_ID`를 환경 설정으로 분리
- [ ] SDK connect/read timeout과 표준 retry 설정
- [ ] JSON/structured output 스키마 검증
- [ ] 모델 출력의 외부 ID와 enum을 서버에서 재검증
- [ ] catch-all 폴백에도 오류 코드와 request ID 로깅
- [ ] 프롬프트, 이미지, 개인정보를 일반 로그에서 제외

### 인프라

- [ ] Bedrock 호출 함수만 `bedrock:InvokeModel` 허용
- [ ] cross-region profile과 destination model ARN을 모두 허용
- [ ] Lambda, Gateway, client timeout을 일관되게 설정
- [ ] 30초를 넘길 가능성이 있으면 비동기 구조 선택
- [ ] 이미지/API payload 상한과 S3 lifecycle 설정
- [ ] CloudWatch 지표, 알람, 로그 보존 기간 설정
- [ ] Budgets와 cost allocation tag 활성화
- [ ] `sam validate --lint` 및 배포 후 smoke test

### 품질

- [ ] 실제 사용자 언어와 입력 품질을 반영한 작은 eval set 준비
- [ ] 정상, 흐린 이미지, 큰 이미지, 빈 문서, 다국어, 악성 prompt 테스트
- [ ] 권한 거부, throttle, timeout, 잘못된 JSON의 폴백 테스트
- [ ] 모델 ID 교체 전후 회귀 테스트

---

## 8. 최소 진단 명령

```bash
# 현재 CLI 주체 확인
aws sts get-caller-identity

# 리전의 foundation model 목록 확인
aws bedrock list-foundation-models --region us-east-1

# 특정 모델의 계정 가용성 확인
aws bedrock get-foundation-model-availability \
  --model-id anthropic.claude-sonnet-4-6 \
  --region us-east-1

# inference profile과 목적지 모델 확인
aws bedrock get-inference-profile \
  --inference-profile-identifier us.anthropic.claude-sonnet-4-6 \
  --region us-east-1

# Lambda의 실제 timeout, memory, role, env 확인
aws lambda get-function-configuration \
  --function-name <FUNCTION_NAME> \
  --region <LAMBDA_REGION>

# 최근 Lambda 로그 확인
aws logs tail /aws/lambda/<FUNCTION_NAME> \
  --since 10m --follow \
  --region <LAMBDA_REGION>
```

CLI가 최신 모델/API를 알지 못하면 AWS CLI와 배포 패키지의 boto3/botocore 버전을 먼저 확인한다. Lambda 런타임 내장 SDK만 사용할 때는 새 API 지원 시점이 런타임과 다를 수 있으므로, 최신 기능을 사용한다면 SDK 버전을 애플리케이션 의존성으로 고정하는 방안도 검토한다.

---

## 9. 이 프로젝트에서 재사용할 것과 버릴 것

**재사용할 것**

- Bedrock 리전을 명시적으로 분리한 클라이언트 구성
- 모델 ID를 환경변수로 교체 가능하게 한 방식
- 빠른 Haiku/복잡한 Sonnet의 역할 분리
- 무거운 AI 플래너와 빠른 CRUD Lambda 분리
- 입력 크기 제한, JSON 방어 파싱, 후보 ID 재검증
- 사용자 폴백과 CloudWatch 오류 로그를 함께 두는 방식
- 실제 CJK 문서와 실기기로 검증한 과정

**그대로 복사하지 않을 것**

- 한 공용 IAM role을 모든 함수가 공유하는 구조
- Bedrock 모델/리전 하드코딩
- Lambda 30초만 올리고 Gateway timeout을 별도 확인하지 않는 구성
- 예외를 빈 문자열로만 바꾸는 catch-all
- 이미지 전체를 항상 API Gateway base64로 전달하는 구조
- 모델에 OCR, 번역, 추천, 안전 판단을 한 번에 몰아넣는 프롬프트
- 콘솔/CloudShell 사용자 권한으로 Lambda 역할 권한까지 검증했다고 가정하는 것
