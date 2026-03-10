# [PRD] CloudWatch Logs 다단계 조인 분석 도구 (LogJoiner)

## 1. 제품 개요 (Product Overview)

본 도구는 CloudWatch Logs Insights의 단일 쿼리 제한(조인 불가, 쿼리 문자열 길이 제한)을 극복하기 위해 설계되었습니다. **Python, YAML, DuckDB**를 결합하여 로컬 환경에서 대용량 로그 데이터를 관계형 데이터베이스처럼 조인하고 분석할 수 있는 CLI 기반 솔루션입니다.

## 2. 목표 및 핵심 가치 (Goals & Strategic Value)

- **복잡한 트래킹**: 특정 패턴(Error, 특정 API 호출 등)에서 추출된 식별자(traceId, userId)를 기반으로 연관된 전후 맥락 로그를 한 번에 확보합니다.
- **쿼리 제한 우회**: CloudWatch의 10,000자 제한에 걸리지 않도록 ID 목록을 로컬에서 처리합니다.
- **성능 최적화**: DuckDB의 컬럼 지향 스토리지 엔진을 활용하여 수백만 건의 로그 조인을 메모리 효율적으로 수행합니다.
- **운영 효율화**: YAML 설정을 통해 코드 수정 없이 분석 시나리오(로그 그룹, 조인 키, 출력 필드)를 변경합니다.

## 3. 사용자 요구사항 (User Requirements)

- **KST 시간 입력**: 별도의 시간 계산 없이 한국 표준시(`yyyy-MM-dd HH:mm:ss`)로 조회 기간을 입력해야 합니다.
- **설정 파일 기반 운영**: 쿼리문과 로직을 YAML 파일에서 관리하여 재사용성을 높여야 합니다.
- **다단계 확장성**: 2단계 이상의 n단계 쿼리 파이프라인 구성을 지원해야 합니다.
- **데이터 정합성**: 조인된 결과는 반드시 시간순(`@timestamp`)으로 정렬되어 제공되어야 합니다.

## 4. 상세 기능 요구사항 (Functional Requirements)

### 4.1. 입력 파라미터 및 설정

- **CLI 인자**:
  - 기본 실행: `--start`, `--end` 필수 (형식: `yyyy-MM-dd HH:mm:ss`)
  - `--skip-extract` 실행: `--start`, `--end` 생략 가능
- **YAML 구성**:
- `log_group_name`: AWS CloudWatch 로그 그룹 경로.
- `analysis_steps`: 각 단계별 쿼리 정의 및 중간 결과 저장 파일명.
- `final_join_sqls`: `name`, `query`, `save_as`로 구성된 조인 결과 정의 목록.
  - `query`는 문자열 또는 문자열 리스트를 지원.
  - 리스트의 2번째 SQL부터 `__input__`으로 직전 결과 참조 가능.
  - `FROM/JOIN` 소스는 파일 경로 대신 `analysis_steps[].name` 참조 가능.

### 4.2. 데이터 처리 프로세스

1. **추출 (Extract)**: 입력된 KST 시간을 UTC 타임스탬프로 변환 후 Boto3를 통해 CloudWatch에 비동기 쿼리를 요청합니다.
   - 1회 조회 결과가 limit에 도달하면 시간 구간을 자동 분할해 재조회/병합합니다.
2. **임시 저장 (Stage)**: 각 단계별 쿼리 결과(JSON)를 로컬 CSV 파일로 즉시 덤프합니다.
3. **조인 및 변환 (Join & Transform)**: DuckDB 엔진을 구동하여 로컬 CSV 파일들을 테이블처럼 참조, 설정된 SQL을 실행합니다.
4. **최종 출력 (Export)**: 각 `final_join_sqls` 항목 결과를 Pandas를 통해 엑셀 호환 CSV(UTF-8-BOM)로 저장합니다.

### 4.3. 실행 정책

- **출력 폴더 초기화**: 전체 실행(`--skip-extract` 미사용) 시 시작 전에 `output/` 폴더 내부 파일을 삭제합니다.
- **조인 전용 실행**: `--skip-extract` 사용 시 기존 `output/` 스테이징 파일을 재사용합니다.

## 5. 기술 스택 (Technical Stack)

| 구분            | 기술        | 용도                                   |
| --------------- | ----------- | -------------------------------------- |
| **언어**        | Python 3.9+ | 전체 로직 제어 및 인터페이스           |
| **AWS 연동**    | Boto3       | CloudWatch Logs Insights API 호출      |
| **데이터 엔진** | **DuckDB**  | 로컬 파일 기반 고속 SQL 조인 및 필터링 |
| **데이터 처리** | Pandas      | 데이터프레임 변환 및 CSV 입출력        |
| **설정 관리**   | PyYAML      | 분석 시나리오 및 쿼리 템플릿 관리      |

## 6. 비기능 요구사항 (Non-Functional Requirements)

- **확장성**: `in` 연산자 대신 로컬 파일 조인을 사용하므로 수만 개의 ID 추적 시에도 성능 저하가 적어야 합니다.
- **안정성**: 네트워크 오류나 AWS API 제한 발생 시 재시도 또는 명확한 에러 메시지를 제공해야 합니다.
- **가독성**: YAML 내 멀티 라인 쿼리(`|`) 지원을 통해 복잡한 Insights 문법 가독성을 확보합니다.

## 7. 향후 로드맵 (Roadmap)

- **S3 연동**: 로컬 용량을 초과하는 대용량 로그 분석 시 S3 Select 또는 Athena 연동 지원.
- **시각화**: 분석 결과를 기반으로 에러 발생 분포도를 시각화한 HTML 리포트 생성.
- **Slack 알림**: 분석 완료 시 요약 보고서를 Slack 인컴잉 웹훅으로 전송.
