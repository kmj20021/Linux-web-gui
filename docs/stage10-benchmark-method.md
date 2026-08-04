# Stage 10 성능·연구 데이터 재현 절차

이 벤치마크는 제품 API와 운영 DB에서 분리된 `backend/benchmarks` 패키지다. 고정 fixture의 동일 문제를 `pure_llm`과 규칙 기반 상태·판정을 제공하는 `structured_state` 변형에 교대로 배분한다. 상태와 정답 판정의 기준은 Bedrock 응답이 아니라 프로젝트 fixture와 규칙 기반 채점기다.

기본 실행은 mock이며 네트워크를 사용하지 않는다.

```bash
cd backend
PYTHONPATH=. .venv/bin/python -m benchmarks.stage10
```

승인된 실제 호출은 다음처럼 명시적으로 활성화한다. 리전은 `us-east-1`, inference profile은 `us.anthropic.claude-haiku-4-5-20251001-v1:0`, API는 Converse로 고정된다. 30개 성공 표본을 목표로 순차 실행하며 전체 API 호출은 최대 40회다.

```bash
cd backend
RUN_BEDROCK_BENCHMARK=1 PYTHONPATH=. .venv/bin/python -m benchmarks.stage10
```

원자료 JSONL의 첫 줄은 실행 manifest이고 이후 줄은 개별 표본이다. summary JSON은 원자료에서 다시 계산할 수 있다. 원문 prompt 대신 SHA-256, 비밀이 아닌 request ID, 토큰 수, 지연시간, 오류 분류만 저장한다. AWS 자격 증명, JWT, 비밀번호, 개인정보는 저장하지 않는다.

자동 평가는 strict JSON parse, authoritative grade 일치, 모순 여부만 다룬다. 전문가의 힌트 적합성, 사용자 학습 효과, 인과 효과는 평가하지 않았다. 공식 단가의 신뢰 가능한 기준시점을 이번 환경에서 확보하지 않았으므로 가격과 추정 비용은 `null`이며 토큰 수와 산식만 남긴다.

제한사항으로 Stage 9의 webterm IMDS 격리는 해결되지 않았고 실제 브라우저 사용자 실험도 수행하지 않았다. 따라서 결과는 시스템 지연시간·스키마 준수·상태 판정 일관성 자료이며 사람 대상 학습 효과나 IRB 연구 결과가 아니다.

## 2026-07-22 최초 live 실행 결과

최초 bounded live 실행은 Converse transport 응답을 40회 수신했지만, 당시 runner의 exact JSON parser가 Markdown JSON code fence를 허용하지 않는 등 실제 모델 출력 형태와 계약이 맞지 않아 strict valid sample은 0개였다. 호출 상한 40회에서 중단했으며 추가 호출은 하지 않았다. 이 실행은 모델 품질 0%의 근거가 아니라 측정 도구의 schema-contract 결함을 발견한 pilot 결과다.

parser는 단일 JSON code fence를 벗긴 뒤에도 정확한 세 필드만 허용하도록 수정했고 해당 관찰 형태를 mock 회귀에 추가했다. 그러나 같은 live 입력으로 재측정하지 않았으므로 Stage 10은 `PARTIAL`이며, 별도 승인된 bounded 재실행에서 성공 표본 30개를 확보하기 전에는 두 variant의 정확도를 비교하거나 결론 내릴 수 없다.

artifact schema를 정규화하는 과정에서 이미 hash-only로 바뀐 request ID 필드를 재처리해 40개 hash가 소실된 도구 결함도 발견했다. 정규화 전 집계에서 40/40 request ID 존재가 확인되었으므로 presence는 유지하지만, 복구할 원문이나 백업이 없어 per-sample hash는 `null`이고 `artifact_normalization_loss=request_id_hash_lost_after_verified_presence`로 표시한다. hash를 임의 생성하지 않았으며, 정규화 함수는 기존 hash-only 레코드를 보존하도록 수정했다. 별도 승인 재실행에서는 새 runner가 원문 ID를 저장하지 않고 즉시 hash만 저장한다.
