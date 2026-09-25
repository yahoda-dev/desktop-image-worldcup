# Desktop Image World Cup

[![Windows build](https://github.com/yahoda-dev/desktop-image-worldcup/actions/workflows/build-windows.yml/badge.svg)](https://github.com/yahoda-dev/desktop-image-worldcup/actions/workflows/build-windows.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

내 컴퓨터에 저장된 이미지·동영상·오디오로 진행하는 Windows용 이상형 월드컵입니다. 미디어가 외부 서버로 전송되지 않으며, 선택한 폴더의 파일을 수정하거나 이동하지 않습니다.

## 프로젝트를 만든 이유

PC에 취향에 맞는 사진들을 모아두는 편이지만, 모으는 양에 비해 다시 꺼내 보는 빈도는 낮다고 느꼈습니다. 평소 잘 보지 않던 이미지들을 이상형 월드컵 방식으로 무작위 제공하면 모아둔 사진을 다시 감상하는 과정도 조금 더 재미있어지지 않을까 생각해, 직접 사용하려고 만들었습니다.

## 다운로드

일반 사용자는 [Releases](https://github.com/yahoda-dev/desktop-image-worldcup/releases)에서 최신 버전을 내려받을 수 있습니다.

| 파일 | 사용 환경 |
| --- | --- |
| `desktop-image-worldcup-x64.exe` | 64비트 Windows 10 이상, Windows 11 — 대부분의 사용자에게 권장 |
| `desktop-image-worldcup-x86.exe` | 32비트 Windows 10 |

설치 프로그램이 없는 포터블 앱이므로 Python이나 별도 런타임을 설치할 필요가 없습니다. 내려받은 `.exe` 파일을 원하는 폴더에 두고 실행하면 됩니다.

> 아직 Release가 게시되지 않았다면 배포 전 상태입니다. 저장소 관리자가 GitHub Actions 빌드를 확인한 뒤 실행 파일을 Release에 첨부해야 일반 사용자가 로그인 없이 받을 수 있습니다.

Windows 종류는 **설정 → 시스템 → 정보 → 시스템 종류**에서 확인할 수 있습니다. Windows 11은 64비트만 제공되므로 x64 파일을 사용하세요.

### Windows 보안 경고

현재 실행 파일에는 코드 서명이 적용되지 않았습니다. 처음 실행할 때 Windows SmartScreen의 "Windows의 PC 보호" 경고가 나타날 수 있습니다. 이 저장소의 공식 Releases에서 받은 파일인지 확인한 뒤 실행 여부를 결정하세요.

## 사용 방법

1. 프로그램을 실행합니다.
2. JPG, JPEG, PNG, WebP, GIF, MP4, WAV 중 월드컵에 사용할 확장자를 체크합니다.
3. **폴더 선택**을 눌러 월드컵에 사용할 미디어가 있는 폴더를 선택합니다.
4. 프로그램이 선택한 폴더와 모든 하위 폴더를 검사할 때까지 기다립니다.
5. 사용할 수 있는 미디어 수와 제외된 파일 수를 확인합니다.
6. `2강`, `4강`, `6강`처럼 시작할 라운드를 선택합니다.
7. **월드컵 시작**을 누릅니다.
8. JPG/JPEG/PNG와 정적 WebP는 화면을 클릭해 선택합니다. GIF·애니메이션 WebP·MP4·WAV는 화면을 클릭해 재생하고, 아래 파일명 버튼을 눌러 선택합니다.
9. 마지막 경기까지 선택하면 우승 미디어와 원본 파일 경로가 표시됩니다.
10. 같은 폴더로 다시 진행하거나 새 폴더를 선택할 수 있습니다.

## 제공 기능

- 시작 화면에서 사용할 확장자를 체크박스로 선택
- 선택 폴더 및 모든 하위 폴더의 미디어 자동 검색
- JPG/JPEG, PNG, WebP, GIF, MP4, WAV 지원
- GIF와 애니메이션 WebP의 앱 내 재생/일시정지
- MP4와 WAV 클릭 시 운영체제 기본 플레이어로 재생
- 손상되었거나 읽을 수 없는 미디어 자동 제외
- 이미지 비율을 유지한 미리보기와 EXIF 회전 정보 적용
- 미디어 검색 및 경기 미디어 로딩 중 진행 상태 표시
- 유효 미디어 수 이하의 모든 짝수 라운드 지원
- 선택한 라운드가 전체 미디어 수보다 작을 때 참가 미디어 무작위 추첨
- 2의 거듭제곱이 아닌 라운드의 무작위 부전승 처리
- 같은 라운드에서 동일한 파일의 중복 출전 방지
- 우승 미디어의 파일명과 전체 경로 표시
- 화면 우측에서 라운드별 대진, 선택 결과, 현재 경기 확인
- 같은 폴더 또는 새 폴더로 즉시 재시작
- Windows x86·x64 실행 파일 제공
- 실행 파일과 프로그램 창에 동일한 전용 아이콘 적용
- 한글과 라틴 문자를 폭넓게 지원하는 Noto Sans KR 글꼴 사용

## 대진 구성 방식

예를 들어 이미지가 10장이고 10강을 선택하면 2경기의 예선을 먼저 진행합니다. 나머지 6장은 무작위로 부전승을 받고, 예선 승자 2장과 함께 8강부터 일반 토너먼트를 진행합니다.

이미지가 20장인데 12강을 선택한 경우에는 20장 중 12장을 무작위로 뽑은 뒤 대진을 구성합니다. 승리한 이미지는 다음 라운드에서 다시 등장하지만, 같은 라운드 안에서는 한 번만 출전하며 자기 자신과 대결하지 않습니다.

## 개인정보와 원본 파일

- 모든 미디어 검색과 월드컵 진행은 사용자의 컴퓨터 안에서 처리됩니다.
- 미디어를 서버에 업로드하거나 네트워크로 전송하지 않습니다.
- 원본 파일을 복사, 이동, 이름 변경 또는 삭제하지 않습니다.
- 경기 선택 기록과 우승 결과를 별도 파일로 저장하지 않습니다.

## 지원 환경과 제한사항

- 지원 운영체제: Windows 10 이상
- 지원 아키텍처: x86 32비트, x86-64 64비트
- 지원 형식: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.mp4`, `.wav` — 확장자 대소문자 무관
- BMP, HEIC 등 다른 형식은 검색 대상에서 제외됩니다.
- 정적 WebP는 이미지로 표시되며 재생할 프레임이 없습니다.
- MP4·WAV 재생에는 해당 형식을 재생할 수 있도록 Windows에 연결된 기본 앱이 필요합니다.
- 경로가 다른 두 파일의 내용이 같더라도 서로 다른 참가자로 취급합니다.
- Pillow의 안전 한도를 초과하는 지나치게 큰 이미지와 손상된 미디어는 제외됩니다.
- 대회 진행 중 원본 파일이 삭제되거나 읽을 수 없게 되면 현재 대회를 중단하고 폴더를 다시 검사합니다.
- 코드 서명, 설치 프로그램, 자동 업데이트, 결과 저장 기능은 아직 제공하지 않습니다.

## 개발 환경 구성

개발에는 Python 3.12와 [uv](https://docs.astral.sh/uv/)를 사용합니다. 저장소를 복제한 뒤 다음 명령을 실행하세요.

```bash
git clone https://github.com/yahoda-dev/desktop-image-worldcup.git
cd desktop-image-worldcup
uv sync --locked
uv run python main.py
```

uv는 `.python-version`에 지정된 Python 3.12가 없으면 관리 영역에 설치하고, 프로젝트의 `.venv`와 `uv.lock`에 고정된 패키지를 준비합니다.

### 테스트

```bash
uv run pytest
uv run python main.py --smoke-test
```

테스트에는 미디어 재귀 검색과 형식 검증, 애니메이션 프레임 로딩, 가능한 라운드 계산, 무작위 참가자 추첨, 예선·부전승, 전체 토너먼트 진행이 포함됩니다.

## Windows 빌드와 릴리즈

[Build Windows executable](https://github.com/yahoda-dev/desktop-image-worldcup/actions/workflows/build-windows.yml) 워크플로는 push 또는 수동 실행 시 다음 작업을 수행합니다.

1. Python 3.12의 x86·x64 환경을 각각 준비합니다.
2. `uv.lock`에 고정된 의존성을 설치하고 테스트를 실행합니다.
3. PyInstaller로 아키텍처별 단일 GUI 실행 파일을 만듭니다.
4. 생성된 실행 파일을 Windows에서 스모크 테스트합니다.
5. 성공한 실행 파일을 14일 동안 Actions 아티팩트로 보관합니다.

일반 브랜치 push와 수동 실행은 여기까지 진행합니다. Actions 아티팩트는 배포 전 테스트 용도이며 다운로드하려면 GitHub 로그인이 필요합니다.

### 새 버전 배포

`v`로 시작하는 버전 태그를 push하면 x86·x64 빌드가 모두 성공한 뒤 [GitHub Releases](https://github.com/yahoda-dev/desktop-image-worldcup/releases)에 자동으로 배포됩니다.

```bash
git tag v0.1.0
git push origin v0.1.0
```

워크플로는 태그 이름으로 Release를 만들고 다음 파일을 첨부합니다.

- `desktop-image-worldcup-x86.exe`
- `desktop-image-worldcup-x64.exe`
- `SHA256SUMS.txt`

Release 설명은 이전 태그 이후의 변경 사항으로 자동 생성됩니다. 같은 태그의 워크플로를 다시 실행하면 기존 Release의 실행 파일과 체크섬을 새 빌드 결과로 교체합니다. 빌드나 테스트 중 하나라도 실패하면 Release는 생성·갱신되지 않습니다.

## 문제 제보

버그나 개선 의견은 [Issues](https://github.com/yahoda-dev/desktop-image-worldcup/issues)에 등록해 주세요. 문제가 발생한 Windows 버전과 x86/x64 실행 파일 중 어느 것을 사용했는지 함께 적어주면 확인에 도움이 됩니다.

## 라이선스

이 프로젝트는 [MIT License](LICENSE)로 배포됩니다.

앱에 포함된 `Noto Sans KR` 글꼴은 [SIL Open Font License 1.1](assets/fonts/OFL.txt)로 배포됩니다. 앱 아이콘은 이 프로젝트를 위해 생성된 자산이며 프로젝트의 MIT License를 따릅니다.
