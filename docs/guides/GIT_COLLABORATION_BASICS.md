# 세종 민원이음 — Git·GitHub 협업 입문 가이드

- 대상: Git을 처음 쓰는 저장소 소유자와 프론트엔드 협업자
- 기준일: 2026-07-22 KST
- 저장소: private `tskwak111/Sejong_AI`
- 프로젝트 기본 원칙: `main` 직접 push 금지, 작업 브랜치 → PR → 검사 → 병합

## 1. Git과 GitHub는 다르다

| 구분 | 뜻 | 비유 |
|---|---|---|
| Git | 내 컴퓨터에서 파일 변경 이력과 브랜치를 관리하는 프로그램 | 문서의 저장 시점과 평행 작업본을 관리하는 기록 장부 |
| GitHub | Git 저장소를 인터넷에서 공유하고 PR·검토·CI를 제공하는 서비스 | 팀 공동 문서함과 검토 게시판 |

인터넷이 없어도 `git status`, `git add`, `git commit`, 로컬 브랜치 생성은 가능하다. `git fetch`, `git pull`, `git push`, GitHub PR 확인은 원격 저장소와 통신하므로 인터넷과 권한이 필요하다.

## 2. 가장 중요한 전체 그림

```text
작업 폴더            스테이징 영역             로컬 저장소              GitHub 원격 저장소
(파일 수정)   --add--> (다음 기록 후보) --commit--> (커밋/브랜치) --push--> (origin의 브랜치)
                                                               |
                                                               +--> PR --> 검토/CI --> main 병합
```

각 단계는 자동으로 다음 단계까지 진행되지 않는다.

- 파일을 저장해도 커밋되지 않는다.
- `git add`를 해도 커밋되지 않는다.
- 커밋해도 GitHub에 올라가지 않는다.
- push해도 `main`에 병합되지 않는다.
- PR을 열어도 자동 병합되지 않는다.

## 3. 로컬에서 파일을 기록하는 용어

### Repository — 저장소

프로젝트 파일과 Git 이력을 함께 가진 작업 단위다. 로컬 저장소와 GitHub 원격 저장소는 서로 다른 복사본이다.

### Working tree — 작업 폴더

현재 화면에서 편집하는 실제 파일들이다. 저장했지만 아직 커밋하지 않은 변경이 있을 수 있다.

### Untracked / Modified / Staged

| 상태 | 뜻 | 예시 |
|---|---|---|
| Untracked (`??`) | 새 파일이지만 Git이 아직 기록 대상으로 선택하지 않음 | 새 컴포넌트 파일 생성 |
| Modified (` M`) | 기존 추적 파일을 수정했지만 stage하지 않음 | 기존 CSS 수정 |
| Staged (`M ` 또는 `A `) | 다음 커밋에 포함하기로 선택함 | `git add` 실행 후 |
| Clean | 커밋되지 않은 변경이 없음 | `git status --short` 출력 없음 |

### `git status`

현재 브랜치와 변경 파일 상태를 확인한다. 작업 전·커밋 전·push 전에 가장 자주 확인해야 한다.

```powershell
git status --short --branch
```

### `git diff`

아직 stage하지 않은 실제 줄 변경을 보여 준다.

```powershell
git diff
git diff --check
```

`git diff --cached`는 stage된, 즉 다음 커밋에 들어갈 변경을 보여 준다.

### `git add` — 스테이징

다음 커밋에 포함할 파일을 선택한다.

```powershell
git add apps/web/src/components/AnswerCard.tsx
git diff --cached
```

초보 단계에서는 무조건 `git add .`를 쓰기보다 파일명을 명시하는 편이 안전하다. `.env`, 임시 파일, 예상 밖 변경을 함께 넣는 실수를 줄일 수 있다.

### `git commit` — 로컬 이력 한 단위 만들기

stage된 변경을 이름·시간·설명과 함께 로컬 저장소에 영구적인 이력 단위로 기록한다.

```powershell
git commit -m "feat(web): add source card"
```

커밋은 GitHub 업로드가 아니다. commit 후에도 push 전이면 내 컴퓨터에만 있다.

좋은 커밋은 하나의 논리적 목적을 가진다. 예를 들어 출처 카드 구현과 전혀 관계없는 DB 수정은 같은 커밋에 넣지 않는다.

### SHA / Commit ID

`73ef5f9` 같은 문자열은 특정 커밋을 식별한다. 같은 커밋 내용과 부모 이력을 가리키는 고유 식별자다.

```powershell
git log --oneline -5
git rev-parse --short HEAD
```

### HEAD

현재 체크아웃한 브랜치의 현재 커밋을 가리키는 포인터다. 쉽게 말하면 “지금 내가 서 있는 이력 위치”다.

## 4. 브랜치와 병렬 작업

### Branch — 브랜치

같은 기준점에서 별도의 작업 흐름을 만드는 이름표다. 작업자가 각자 브랜치를 사용하면 미완성 변경을 `main`에 바로 넣지 않고 독립적으로 개발할 수 있다.

```text
main:       A---B---C
                    \
feature:             D---E
```

- `main`: 합의된 통합 기준선
- `codex/...`: 소유자 Codex 작업 브랜치
- `feat/web-...`: 프론트엔드 팀원 작업 브랜치

브랜치를 만들고 이동하는 예:

```powershell
git switch main
git switch -c feat/web-answer-card
```

`git checkout`도 비슷한 일을 하지만 여러 기능이 섞여 있다. 새 사용자는 목적이 분명한 `git switch`를 권장한다.

### Worktree — 여러 브랜치를 별도 폴더에서 동시에 열기

하나의 Git 저장소 이력을 공유하면서 브랜치마다 별도 작업 폴더를 두는 기능이다. 현재 로컬 Codex 작업도 worktree를 사용한다.

```text
기본 폴더                          → main
.worktrees/collab-...              → codex/COLLAB-... 브랜치
```

한 브랜치는 원칙적으로 한 worktree에서만 체크아웃할 수 있다. worktree 폴더를 일반 폴더처럼 임의 삭제하지 말고 Git 상태를 확인해야 한다.

## 5. 원격 저장소와 동기화

### Remote / `origin`

GitHub에 있는 원격 저장소 주소의 별칭이다. 보통 첫 원격을 `origin`이라고 부른다.

```powershell
git remote -v
```

### `git fetch` — 원격 소식만 받아오기

GitHub의 최신 브랜치와 커밋 정보를 내려받지만 내 작업 브랜치 파일은 바꾸지 않는다.

```powershell
git fetch origin
```

먼저 상황을 확인하고 싶을 때 가장 안전한 동기화 명령이다.

### `origin/main`

마지막 `fetch` 시점에 로컬 Git이 알고 있는 GitHub의 `main` 상태다. `main`은 로컬 브랜치이고 `origin/main`은 원격 추적 상태이므로 서로 다를 수 있다.

### Ahead / Behind

- `ahead 3`: 내 브랜치에 원격 기준보다 3개 커밋이 더 있음. 보통 push할 변경이 있다는 뜻이다.
- `behind 2`: 원격에 내 브랜치가 아직 받지 않은 커밋이 2개 있음.
- `ahead 3, behind 2`: 양쪽에서 각각 변경되어 이력이 갈라진 상태다.

### `git pull` — fetch 후 현재 브랜치에 반영

`pull`은 보통 `fetch + merge`다. 이 저장소에서는 예상치 않은 자동 merge를 막기 위해 다음처럼 fast-forward만 허용한다.

```powershell
git pull --ff-only origin main
```

현재 로컬 `main`이 단순히 뒤처졌을 때만 앞으로 이동하고, 이력이 갈라졌다면 멈춰서 사람에게 알린다.

### `git push` — 로컬 커밋을 GitHub에 올리기

```powershell
git push -u origin feat/web-answer-card
```

- `push`: 로컬 브랜치 커밋을 원격 브랜치로 전송한다.
- `-u`: 다음부터 `git push`만 입력해도 연결된 원격 브랜치를 알도록 upstream을 설정한다.
- push는 `main` 병합이 아니다. GitHub에 검토 가능한 브랜치가 생기는 단계다.

## 6. Pull Request와 CI

### Pull Request — PR

“이 작업 브랜치의 변경을 `main`에 합쳐 달라”는 검토 요청이다.

PR에서 확인해야 할 것:

1. base가 `main`인지
2. compare/head가 의도한 작업 브랜치인지
3. 변경 파일이 허용 범위 안인지
4. 비밀값·개인정보·임시 파일이 없는지
5. CI 검사가 모두 초록색인지
6. 충돌 또는 논리적 중복이 없는지

### Draft PR

아직 완성되지 않아 병합하면 안 되는 PR이다. 중간 작업 공유와 조기 검토에 사용한다. 이 프로젝트에서 Codex Cloud는 branch와 Draft PR까지만 만들고 사람이 병합한다.

### CI / Checks

GitHub가 push 또는 PR마다 자동 실행하는 검사다. 테스트·문서 정책·빌드 등을 검사한다.

초록색 검사는 “설정된 자동 검사를 통과했다”는 뜻이지, 모든 제품 요구와 논리적 의미가 완벽하다는 뜻은 아니다. PR #4의 중복 노트 ID처럼 다른 미게시 브랜치에만 존재하는 문제는 CI가 보지 못할 수 있다.

## 7. Merge — 병합

작업 브랜치의 변경을 대상 브랜치에 통합하는 작업이다. 이 프로젝트에서는 GitHub PR 화면에서 `Create a merge commit`을 기본값으로 사용한다.

### Merge commit

두 작업 흐름을 부모로 가진 새 커밋을 만들어 “이 PR을 여기서 병합했다”는 경계를 남긴다.

```text
main:       A---B-------M
                 \     /
feature:          C---D
```

장점은 PR의 작업 커밋과 병합 시점을 그대로 추적하기 쉽다는 것이다.

### Squash and merge

작업 브랜치의 여러 커밋을 하나로 압축해 `main`에 넣는다. main 이력은 단순해지지만 기존 커밋 SHA와 세부 이력이 바뀐다. 현재 프로젝트 기본값이 아니다.

### Rebase and merge

작업 커밋을 `main` 끝에 새로 재작성해 직선 이력을 만든다. 커밋 SHA가 달라지고 초보자가 충돌을 해석하기 어렵기 때문에 현재 프로젝트 기본값이 아니다.

### Fast-forward

대상 브랜치에 별도 변경이 없어 포인터만 앞으로 이동하는 병합이다.

## 8. 충돌은 두 종류가 있다

### 텍스트 Git 충돌

같은 파일의 같은 줄을 서로 다르게 수정해 Git이 어느 쪽을 선택할지 판단할 수 없는 상태다.

예:

```text
main:    버튼 문구를 "민원 시작"으로 변경
feature: 같은 버튼 문구를 "질문하기"로 변경
```

사람이 최종 문구를 결정하고 충돌 표시를 제거한 뒤 다시 검사·커밋해야 한다.

### 논리 충돌

Git은 파일을 합칠 수 있지만 결과의 의미가 잘못되는 상태다.

현재 PR #4 사례:

```text
원격 main에서 보이는 마지막 노트: 011
owner 미병합 브랜치:              012 생성
teammate 미병합 브랜치:           다른 012 생성
```

GitHub는 owner의 로컬 미게시 브랜치를 보지 않으므로 PR #4를 `CLEAN/MERGEABLE`로 표시한다. 하지만 두 브랜치를 모두 합치면 서로 다른 문서가 같은 고유번호를 사용한다. 따라서 PR #4는 owner 노트를 먼저 통합한 후 teammate 노트를 예약된 014로 바꾸고 병합해야 한다.

## 9. 되돌리기 관련 용어

### `git revert`

기존 커밋의 반대 변경을 새 커밋으로 만든다. 이미 GitHub에 공유되거나 `main`에 병합된 변경을 안전하게 취소할 때 사용한다. 이력이 남으므로 협업 환경의 기본 복구 방식이다.

### `git reset`

브랜치 포인터와 경우에 따라 작업 파일까지 과거로 이동한다. 특히 `git reset --hard`는 미커밋 변경을 없앨 수 있다. 공유 이력에서는 사용자 승인 없이 사용하지 않는다.

### Force push

원격 브랜치 이력을 강제로 덮어쓴다. 다른 사람의 커밋과 PR 검토 기준을 잃을 수 있으므로 이 프로젝트에서는 사용하지 않는다.

### `git stash`

커밋하기 애매한 임시 변경을 잠시 치워 두는 기능이다. 편리하지만 숨겨 둔 변경을 잊기 쉬우므로 이름을 붙이고 목록을 확인한다.

```powershell
git stash push -m "wip answer card"
git stash list
git stash pop
```

## 10. 이 프로젝트의 권장 작업 순서

### 새 작업 시작

```powershell
git status --short --branch
git switch main
git fetch origin
git pull --ff-only origin main
git switch -c feat/web-작업이름
```

작업 폴더가 깨끗하지 않으면 임의로 이동·삭제하지 말고 먼저 변경의 소유자를 확인한다.

### 작업 후 로컬 기록

```powershell
git status --short
git diff
git add <의도한 파일들>
git diff --cached
git commit -m "feat(web): 사용자에게 보이는 결과"
```

### GitHub에 공유하고 PR 생성

```powershell
git push -u origin feat/web-작업이름
```

이후 GitHub에서 `base: main`, `compare: feat/web-작업이름`으로 PR을 만든다.

### 병합 전

- 변경 파일과 diff를 직접 확인한다.
- 모든 필수 check가 초록색인지 확인한다.
- 예상 밖 파일, secret, 개인정보, 충돌이 있으면 병합하지 않는다.
- 프론트엔드 팀원은 허용된 frontend-only green PR만 자가 병합한다.
- Codex Cloud PR은 사용자가 검토·병합한다.

### 병합 후 동기화

```powershell
git switch main
git fetch origin
git pull --ff-only origin main
git status --short --branch
```

GitHub에서 merged된 원격 작업 브랜치는 삭제해도 되지만 `main`은 삭제하지 않는다.

## 11. 자주 겪는 상황

### “commit했는데 GitHub에 안 보여요”

commit은 로컬 기록일 뿐이다. 해당 브랜치를 push했는지 확인한다.

### “push했는데 main에 반영되지 않았어요”

push는 원격 작업 브랜치를 올린 것이다. PR을 만들고 검사·검토 후 merge해야 main에 들어간다.

### “push가 rejected 됐어요”

원격 브랜치에 내가 받지 않은 커밋이 있을 수 있다. force-push하지 말고 `git fetch origin`, `git status --short --branch`, `git log --oneline --graph --decorate --all -20` 결과를 확인한다.

### “main이 behind라고 나와요”

GitHub main이 로컬 main보다 앞서 있다. 작업 폴더가 깨끗한지 확인한 후 `git pull --ff-only origin main`으로 동기화한다.

### “잘못된 파일을 stage했어요”

아직 commit 전이면 파일 내용은 유지하면서 stage에서만 뺄 수 있다.

```powershell
git restore --staged <파일>
```

### “이미 병합한 변경이 잘못됐어요”

공유 이력을 강제로 지우지 말고 작은 revert PR을 만든다.

### “`.env`나 API 키가 보입니다”

commit·push를 즉시 멈춘다. 키를 지우는 것만으로 끝내지 말고 노출 가능성이 있으면 공급자에서 키를 폐기·재발급해야 한다. 실제 키 값을 채팅이나 이슈에 붙이지 않는다.

## 12. 최소 명령 치트시트

| 목적 | 명령 |
|---|---|
| 현재 상태 | `git status --short --branch` |
| 변경 내용 | `git diff` |
| stage된 변경 | `git diff --cached` |
| 최근 커밋 | `git log --oneline -10` |
| 원격 최신 정보 | `git fetch origin` |
| main 안전 동기화 | `git pull --ff-only origin main` |
| 새 브랜치 | `git switch -c <브랜치>` |
| 파일 stage | `git add <파일>` |
| 로컬 커밋 | `git commit -m "<메시지>"` |
| 작업 브랜치 push | `git push -u origin <브랜치>` |
| 잘못 stage한 파일 빼기 | `git restore --staged <파일>` |

기억할 핵심은 다음 한 줄이다.

> **수정 → add → commit → push → PR → 검사·검토 → merge → main 동기화**
