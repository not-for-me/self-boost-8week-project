# CLAUDE.md

## Project Context

This repository documents an 8-week intensive self-development program aimed at building practical experience in AI/ML data management and engineering.
The focus is on hands-on implementation of data-centric AI projects using modern tooling and best practices.

## Repository Structure

```
self-boost-8week-project/
├── projects/           # Individual project implementations
│   └── [project-name]/ # Each project as a separate module
│       ├── docs/       # Technical documentation (REQUIRED)
│       │   └── TECH_SPEC_*.md  # Feature/component specs
│       ├── tests/      # Test cases (REQUIRED)
│       │   ├── unit/           # Unit tests (isolated)
│       │   └── integration/    # Integration tests
│       └── src/        # Source code
├── til/                # Daily learning logs (Today I Learned)
│   └── tpl.md         # Template for daily entries
├── CLAUDE.md          # This file - context for AI assistants
└── README.md          # Human-readable project overview (Korean)
```

## Technology Stack
- **Language**: Python 3.14
- **Package Manager**: `uv` (fast Python package installer and resolver)
- **Project Organization**: Modular structure under `projects/` directory
- **Documentation**: Daily TIL entries tracking progress and learnings

## Development Principles

모든 프로젝트는 아래 세 가지 원칙을 반드시 준수해야 합니다.

### 1. Documentation First (문서화 우선)

모든 프로젝트 폴더에는 `docs/` 폴더가 **반드시** 존재해야 합니다.

- **TECH_SPEC.md**: 기능 구현을 위한 기술 스펙 문서
- 기술 스펙 문서는 **주요 세부 기능 또는 컴포넌트 단위**로 파일을 분리하여 관리
- 예시:
  ```
  docs/
  ├── TECH_SPEC_auth.md        # 인증 기능 스펙
  ├── TECH_SPEC_data_pipeline.md  # 데이터 파이프라인 스펙
  └── TECH_SPEC_api.md         # API 스펙
  ```

### 2. Human-Readable Test Cases (읽기 쉬운 테스트)

Claude가 작성한 코드를 검증하기 위해 **명확하고 사람이 읽기 쉬운 테스트 케이스**가 반드시 있어야 합니다.

- 테스트 이름은 기능을 명확히 설명할 것
- 테스트 구조는 Given-When-Then 또는 Arrange-Act-Assert 패턴 권장
- 각 테스트는 하나의 동작만 검증할 것

### 3. Test-Driven Completion (테스트 기반 완료)

코드 작성 후 **테스트 케이스를 반드시 실행**하여 **모든 테스트가 성공**했을 때만 작업이 완료된 것으로 간주합니다.

- 코드 작성 → 테스트 실행 → 성공 확인 → 작업 완료
- 테스트 실패 시: 코드 수정 → 재실행 → 성공할 때까지 반복
- **테스트를 실행하지 않은 코드는 미완성 상태**로 취급

### 4. SOLID Principles (코드 설계 원칙)

Python 코드 작성 시 SOLID 원칙을 준수하여 유지보수성과 확장성을 확보합니다.

#### 4.1 Single Responsibility Principle (단일 책임 원칙)

각 클래스/모듈은 **하나의 책임**만 가져야 합니다.

- **CLI 모듈**: 사용자 입력 처리와 출력만 담당
- **Processing 모듈**: 비즈니스 로직(데이터 처리)만 담당
- **Exporter 모듈**: 결과 내보내기만 담당

```
# Bad: CLI가 비즈니스 로직까지 처리
cli/detect.py → PDF 처리 + 이미지 변환 + 테이블 감지 + 결과 저장

# Good: 책임 분리
cli/detect.py        → 사용자 입력/출력
processing/batch.py  → 배치 처리 오케스트레이션
processing/pdf.py    → 단일 PDF 처리
exporters/base.py    → 결과 내보내기 인터페이스
```

#### 4.2 Open/Closed Principle (개방-폐쇄 원칙)

확장에는 열려 있고, 수정에는 닫혀 있어야 합니다.

- 새로운 기능 추가 시 **기존 코드 수정 없이** 확장 가능하도록 설계
- **추상 클래스(ABC)** 를 활용하여 인터페이스 정의

```python
# 추상 인터페이스 정의
class ResultExporter(ABC):
    @abstractmethod
    def export(self, result: ProcessingResult) -> None:
        pass

# 새 포맷 추가 시 기존 코드 수정 불필요
class LabelStudioExporter(ResultExporter): ...
class COCOExporter(ResultExporter): ...  # 새로 추가
```

#### 4.3 Dependency Inversion Principle (의존성 역전 원칙)

구체 클래스가 아닌 **추상화에 의존**해야 합니다.

```python
# Bad: 구체 클래스에 의존
class BatchProcessor:
    def __init__(self):
        self._exporter = LabelStudioExporter()  # 구체 클래스

# Good: 추상화에 의존
class BatchProcessor:
    def __init__(self, exporter: ResultExporter):  # 인터페이스
        self._exporter = exporter
```

### 5. Code Organization (코드 구조화)

#### 5.1 모듈 구조

```
src/package_name/
├── cli/                 # CLI 진입점 (입출력만)
│   ├── commands/        # 개별 명령어
│   └── display.py       # 출력 포맷팅
├── processing/          # 비즈니스 로직
│   ├── config.py        # 설정 및 결과 데이터클래스
│   ├── processor.py     # 단일 항목 처리
│   └── batch.py         # 배치 처리 (Sequential/Parallel)
├── exporters/           # 결과 내보내기
│   ├── base.py          # 추상 인터페이스
│   └── [format].py      # 구체 구현
├── detectors/           # 감지/분석 로직
│   └── factory.py       # 객체 생성 팩토리
├── models/              # 도메인 모델
└── utils/               # 유틸리티 함수
```

#### 5.2 테스트 구조

```
tests/
├── unit/                # 단위 테스트 (외부 의존성 없음)
│   ├── test_models.py
│   └── test_processor.py
├── integration/         # 통합 테스트 (외부 의존성 포함)
│   ├── test_cli.py
│   └── test_exporter.py
└── conftest.py          # pytest 설정 및 픽스처
```

- **Unit 테스트**: 모킹을 통해 외부 의존성 격리
- **Integration 테스트**: 실제 파일 시스템, 외부 라이브러리 사용
- pytest 마커로 구분: `@pytest.mark.unit`, `@pytest.mark.integration`

#### 5.3 데이터클래스 활용

설정과 결과는 **dataclass**로 명확히 정의합니다.

```python
@dataclass
class ProcessingConfig:
    """처리 설정."""
    images_dir: Path
    dpi: int = 150
    summary_only: bool = False

@dataclass
class ProcessingResult:
    """처리 결과."""
    pdf_path: Path
    pages: int = 0
    tables: list[Table] = field(default_factory=list)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None
```

---

## Working with This Repository

### For AI Assistants (Claude)

When assisting with this project:

1. **Understand the Goal**: Each task should contribute to building AI Data Manager competencies
2. **Follow the Structure**: Use `projects/` for implementations, `til/` for daily logs
3. **Use Modern Tools**: Leverage Python 3.14 features and `uv` for dependency management
4. **Maintain Quality**: Write production-quality code with proper error handling and documentation
5. **Track Progress**: Help update TIL entries with accomplishments and learnings
6. **Stay Focused**: Avoid over-engineering; build practical, demonstrable skills
7. **Document First**: 코드 작성 전 `docs/TECH_SPEC_*.md` 문서 작성 또는 확인
8. **Write Tests**: 모든 코드에 대해 읽기 쉬운 테스트 케이스 작성
9. **Verify with Tests**: 코드 작성 완료 후 반드시 테스트 실행하여 성공 확인

### Project Setup Pattern

Each new project should follow this initialization:

```bash
cd projects
mkdir project-name
cd project-name
uv init
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Required directories
mkdir -p docs tests src
```

After setup, create the initial tech spec:
```bash
touch docs/TECH_SPEC_overview.md  # Project overview spec
```

### Commit Convention

Use conventional commit messages:
- `feat: add table extraction module`
- `fix: resolve PDF parsing encoding issue`
- `docs: update TIL for day 15`
- `refactor: optimize image preprocessing pipeline`
