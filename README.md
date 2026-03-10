# LogJoiner

CloudWatch Logs Insights의 조인 제약을 우회하기 위한 다단계 분석 CLI입니다.

## 문서 위치
- PRD: `doc/prd.md`
- Epic/Story 백로그: `doc/epic-story-backlog.md`
- Sprint 계획: `doc/sprint-plan-with-tasks.md`
- 에러 코드 표준: `doc/error-codes.md`
- 운영 가이드: `doc/operations-guide.md`
- 로드맵 설계 초안: `doc/roadmap-design-draft.md`
- MVP 릴리즈 체크리스트: `doc/mvp-release-checklist.md`

## 개발환경
- Python 실행/의존성 관리는 `uv` 사용
- 가상환경 및 의존성 설치

```bash
uv sync
```

## AWS 인증 정보(`dotenv`)
- `.env.example`를 복사해 `.env` 파일을 생성한 뒤 값을 채웁니다.
- 기본적으로 `logjoiner`는 실행 시 `.env`를 자동 로드합니다.

```bash
cp .env.example .env
```

필수 키:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

권장 키:
- `AWS_DEFAULT_REGION` (예: `ap-northeast-2`)

## 실행 예시

### 1) 설정 검증만 수행 (dry-run)

```bash
uv run logjoiner \
  --start "2026-03-10 00:00:00" \
  --end "2026-03-10 01:00:00" \
  --config config.sample.yaml \
  --env-file .env \
  --dry-run
```

### 2) 전체 실행 (CloudWatch 추출 + DuckDB 조인 + 최종 CSV)

```bash
uv run logjoiner \
  --start "2026-03-10 00:00:00" \
  --end "2026-03-10 01:00:00" \
  --config config.sample.yaml \
  --env-file .env
```

전체 실행(`--skip-extract` 미사용) 시에는 시작 전에 `output/` 폴더 내부 파일을 모두 삭제하고 진행합니다.

### 3) 추출을 건너뛰고 조인/출력만 실행

```bash
uv run logjoiner \
  --config config.sample.yaml \
  --env-file .env \
  --skip-extract
```

`--skip-extract` 사용 시 `--start`, `--end`는 생략 가능합니다.

## 설정 파일
- 샘플: `config.sample.yaml`
- 템플릿:
  - 기본형: `config.basic.sample.yaml`
  - 고급형: `config.advanced.sample.yaml`
- 핵심 키
  - `log_group_name`
  - `extract_pattern`
  - `output_file`
  - `analysis_steps[].name`
  - `analysis_steps[].query`
  - `analysis_steps[].save_as`
  - `final_join_sqls`

`analysis_steps[].query`에서 `%s`를 사용하면 `extract_pattern`이 치환됩니다.
상대 경로로 지정한 `output_file`/`save_as`는 자동으로 `output/` 하위로 저장됩니다.
`final_join_sqls`는 `analysis_steps`와 유사하게 `name/query/save_as` 형태를 사용합니다.
`final_join_sqls.query`의 `FROM/JOIN` 소스는 파일 경로 대신 `analysis_steps[].name`을 사용할 수 있습니다.
예:

```yaml
analysis_steps:
  - name: "errors"
    ...
  - name: "all_logs"
    ...

final_join_sqls:
  - name: "a"
    query: |
      SELECT a.*
      FROM all_logs a
      JOIN errors e ON a.traceId = e.traceId
    save_as: "output/a.csv"
  - name: "b"
    query:
      - |
        SELECT ...
      - |
        SELECT * FROM __input__
    save_as: "output/b.csv"
```

`query`는 문자열(단일 SQL) 또는 문자열 리스트(다단계 SQL)를 지원하며,
리스트의 2번째 SQL부터 직전 결과를 `__input__`으로 참조할 수 있습니다.

## 실행 옵션
- `--retry-attempts`: CloudWatch 쿼리 재시도 횟수
- `--retry-backoff-seconds`: 재시도 백오프(초)
- `--query-limit`: CloudWatch 1회 조회 최대 건수 (기본 10000)
- `--min-split-seconds`: limit 도달 시 자동 분할 최소 구간(초)
- `--no-overwrite-stage`: step 산출물 파일 충돌 시 고유 파일명 사용
- `--skip-extract`: 기존 stage CSV를 재사용해 조인/출력 단계만 실행
- `--env-file`: dotenv 파일 경로 (기본값: `.env`)
- `--log-level`: 로그 레벨(`INFO`/`DEBUG`)

CloudWatch 조회 시 결과가 `--query-limit`에 도달하면 시간 구간을 자동으로 분할해 재조회하고 병합합니다.

## 테스트

```bash
uv run pytest
```

## CI 로컬 실행

```bash
./scripts/ci-test.sh
```
