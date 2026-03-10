from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logjoiner",
        description="CloudWatch Logs 다단계 조인 분석 CLI",
    )
    parser.add_argument(
        "--start",
        help="조회 시작 시각 (KST, yyyy-MM-dd HH:mm:ss, --skip-extract 시 선택)",
    )
    parser.add_argument(
        "--end",
        help="조회 종료 시각 (KST, yyyy-MM-dd HH:mm:ss, --skip-extract 시 선택)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="분석 설정 파일 경로 (기본값: config.yaml)",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="AWS 자격증명/리전 환경변수 파일 경로 (기본값: .env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 쿼리 호출 없이 설정/시간 변환만 검증",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=1.0,
        help="CloudWatch 쿼리 상태 폴링 간격(초, 기본값: 1.0)",
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=int,
        default=120,
        help="CloudWatch 쿼리 대기 타임아웃(초, 기본값: 120)",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=3,
        help="CloudWatch 쿼리 재시도 횟수(기본값: 3)",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=1.0,
        help="CloudWatch 쿼리 재시도 백오프(초, 기본값: 1.0)",
    )
    parser.add_argument(
        "--query-limit",
        type=int,
        default=10000,
        help="CloudWatch 쿼리 1회 조회 최대 건수(기본값: 10000)",
    )
    parser.add_argument(
        "--min-split-seconds",
        type=int,
        default=1,
        help="전체 수집용 자동 분할 최소 구간(초, 기본값: 1)",
    )
    parser.add_argument(
        "--no-overwrite-stage",
        action="store_true",
        help="step 산출물 파일 충돌 시 덮어쓰지 않고 고유 파일명으로 저장",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="CloudWatch 추출을 건너뛰고 기존 스테이징 CSV로 조인 단계만 수행",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("INFO", "DEBUG"),
        help="로그 레벨 (INFO 또는 DEBUG, 기본값: INFO)",
    )
    return parser
