# Train Data Collector

증권사 종목분석 리포트 PDF 수집기

## 목표

네이버 금융(https://finance.naver.com/research/company_list.naver)에서 증권사 종목분석 리포트 PDF를 스크래핑하여 훈련용 데이터를 수집합니다.

이 프로젝트는 1주차 프로젝트의 일환으로, 재무제표 인식 시스템(Table Recognition)을 위한 학습 데이터를 확보하는 것이 목적입니다.

## 주요 기능

- 네이버 금융 리서치 페이지에서 종목분석 리포트 목록 수집
- 각 리포트의 PDF 파일 다운로드
- 메타데이터 관리 (증권사, 종목, 날짜 등)

## 기술 스택

- Python 3.14
- 패키지 관리: uv

## 설치 및 실행

```bash
cd projects/train-data-collector
uv sync
uv run python main.py
```
