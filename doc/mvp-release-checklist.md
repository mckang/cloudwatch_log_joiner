# MVP 릴리즈 체크리스트

## 기능

- [x] `analysis_steps` 추출 -> 스테이징 CSV/JSON 생성 검증
- [x] `final_join_sqls` 다중 실행 및 `__input__` 파이프라인 검증
- [x] `save_as`별 최종 CSV 생성 검증
- [x] `--skip-extract` 실행 경로 검증

## 안정성

- [x] 입력 검증 실패 시 `LJ001` 코드 노출 확인
- [x] AWS 실패/타임아웃 시 `LJ101` 코드 노출 확인
- [x] SQL 실패 시 `LJ201` 코드 노출 확인
- [x] 파일 I/O 실패 시 `LJ301` 코드 노출 확인

## 품질 자동화

- [x] `scripts/ci-test.sh` 로컬 실행 통과
- [x] `pytest` 성공/실패/재시도 시나리오 통과
- [x] 정적 점검(`ruff`, `mypy`) 통과

## 문서

- [x] `README.md` 실행법 최신화
- [x] `doc/error-codes.md` 최신화
- [x] `doc/operations-guide.md` 최신화
- [x] 샘플 YAML(기본/고급) 최신화

## 검증 메모 (2026-03-10)

- `./scripts/ci-test.sh` 통과 (`ruff`, `mypy`, `pytest`)
- `pytest` 통합 테스트에서 성공/실패/재시도 시나리오 확인
- `pytest` 추가 검증: `--skip-extract` 경로 및 `LJ001/LJ101/LJ201/LJ301` 코드 노출 확인 (총 27개 테스트 통과)

## 릴리즈 승인

- [x] 샘플 설정으로 End-to-End 데모 완료
- [x] 릴리즈 노트 작성
- [x] 배포 및 롤백 담당자 지정

### End-to-End 데모 실행 절차

- [x] `uv sync`
- [x] `uv run logjoiner --start "2026-03-10 00:00:00" --end "2026-03-10 01:00:00" --config config.sample.yaml --env-file .env --dry-run`
- [x] `uv run logjoiner --start "2026-03-10 00:00:00" --end "2026-03-10 01:00:00" --config config.sample.yaml --env-file .env`
- [x] `output/`에 `temp_*.csv`, `temp_*.json`, 최종 `*.csv` 생성 확인
- [x] 최종 CSV를 엑셀로 열어 한글 깨짐/컬럼 누락 여부 확인
- [x] 데모 결과(성공, 2.79s, 6개) 기록
