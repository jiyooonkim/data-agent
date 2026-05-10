# Notion Document QA Test Questions

This file contains sample questions for testing the Notion -> pgvector -> Ollama document QA flow.

Run format:

```bash
./.venv/bin/python main.py ask-doc --question "질문"
```

---

## 1. CI / CD Basic Questions

```bash
./.venv/bin/python main.py ask-doc --question "이 문서에서 CI는 어떤 역할을 하나?"
./.venv/bin/python main.py ask-doc --question "이 문서에서 CD는 어떤 의미로 설명되어 있나?"
./.venv/bin/python main.py ask-doc --question "포트폴리오 프로젝트에서 CI를 왜 넣었는지 설명해줘"
./.venv/bin/python main.py ask-doc --question "이 프로젝트에서 자동 배포는 포함되어 있나?"
```

---

## 2. Lint / Test Questions

```bash
./.venv/bin/python main.py ask-doc --question "이 문서에서 lint는 어떤 목적이야?"
./.venv/bin/python main.py ask-doc --question "이 문서에서 test는 어떤 목적이야?"
./.venv/bin/python main.py ask-doc --question "lint와 test의 차이를 설명해줘"
./.venv/bin/python main.py ask-doc --question "왜 Ruff를 쓰는지 알려줘"
./.venv/bin/python main.py ask-doc --question "Pytest는 이 프로젝트에서 어떤 역할이야?"
```

---

## 3. GitHub Actions Questions

```bash
./.venv/bin/python main.py ask-doc --question "이 프로젝트에서 GitHub Actions는 무엇을 하나?"
./.venv/bin/python main.py ask-doc --question "push 하면 어떤 검사가 실행되나?"
./.venv/bin/python main.py ask-doc --question "PR에서도 같은 CI가 도는지 알려줘"
./.venv/bin/python main.py ask-doc --question "현재 CI 파이프라인 흐름을 요약해줘"
```

---

## 4. Portfolio / Design Intent Questions

```bash
./.venv/bin/python main.py ask-doc --question "이 프로젝트에서 CI 범위를 왜 가볍게 유지했는지 설명해줘"
./.venv/bin/python main.py ask-doc --question "이 문서 기준으로 왜 배포 자동화는 아직 안 넣었는지 알려줘"
./.venv/bin/python main.py ask-doc --question "포트폴리오 프로젝트 기준으로 이 CI 구조의 의도가 뭐야?"
./.venv/bin/python main.py ask-doc --question "이 문서에서 품질 검증 전략을 설명해줘"
```

---

## 5. Validation / Edge Questions

```bash
./.venv/bin/python main.py ask-doc --question "이 문서에서 사용하지 않는 도구는 무엇이라고 했어?"
./.venv/bin/python main.py ask-doc --question "flake8을 왜 제거했는지 설명해줘"
./.venv/bin/python main.py ask-doc --question "Ruff와 Pytest를 각각 무엇으로 설명하고 있나?"
./.venv/bin/python main.py ask-doc --question "현재 CI에 포함되지 않은 항목들을 알려줘"
```

---

## 6. Short Korean Natural Questions

```bash
./.venv/bin/python main.py ask-doc --question "CI가 뭐야?"
./.venv/bin/python main.py ask-doc --question "이 프로젝트 테스트는 어떻게 해?"
./.venv/bin/python main.py ask-doc --question "자동 배포도 해?"
./.venv/bin/python main.py ask-doc --question "Ruff 왜 써?"
```

---

## 7. Short English Questions

```bash
./.venv/bin/python main.py ask-doc --question "What is the role of CI in this project?"
./.venv/bin/python main.py ask-doc --question "Why does this project use Ruff?"
./.venv/bin/python main.py ask-doc --question "What is Pytest used for in this project?"
./.venv/bin/python main.py ask-doc --question "Does this project include CD?"
```

---

## Quick Smoke Test Set

If you want a short validation set, start with these four:

```bash
./.venv/bin/python main.py ask-doc --question "이 문서에서 CI는 어떤 역할을 하나?"
./.venv/bin/python main.py ask-doc --question "lint와 test의 차이를 설명해줘"
./.venv/bin/python main.py ask-doc --question "포트폴리오 프로젝트에서 CI를 왜 넣었는지 설명해줘"
./.venv/bin/python main.py ask-doc --question "Does this project include CD?"
```
