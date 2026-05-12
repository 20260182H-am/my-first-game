# Week 11 실습

## 오늘 한 것
- PyInstaller 설치 및 빌드 = 완료
- resource_path() 함수 추가 = 완료
- --add-data 옵션으로 에셋 포함 = 완료
- .exe 실행 확인 = 완료

## resource_path() 를 써야 하는 이유
resource_path를 써야 하는 이유는 Python으로 실행할 때와exe로 실행할 때 파일 위치가 달라지기 때문입니다.
보통의 pygame 게임은 에셋을 상대경로로 하여 찾아낼 수 있습니다. 하지만 PyInstaller의 --onefile로 exe를 만들면, 실행 위치가 원래 프로젝트 폴더가 아니기에 에셋을 찾지 못하게 됩니다.
이를 해결하기 위해 sys._MEIPASS를 사용해 'PyInstaller가 실제로 압축을 풀어놓은 위치'를 기준으로 파일을 찾게 햐여 경로 상의 오류가 생기지 않게 합니다.

## 빌드 명령어
Thonny - Open system shell 클릭

### 명령어
pyinstaller --onefile --windowed --add-data "sprites;sprites" --add-data "sounds;sounds" --add-data "fonts;fonts" game.py

--onefile : 압축
--windowed : 콘솔창 숨기기
--add-data : 리소스 포함하기
game.py : 빌드 대상이 되는 파일

## AI 활용 내역

### 1. Python 실행 환경과 exe 실행 환경이 달라서 에셋을 받아오지 못한다는데 이해가 잘 안되서 쉽게 설명해줘.

AI 답변: Python으로 실행할 때는 game.py 옆에서 바로 파일을 찾지만, exe는 실행 시 내부 파일들을 임시 폴더에 꺼내서 실행하기 때문에 원래 위치에 있는 sprites, sounds 폴더를 찾지 못할 수 있다.

적용 결과: exe 실행 시 파일 위치 자체가 달라진다는 부분을 이해할 수 있었고, `_MEIPASS`를 사용하여 에셋을 불러와야 한다는 것에 대한 이유를 이해할 수 있었다.

### 2. 에셋 오류가 있는 build, dist, spec 파일 지워도 되는거야? 기존 파일에 문제 생겨?

AI 답변: build는 임시 빌드 파일, dist는 결과물 폴더, spec은 빌드 설정 파일이라 삭제해도 원본 game.py와 sprites 폴더에는 영향을 주지 않는다고 설명.

적용 결과: build, dist, spec 파일의 역할을 이해하고 기존 프로젝트에는 문제가 없다는 것을 확인한 뒤 삭제 후 재빌드를 진행하였다.

### 3. GitHub Desktop에 계정 연동을 했는데도 이전 사용자 VSCode가 계속 열려

AI 답변: GitHub 계정 문제가 아니라 PC에 남아 있던 이전 사용자의 local repository가 연결되어 있어서 이전 프로젝트가 계속 열리는 것이라고 설명.

적용 결과: 이전 repository를 제거하고 현재 pygame 프로젝트를 다시 연결하여 정상적으로 내 VSCode 프로젝트를 열 수 있었다.

## AI 답변에서 도움이 된 것

PyInstaller를 설치하고 활용해 .exe 실행을 확인하는 과정은 AI를 활용하니 쉽게 할 수 있었으나, GitHub Desktop 연동 문제는 내가 실수하면 다른 사람의 작업물에 문제가 생길 수 있다는 부담감에 쉽게 손쓰기 어려웠다. 그러나 AI가 질의하는 과정에서 이전 작업물을 건들지 않으면서 나의 계정을 GitHub Desktop에 연동하는 방법을 알려주어 수월하게 문제를 해결할 수 있었다.
