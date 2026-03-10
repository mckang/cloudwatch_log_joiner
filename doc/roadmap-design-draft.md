# 로드맵 기능 설계 초안

## 범위
- S3/Athena 적재
- 시각화 대시보드
- Slack 알림

## 1) S3/Athena 연동
- 목표: `analysis_steps` 또는 `final_join_sqls` 결과를 S3 Parquet로 적재하고 Athena에서 조회 가능하게 한다.
- 설계 초안:
  - 출력 어댑터 계층 추가 (`csv`, `parquet-s3`)
  - 실행 단위 메타데이터(`run_id`, `executed_at`, `config_hash`) 저장
  - 파티션 키: `dt`, `log_group_name`
- PoC 기준:
  - 1개 결과셋을 S3에 적재
  - Athena 테이블 생성 및 기본 쿼리 성공

## 2) 시각화
- 목표: 반복 분석 결과를 빠르게 파악할 수 있는 시각화 제공
- 설계 초안:
  - 우선순위 1: CSV 기반 로컬 대시보드(정적 HTML)
  - 우선순위 2: Athena 결과를 BI 도구와 연결
- 초기 지표:
  - 오류 코드별 빈도
  - 시간대별 오류 추이
  - traceId 기준 상위 영향 이벤트

## 3) Slack 알림
- 목표: 실행 실패/성공 요약을 운영 채널에 자동 전송
- 설계 초안:
  - 실행 종료 후 webhook POST
  - 메시지 필드: 상태, 소요시간, 결과 파일 수, 실패 스텝, 대표 에러 코드
  - 실패 시 `LJxxx` 코드 중심으로 요약
- 보안:
  - webhook URL은 `.env`로만 주입
  - 로그에 민감정보 마스킹

## 단계별 추진
- Phase 1: 설계 확정 + 출력 어댑터 인터페이스 정의
- Phase 2: S3/Athena PoC
- Phase 3: Slack 알림 + 운영 텔레메트리
- Phase 4: 시각화 연계 및 운영 대시보드 고도화
