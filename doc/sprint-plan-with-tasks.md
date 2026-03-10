# LogJoiner Sprint Plan (Task 포함)

## 계획 개요
- 기준 문서: `prd.md`, `epic-story-backlog.md`
- 스프린트 길이: 2주
- 목표: MVP 구축 + 운영 안정화
- 우선순위 기준: P0(필수) -> P1(중요) -> P2(확장)

## 구현 기준 (`config.yaml` 샘플 반영)
- 실행기는 아래 설정 키를 직접 읽어 동작해야 한다.
- 기준 샘플 파일: `config.sample.yaml`
  - `log_group_name`, `extract_pattern`, `output_file(폴백)`
  - `analysis_steps[].{name,query,save_as}`
  - `final_join_sqls[].{name,query,save_as}`
- `analysis_steps[].query`에 `%s`가 있으면 `extract_pattern`으로 치환 후 실행한다.
- `final_join_sqls.query`는 `analysis_steps[].name`을 `FROM/JOIN` 소스로 참조할 수 있다.
- 최종 결과는 `final_join_sqls[].save_as` 기준으로 저장한다.

## Sprint 1 (2주): 입력/설정/기본 추출 파이프라인
**Sprint Goal**
- CLI 입력과 YAML 설정을 안정적으로 처리하고, CloudWatch 단일/다단계 기본 추출 흐름을 완성한다.

**포함 Story**
- Story 1-1, 1-2, 1-3
- Story 2-1, 2-2, 2-3, 2-4
- Story 3-1(기본), 3-2(기본 상태 처리)

### Task 목록
- [x] `cli.py`에 `--start`, `--end`, `--config` 인자 파서 구현 (P0)
- [x] 시간 형식 검증 유틸 구현 (`yyyy-MM-dd HH:mm:ss`) (P0)
- [x] KST -> UTC 변환 유틸 구현 및 단위 테스트 작성 (P0)
- [x] 기간 유효성 검증 (`start <= end`) 및 에러 메시지 표준화 (P0)
- [x] YAML 로더 구현 (`PyYAML`) 및 필수 키 스키마 검증 (P0)
- [x] 필수 키 검증에 `extract_pattern` 포함, `output_file` 폴백 키 처리 (P0)
- [x] 멀티라인 쿼리 로딩 테스트 케이스 작성 (P1)
- [x] `%s` 템플릿 치환기 구현 (`extract_pattern` 주입) (P0)
- [x] 치환 실패/패턴 누락 시 에러 처리 및 테스트 작성 (P1)
- [x] `analysis_steps` 반복 실행 골격 코드 구현 (P0)
- [x] CloudWatch Insights 쿼리 실행 함수(시작/상태조회/결과조회) 구현 (P0)
- [x] 비동기 상태 처리(Complete/Failed 중심) 구현 (P1)
- [x] 스텝별 결과를 임시 JSON/CSV로 저장하는 인터페이스 정의 (P1)
- [x] README 초안: 실행 방법과 설정 예시 추가 (P2)

**완료 기준 (Definition of Done)**
- KST 입력으로 최소 2단계 스텝 실행이 가능하다.
- YAML 누락/오타에 대해 즉시 실패하고 원인 메시지를 제공한다.
- `%s` 포함 쿼리가 `extract_pattern`으로 정상 치환되어 실행된다.
- 기본 통합 테스트 1개(샘플 설정 기반)가 통과한다.

**리스크 및 대응**
- CloudWatch API 응답 지연: 폴링 간격/타임아웃 파라미터화
- 시간대 버그: 경계값 테스트(자정, 월말) 우선 추가

## Sprint 2 (2주): 스테이징/조인/최종 출력 완성
**Sprint Goal**
- 단계별 CSV 스테이징과 DuckDB 조인을 완성하고, 엑셀 호환 최종 CSV를 안정적으로 배포한다.

**포함 Story**
- Story 3-1(완성), 3-3
- Story 4-1, 4-2, 4-3
- Story 5-1, 5-2, 5-3

### Task 목록
- [x] 스텝 결과 JSON -> CSV 덤프 구현 (헤더/타입 정규화) (P0)
- [x] 파일 네이밍 정책(설정값/충돌 처리) 구현 (P1)
- [x] DuckDB 세션 생성 및 CSV 테이블 매핑 구현 (P0)
- [x] `final_join_sqls` 실행기 구현 및 SQL 오류 핸들링 강화 (P0)
- [x] 최종 정렬(`@timestamp` ASC) 강제 로직 구현 (P0)
- [x] 마지막 SQL 결과 컬럼을 그대로 export 처리 (P0)
- [x] 최종 CSV 저장 UTF-8-BOM 적용 (P0)
- [x] 최종 저장 파일명을 `final_join_sqls[].save_as`로 반영 (P0)
- [x] 실행 요약 로그(행 수, 파일 경로, 소요시간, 실패 스텝) 출력 (P1)
- [x] 재시도 정책(횟수/백오프) 구현 (P1)
- [x] 대용량 샘플 데이터로 성능 스모크 테스트 수행 (P1)

## Sprint 2.5 (반영 완료): 운영성/설정 확장
**Sprint Goal**
- 실제 사용 흐름에 맞춰 실행 정책과 설정 스키마를 고도화한다.

### Task 목록
- [x] `dotenv` 기반 AWS 인증정보 로딩(`--env-file`) 지원
- [x] 전체 실행 시 `output/` 폴더 초기화 정책 적용
- [x] `--skip-extract` 사용 시 `--start`, `--end` 선택화
- [x] `final_join_sqls` 스키마를 `name/query/save_as` 형태로 확장
- [x] `final_join_sqls.query`에서 `analysis_steps[].name` 참조 지원
- [x] CloudWatch 결과 상한 대응 자동 분할 조회(`--query-limit`, `--min-split-seconds`) 지원

**완료 기준 (Definition of Done)**
- 조인 전용 실행 시 시간 인자 없이 정상 수행된다.
- 조인 결과가 항목별 CSV로 분리 생성된다.
- 대량 조회에서 상한 도달 시 자동 분할 재조회가 동작한다.

**완료 기준 (Definition of Done)**
- 다단계 결과를 DuckDB로 조인해 항목별 `save_as` CSV를 정상 생성한다.
- 결과 CSV를 엑셀에서 열었을 때 한글 깨짐이 없다.
- 실패 케이스(잘못된 SQL, 누락 컬럼, API 실패)에 대한 에러 메시지가 명확하다.

**리스크 및 대응**
- 스키마 불일치: 컬럼 매핑 규칙 및 누락 컬럼 처리 정책 명시
- 대용량 성능 저하: 중간 파일 압축/파티셔닝 옵션 검토

## Sprint 3 (2주): 운영 안정화 및 릴리즈 준비
**Sprint Goal**
- 운영 관점의 안정성, 로그 가시성, 품질 자동화 기반을 갖추고 MVP 릴리즈 준비를 마친다.

**포함 Story**
- Story 3-3(고도화)
- Story 5-3(고도화)
- Story 6-1 일부(설계/PoC 범위 정의)

### Task 목록
- [x] 예외 분류 체계 정의 (입력/AWS/SQL/파일 I/O) (P0)
- [x] 에러 코드 및 사용자 메시지 표준 테이블 작성 (P1)
- [x] 로그 레벨 옵션(`INFO`, `DEBUG`) 및 출력 포맷 통일 (P1)
- [x] 통합 테스트 시나리오 확장 (성공/실패/재시도) (P0)
- [x] 회귀 방지를 위한 CI 테스트 스크립트 정비 (P1)
- [x] 샘플 YAML 템플릿 2종(기본/고급) 제공 (P2)
- [x] 운영 가이드 문서(문제 해결, 재시도 튜닝, 비용 주의사항) 작성 (P1)
- [x] 로드맵 기능(S3/Athena, 시각화, Slack) 기술 설계 초안 작성 (P2)
- [x] MVP 릴리즈 체크리스트 작성 및 검수 (P0)

**완료 기준 (Definition of Done)**
- 핵심 실패 시나리오에서 복구 또는 명확한 종료가 보장된다.
- 문서(사용법/운영가이드/제한사항)가 배포 가능한 수준이다.
- MVP 릴리즈 체크리스트를 충족한다.

**리스크 및 대응**
- 테스트 데이터 편향: 실제 로그 패턴 기반 테스트셋 추가
- 운영 복잡도 증가: 기본 설정값 제공 및 고급 옵션 분리

## 우선순위 백로그 (Cross-Sprint)
- **P0**
  - CLI 입력 검증, 시간 변환, YAML 스키마 검증
  - CloudWatch 실행/폴링, DuckDB 조인, 최종 CSV 생성
  - 핵심 통합 테스트 및 릴리즈 체크리스트
- **P1**
  - 재시도 정책, 실행 요약 로그, 오류 표준화
  - 성능 스모크 테스트, 운영 가이드
- **P2**
  - 샘플 템플릿 확장, S3/Athena/시각화/Slack 설계

## 권장 운영 방식
- 스프린트 시작 시 Story별 담당자와 예상 공수(Story Point)를 확정한다.
- 데일리에서는 API 호출 안정성/쿼리 품질/성능 리스크를 우선 점검한다.
- 스프린트 종료 시 데모 기준은 "샘플 YAML로 실행 -> 최종 CSV 산출"의 End-to-End 성공으로 고정한다.
