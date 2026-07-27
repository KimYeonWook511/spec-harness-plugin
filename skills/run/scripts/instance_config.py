from __future__ import annotations

"""저장소(인스턴스)가 하네스에 공급하는 설정을 읽는다.

하네스 엔진은 어떤 저장소의 문서 이름·구조도 알지 않는다. "무엇을 규칙으로 읽을지"는
저장소가 설정 파일로 직접 나열하고, 엔진은 그 목록만 따른다. 설정이 없으면 규칙 주입을
생략하고 코어 흐름만 돈다(오류가 아니다).

python 표준 라이브러리로 읽히도록 JSON을 쓴다(YAML은 외부 패키지가 필요해 실행 환경을
전제하게 된다).

설정 예:
    {
      "rule_docs": [
        { "path": "docs/some-rules.md", "section": "## 핵심 원칙" },
        "docs/another-rules.md"
      ],
      "reference_docs": ["docs/api-spec.md"]
    }

- rule_docs: 항상 주입하는 규칙 문서. 문자열이면 전문, 객체면 그 섹션만 주입한다.
  섹션 문자열은 저장소가 공급한다 — 엔진은 특정 헤딩을 전제하지 않는다.
- reference_docs: step 문서가 그 경로를 언급할 때만 주입하는 참고 문서.
"""

import json
from pathlib import Path
from typing import Optional

CONFIG_RELPATH = ".spec-harness/config.json"

# 실행 부산물(진행 마커·로그 증분 상태)이 쌓이는 곳. 설정과 같은 폴더 아래 두되 하위로 갈라
# 놓는다 — 설정은 사람이 쓰고 커밋하지만 이쪽은 엔진이 자동 생성하는 휘발 데이터라
# 저장소가 버전 관리에서 제외해야 한다(무시 규칙 한 줄로 끝나도록 하위 폴더로 모은다).
RUNTIME_RELPATH = ".spec-harness/run"

# 엔진 기본값 — 저장소 고유값은 하나도 담지 않는다. 비어 있으면 그 기능을 생략한다.
DEFAULTS: dict = {
    "rule_docs": [],
    "reference_docs": [],
    # 커밋 메시지·커밋 단위 규칙 문서. rule_docs와 따로 두는 이유: rule_docs는 step마다 구현 컨텍스트로
    # 주입되는데 커밋 규칙은 커밋할 때만 필요하고, 커밋 담당 agent는 문서를 탐색할 도구가 없어 경로를
    # 명시로 받아야 한다.
    "commit_rule_docs": [],
    # spec 문서 템플릿을 저장소가 자기 것으로 쓰고 싶을 때만 지정한다(저장소 루트 기준 상대경로).
    # 없으면 플러그인이 싣고 있는 기본 템플릿을 쓴다 — 템플릿이 없는 저장소에서도 시작할 수 있도록.
    "template_dir": None,
    # spec 작업 공간이 사는 곳(저장소 루트 기준). 하네스가 spec 폴더를 만들고 찾는 기준점이다.
    "spec_root": "docs/specs",
    # 이 저장소가 켠 방법론 이름 목록(예: ["ddd"]). 비어 있으면 방법론 무관 코어만 돈다.
    # 방법론은 검사·요구 산출물·전용 agent를 더하며, 코어 게이트를 끄지는 못한다.
    "methodologies": [],
    # 작업 공간을 어떻게 만드는지. 저장소마다 브랜치 모델이 달라 값으로 받는다.
    "workspace": {
        # "worktree": 별도 디렉터리에 워크트리를 만들어 그 안에서 작업(메인 체크아웃을 건드리지 않음).
        # "branch": 현재 체크아웃에서 브랜치만 새로 만들어 작업.
        "mode": "worktree",
        # 분기 기준 브랜치. null이면 저장소의 기본 브랜치를 쓴다(값을 추측하지 않는다).
        "base_ref": None,
        # 이름 형식. <type>은 작업 종류, <name>은 spec 이름으로 치환된다.
        "branch_pattern": "<type>/<name>",
        "worktree_pattern": "worktrees/<type>-<name>",
        # 허용하는 작업 종류. 비어 있으면 하네스가 값을 정하지 않고 사용자에게 확인한다.
        "types": [],
    },
}

# 플러그인이 싣고 있는 기본 템플릿 위치(이 스크립트 기준).
BUILTIN_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "spec"

# 방법론 선언이 사는 곳. 이 스크립트는 skills/run/scripts/ 아래이므로 플러그인 루트는 세 단계 위다.
PLUGIN_DIR = Path(__file__).resolve().parents[3]
METHODOLOGY_DIR = PLUGIN_DIR / "methodologies"


def resolve_template_dir(root_path: Path, config: dict) -> tuple[Path, list[str]]:
    """쓸 템플릿 폴더를 결정한다. 저장소 지정이 있으면 그것, 없거나 없는 경로면 내장 템플릿."""
    notes: list[str] = []
    rel = config.get("template_dir")
    if isinstance(rel, str) and rel:
        candidate = root_path / rel
        if candidate.is_dir():
            return candidate, notes
        notes.append(f"지정한 template_dir를 찾지 못해 내장 템플릿을 쓴다: {rel}")
    return BUILTIN_TEMPLATE_DIR, notes


def config_path(root_path: Path) -> Path:
    return root_path / CONFIG_RELPATH


def load_config(root_path: Path) -> dict:
    """설정을 읽어 기본값과 병합한다. 없으면 기본값, 깨졌으면 기본값 + 경고를 남긴다.

    반환 dict의 `_notes`는 설정을 읽는 중 생긴 알림 목록이다. 조용히 삼키면 규칙이
    사라진 것을 아무도 모르게 되므로, 호출자가 컨텍스트에 드러내도록 함께 넘긴다.
    """
    config = dict(DEFAULTS)
    config["_notes"] = []

    path = config_path(root_path)
    if not path.exists():
        return config

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        config["_notes"].append(f"설정 파일을 읽지 못해 규칙 주입을 생략한다 ({CONFIG_RELPATH}): {exc}")
        return config

    if not isinstance(loaded, dict):
        config["_notes"].append(f"설정 파일 최상위가 객체가 아니라 무시한다 ({CONFIG_RELPATH}).")
        return config

    for key in DEFAULTS:
        if key in loaded:
            config[key] = loaded[key]
    return config


def normalize_rule_docs(config: dict) -> tuple[list[tuple[str, Optional[str]]], list[str]]:
    """rule_docs를 (경로, 섹션|None) 목록으로 정규화한다. 형식이 잘못된 항목은 알림으로 남긴다."""
    entries: list[tuple[str, Optional[str]]] = []
    notes: list[str] = []

    raw = config.get("rule_docs") or []
    if not isinstance(raw, list):
        notes.append("rule_docs가 목록이 아니라 무시한다.")
        return entries, notes

    for item in raw:
        if isinstance(item, str):
            entries.append((item, None))
            continue
        if isinstance(item, dict):
            path = item.get("path")
            if isinstance(path, str) and path:
                section = item.get("section")
                entries.append((path, section if isinstance(section, str) and section else None))
                continue
        notes.append(f"rule_docs 항목 형식이 잘못돼 건너뛴다: {item!r}")

    return entries, notes


def reference_doc_paths(config: dict) -> tuple[list[str], list[str]]:
    """reference_docs를 경로 목록으로 반환한다."""
    paths: list[str] = []
    notes: list[str] = []

    raw = config.get("reference_docs") or []
    if not isinstance(raw, list):
        notes.append("reference_docs가 목록이 아니라 무시한다.")
        return paths, notes

    for item in raw:
        if isinstance(item, str) and item:
            paths.append(item)
        else:
            notes.append(f"reference_docs 항목 형식이 잘못돼 건너뛴다: {item!r}")

    return paths, notes
