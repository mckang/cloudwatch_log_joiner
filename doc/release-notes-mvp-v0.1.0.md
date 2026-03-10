# LogJoiner MVP v0.1.0 릴리즈 노트 (Draft)

## 릴리즈 개요
- 버전: `v0.1.0` (MVP)
- 목적: CloudWatch Logs Insights 조인 제약을 우회하는 다단계 추출/조인/CSV 산출 파이프라인 제공
- 범위: Sprint 1 ~ Sprint 3 반영 기능 기준

## 주요 기능
- CLI 기반 실행 흐름 제공
  - KST 입력 시간(`--start`, `--end`) 처리
  - `--skip-extract`로 조인 전용 실행 지원
  - `--dry-run`으로 설정 검증 전용 실행 지원
- YAML 기반 분석 파이프라인
  - `analysis_steps` 다단계 실행
  - `%s` 템플릿에 `extract_pattern` 치환
- DuckDB 기반 최종 조인
  - `final_join_sqls` 다중 SQL 실행
  - `__input__` 파이프라인 지원
  - `analysis_steps[].name`을 `FROM/JOIN` 소스로 참조 가능
- 산출물 생성
  - 스테이징 CSV/JSON 저장
  - 최종 CSV UTF-8-BOM 저장 (엑셀 호환)

## 안정성/운영성 개선
- 에러 분류 체계 도입
  - `LJ001` 입력 검증
  - `LJ101` AWS/CloudWatch 실행
  - `LJ201` SQL 실행
  - `LJ301` 파일 I/O
- 로그 표준화
  - `--log-level` (`INFO` / `DEBUG`) 지원
  - 공통 로그 포맷 통일
- 자동 분할 조회 지원
  - CloudWatch 조회 상한 도달 시 시간 구간 분할 재조회

## 품질/검증
- 테스트: `pytest` 27개 통과
- 정적 점검: `ruff`, `mypy` 통과 (`scripts/ci-test.sh` 기준)
- 통합 시나리오 검증:
  - 성공
  - 실패
  - 재시도
  - `--skip-extract` 경로

## 문서
- 운영 문서 추가
  - `doc/error-codes.md`
  - `doc/operations-guide.md`
  - `doc/roadmap-design-draft.md`
  - `doc/mvp-release-checklist.md`
- 샘플 설정 확장
  - `config.basic.sample.yaml`
  - `config.advanced.sample.yaml`

## 알려진 제한사항
- 실제 운영 릴리즈 전, 샘플 설정 기준 End-to-End 데모 최종 승인 필요
- 배포/롤백 담당자 지정 필요
- S3/Athena, 시각화, Slack 알림은 설계 초안 단계

## 롤백 가이드 (초안)
- 이전 태그/커밋으로 코드 롤백
- 기존 `config.yaml`과 `.env` 백업본으로 복원
- 재실행 전 `--dry-run`으로 설정 검증 수행
