import pygame

pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Number Animation")
clock = pygame.time.Clock()

# 스프라이트 시트 불러오기
sheet = pygame.image.load("./assets/images/spritesheet.png").convert_alpha()

# ───────── 설정 ─────────
FRAME_W = 40   # 숫자 하나 가로 크기
FRAME_H = 40   # 숫자 하나 세로 크기

start_x = 300  # 숫자 시작 x좌표 (이미지 기준)
start_y = 20   # 숫자 7 위치 기준 y좌표

# ───────── 숫자 프레임 추출 (1~9) ─────────
number_frames = []

# 이미지에서 위에서 아래로 7→0 순서라서 뒤집어서 1~9 만들기
raw_frames = []
for i in range(8):  # 7~0까지 8개
    rect = pygame.Rect(start_x, start_y + i * FRAME_H, FRAME_W, FRAME_H)
    raw_frames.append(sheet.subsurface(rect))

# 순서 뒤집고 1~7
raw_frames.reverse()

# 1~7 + 8,9 (아래쪽 따로)
number_frames = raw_frames[1:]  # 1~7

# 8, 9 추가 (직접 좌표 맞춤)
rect_8 = pygame.Rect(start_x, start_y + 8 * FRAME_H, FRAME_W, FRAME_H)
rect_9 = pygame.Rect(start_x, start_y + 9 * FRAME_H, FRAME_W, FRAME_H)

number_frames.append(sheet.subsurface(rect_8))
number_frames.append(sheet.subsurface(rect_9))

# ───────── 애니메이션 변수 ─────────
index = 0
timer = 0
delay = 150  # 속도 (작을수록 빠름)

# ───────── 게임 루프 ─────────
running = True
while running:
    dt = clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 애니메이션
    timer += dt
    if timer >= delay:
        index = (index + 1) % len(number_frames)
        timer = 0

    screen.fill((30, 30, 40))

    # 확대해서 보기 좋게
    img = pygame.transform.scale(number_frames[index], (80, 80))
    screen.blit(img, (160, 110))

    pygame.display.flip()

pygame.quit()