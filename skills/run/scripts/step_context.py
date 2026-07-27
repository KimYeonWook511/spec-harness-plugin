from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import instance_config

SPEC_DOC_FILES = [
    "spec.md",
    "architecture.md",
    "adr.md",
    "api-spec.md",
    "db-schema.md",
]


def extract_section(text: str, heading: str) -> Optional[str]:
    """문서에서 지정한 헤딩의 섹션 본문만 추출한다. 헤딩이 없으면 None.

    끝나는 지점은 "같은 깊이 이상"의 다음 헤딩이다 — `## X`를 지정하면 다음 `##`이나 `#`에서,
    `### X`를 지정하면 다음 `###`·`##`·`#`에서 끊는다. 특정 깊이를 전제하지 않으려는 것이다.
    """
    heading = heading.strip()
    level = len(heading) - len(heading.lstrip("#"))
    if level == 0:
        return None

    # 헤딩은 줄 시작에서만 인정한다(본문에 같은 문구가 인용된 경우를 피한다).
    start = re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not start:
        return None

    after = text[start.end():]
    next_heading = re.search(rf"^#{{1,{level}}} ", after, re.MULTILINE)
    body = after[: next_heading.start()] if next_heading else after
    body = body.strip()
    # 섹션 끝의 구분선(---)은 문서 가독성용이라 문서에는 두되, 주입 시에는 토큰 절약을 위해 제거한다.
    if body.endswith("---"):
        body = body[:-3].strip()
    return body or None


def load_rule_docs(root_path: Path, config: dict) -> tuple[list[tuple[str, str]], list[str]]:
    """설정이 지정한 규칙 문서를 (상대경로, 본문) 목록으로 반환한다.

    엔진은 어떤 문서가 규칙인지 알지 않는다 — 저장소가 설정에 나열한 것만 읽는다.
    섹션을 지정하지 않으면 전문을, 지정했으면 그 섹션만 넣는다. 지정한 섹션을 못 찾으면
    전문을 넣고 그 사실을 알림으로 남긴다 — 지켜야 할 규칙이 조용히 빠지는 것이 토큰이
    늘어나는 것보다 나쁘기 때문이다.
    """
    entries, notes = instance_config.normalize_rule_docs(config)
    docs: list[tuple[str, str]] = []

    for rel, section in entries:
        path = root_path / rel
        if not path.exists():
            notes.append(f"규칙 문서를 찾지 못해 건너뛴다: {rel}")
            continue

        text = path.read_text(encoding="utf-8")
        if section is None:
            body = text.strip()
        else:
            extracted = extract_section(text, section)
            if extracted is None:
                notes.append(f"'{section}' 섹션을 찾지 못해 전문을 주입한다: {rel}")
                body = text.strip()
            else:
                body = extracted

        if body:
            docs.append((rel, body))

    return docs, notes


def resolve_doc(root_path: Path, *candidates: str) -> Optional[Path]:
    """후보 경로 중 실제로 존재하는 첫 문서를 반환한다."""
    for candidate in candidates:
        path = root_path / candidate
        if path.exists():
            return path
    return None


def list_reference_docs(root_path: Path, config: dict) -> tuple[list[Path], list[str]]:
    """설정이 지정한 참고 문서 중 실제로 존재하는 것을 반환한다.

    규칙 문서와 달리 이쪽은 step 문서가 그 경로를 언급할 때만 주입된다(호출자가 걸러낸다).
    프로젝트 문서의 특정 섹션 서식을 훑어 목록을 추측하지 않는다 — 서식이 조금 달라지면
    조용히 빈 목록이 되어 아무 문서도 주입되지 않기 때문이다.
    """
    paths, notes = instance_config.reference_doc_paths(config)
    docs: list[Path] = []
    for rel in paths:
        path = root_path / rel
        if path.exists():
            docs.append(path)
        else:
            notes.append(f"참고 문서를 찾지 못해 건너뛴다: {rel}")
    return docs, notes


def list_spec_docs(spec_dir: Path) -> list[Path]:
    """spec 폴더에서 기본 문서 5개 중 존재하는 문서만 순서대로 반환한다."""
    docs: list[Path] = []
    for filename in SPEC_DOC_FILES:
        path = spec_dir / filename
        if path.exists():
            docs.append(path)
    return docs


def load_step_documents(
    root_path: Path, spec_dir: Path, step_text: str, config: Optional[dict] = None
) -> str:
    """현재 step에 필요한 최소 문서만 developer 컨텍스트로 주입한다.

    config를 주지 않으면 저장소에서 읽는다(테스트가 설정을 직접 넘길 수 있도록 인자로 뺐다).
    """
    if config is None:
        config = instance_config.load_config(root_path)

    sections: list[str] = []
    notes: list[str] = list(config.get("_notes") or [])

    claude_md = resolve_doc(root_path, "CLAUDE.md")
    if claude_md:
        sections.append(f"## 프로젝트 규칙 (CLAUDE.md)\n\n{claude_md.read_text(encoding='utf-8')}")

    for doc in list_spec_docs(spec_dir):
        rel_path = doc.relative_to(root_path).as_posix()
        sections.append(f"## spec 문서 ({rel_path})\n\n{doc.read_text(encoding='utf-8')}")

    # 저장소가 규칙으로 지정한 문서를 항상 주입한다.
    # agent가 그 저장소의 규칙을 안 보고 자기 판단으로 코딩하는 것을 막는다.
    rule_docs, rule_notes = load_rule_docs(root_path, config)
    notes.extend(rule_notes)
    if rule_docs:
        block = "## 규칙 문서 (반드시 준수)\n\n"
        block += (
            "아래는 이 저장소에서 항상 지켜야 하는 규칙이다. 자기 판단보다 우선한다. "
            "세부 사례가 더 필요하면 step이 가리키는 문서를 참조한다.\n\n"
        )
        for rel, body in rule_docs:
            block += f"### {rel}\n\n{body}\n\n"
        sections.append(block.rstrip())

    reference_docs, ref_notes = list_reference_docs(root_path, config)
    notes.extend(ref_notes)
    for doc in reference_docs:
        rel_path = doc.relative_to(root_path).as_posix()
        if rel_path in step_text:
            sections.append(f"## 관련 문서 ({rel_path})\n\n{doc.read_text(encoding='utf-8')}")

    # 설정·문서 문제는 조용히 넘기지 않고 컨텍스트에 드러낸다(로그에도 함께 남는다).
    if notes:
        block = "## 하네스 설정 알림\n\n"
        block += "\n".join(f"- {note}" for note in notes)
        sections.append(block)

    return "\n\n---\n\n".join(sections) if sections else ""


def build_previous_step_context(index: dict) -> str:
    """이전 완료 step의 summary를 다음 step용 컨텍스트로 구성한다."""
    lines = [
        f"- Step {step['step']} ({step['name']}): {step['summary']}"
        for step in index.get("steps", [])
        if step.get("status") == "completed" and step.get("summary")
    ]
    if not lines:
        return ""
    return "## 이전 Step 산출물\n\n" + "\n".join(lines) + "\n\n"
