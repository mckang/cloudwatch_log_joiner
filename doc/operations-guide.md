# 운영 가이드

## 1. 기본 점검 순서
1. `.env` 파일에 AWS 키 쌍이 모두 존재하는지 확인
2. `config.yaml`의 `analysis_steps`, `final_join_sqls` 필수 필드 확인
3. `--dry-run`으로 설정 검증 후 본 실행

## 2. 자주 발생하는 문제 해결

### `LJ001` (입력 오류)
- 증상: 실행 직후 종료
- 조치:
  - 시간 형식이 `yyyy-MM-dd HH:mm:ss`인지 확인
  - `--skip-extract` 사용 시 `--start`, `--end` 동시 지정 여부 확인
  - YAML 키 오탈자 확인

### `LJ101` (AWS 오류)
- 증상: 스텝 실행 중 실패 또는 타임아웃
- 조치:
  - `--retry-attempts`, `--retry-backoff-seconds` 상향
  - 조회 시간 구간 축소
  - CloudWatch 로그 그룹 권한/리전 확인

### `LJ201` (SQL 오류)
- 증상: 조인 단계에서 실패
- 조치:
  - `final_join_sqls.query` 문법 점검
  - `analysis_steps[].name` 참조명이 정확한지 확인
  - `@timestamp` 정렬이 필요한 경우 컬럼 포함 여부 확인

### `LJ301` (파일 I/O 오류)
- 증상: output 초기화/CSV 저장 실패
- 조치:
  - 실행 경로 쓰기 권한 확인
  - 상대경로 대신 절대경로로 `save_as` 지정해 재시도

## 3. 재시도 튜닝 가이드
- 기본 권장값:
  - `--retry-attempts 3`
  - `--retry-backoff-seconds 1.0`
- API 불안정 시간대:
  - `--retry-attempts 5`
  - `--retry-backoff-seconds 2.0`
- 타임아웃이 잦으면 `--poll-timeout-seconds`를 단계적으로 증가

## 4. 비용 주의사항
- 넓은 시간 범위 + 낮은 필터 조건은 조회 비용 증가 위험이 큼
- `extract_pattern`과 쿼리 필터를 먼저 좁힌 뒤 실행
- `query_limit` 상한 도달 시 자동 분할이 동작하므로, 필요 이상으로 큰 범위를 한 번에 요청하지 않기
