# Annotation Workspace

Label Studio를 활용한 테이블 탐지 결과 검수 환경.

## 워크플로우

```
fin-stat-table-detector     →     Label Studio     →     data-evaluator
   (테이블 탐지)                   (수동 검수)              (평가)
   predictions.json          annotations.json         Precision/Recall/F1
```

## 빠른 시작

### 1. Label Studio 실행

```bash
cd projects/annotation-workspace
./scripts/start.sh
```

브라우저에서 http://localhost:8081 접속

### 2. 초기 설정 (최초 1회)

1. 계정 생성 (로컬 전용, 아무 이메일 사용 가능)
2. 새 프로젝트 생성
3. Settings > Labeling Interface에서 `config/labeling-interface.xml` 내용 붙여넣기

### 3. 데이터 준비

```bash
# fin-stat-table-detector로 PDF 처리 (dataset-name 필수)
cd ../fin-stat-table-detector
uv run fin-stat-table-detector detect ../data/SK증권/ \
    -o ./sk_broker_labels.json \
    -i ./sk_broker/ \
    -d sk_broker \
    -p -w 4

# 생성된 이미지를 annotation-workspace로 이동
mv ./sk_broker/* ../annotation-workspace/data/local-files/
```

### 3.5. Cloud Storage 설정 (최초 1회)

1. Label Studio > Settings > Cloud Storage
2. **Add Source Storage** 클릭
3. Storage Type: **Local files**
4. Absolute local path: `/label-studio/data/local-files`
5. **Add Storage** 클릭
6. **Sync Storage** 클릭하여 파일 목록 동기화

### 4. 검수 작업

1. Label Studio에서 **Import** 클릭
2. `sk_broker_labels.json` 파일 업로드
3. 각 이미지의 bbox 검토:
   - 잘못된 bbox 삭제
   - 누락된 bbox 추가
   - 카테고리 수정
4. **Export** > JSON으로 annotations 내보내기

### 5. 평가

```python
from data_evaluator import DetectionEvaluator
from data_evaluator.parsers import parse_predictions, parse_annotations
import json

with open("predictions.json") as f:
    preds = parse_predictions(json.load(f))

with open("annotations.json") as f:  # Label Studio export
    gts = parse_annotations(json.load(f))

evaluator = DetectionEvaluator(iou_threshold=0.5)
result = evaluator.evaluate_dataset(preds, gts)

print(f"Precision: {result.precision:.2%}")
print(f"Recall: {result.recall:.2%}")
print(f"F1: {result.f1:.2%}")
```

## 디렉토리 구조

```
annotation-workspace/
├── config/
│   └── labeling-interface.xml   # Label Studio 라벨링 인터페이스
├── data/
│   ├── label-studio/            # Label Studio 내부 데이터 (자동 생성)
│   └── local-files/
│       └── images/              # 검수할 이미지 파일
├── scripts/
│   ├── start.sh                 # Label Studio 시작
│   └── stop.sh                  # Label Studio 중지
├── docker-compose.yml
└── README.md
```

## 레이블 종류

| 레이블 | 설명 | 색상 |
|--------|------|------|
| income_statement | 손익계산서 | 빨강 |
| balance_sheet | 재무상태표 | 청록 |
| cash_flow | 현금흐름표 | 파랑 |
| valuation | 투자지표 | 녹색 |
| performance | 실적 추이 | 노랑 |
| other_table | 기타 테이블 | 회색 |

## 종료

```bash
./scripts/stop.sh
```

## 요구사항

- Docker & Docker Compose
