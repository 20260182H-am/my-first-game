from ast import pattern
import random  # 파일 맨 위에 추가 필요

import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 600, 1000
FPS = 60

GRID_SIZE = 50

COLS = WIDTH // GRID_SIZE   # 12
ROWS = HEIGHT // GRID_SIZE  # 20

PLAY_ROWS = 17  # 실제 플레이 영역

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()


# =========================
# Ball
# =========================
class Ball:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.vx = 5
        self.vy = -5
        self.radius = 8

    def update(self):
        # 이동만 담당
        self.x += self.vx
        self.y += self.vy

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 255), (self.x, self.y), self.radius)


# =========================
# Paddle
# =========================
class Paddle:
    def __init__(self):
        self.x = WIDTH // 2 - 50
        self.y = HEIGHT - 40
        self.speed = 7
        self.width = 100
        self.height = 12

    def update(self):
        # GameManager가 값을 바꿔줌
        pass

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 255, 255), (self.x, self.y, self.width, self.height))


# =========================
# Block
# =========================
class Block:
    def __init__(self, col, row, size):
        self.col = col
        self.row = row
        self.size = size
        
        self.hp = 1
        self.hit_timer = 0

    def update(self):
        pass

    def draw(self, screen):
        x = self.col * self.size
        y = self.row * self.size

        color = (255, 0, 0)

        if self.hit_timer > 0:
            color = (255, 255, 255)

        pygame.draw.rect(screen, color, (x, y, self.size, self.size))
# =========================
# Orb
# =========================
class Orb:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        # 나중에 사용할 값들 (지금은 의미 없음)
        self.vx = 0
        self.vy = 0
        self.target_x = 0
        self.target_y = 0

    def update(self):
        pass   # 아직 구현 안 함

    def draw(self, screen):
        # 임시로 점만 찍어도 됨 (선택)
        pygame.draw.circle(screen, (0, 255, 255), (int(self.x), int(self.y)), 3)


# =========================
# GameManager
# =========================
class GameManager:
    def __init__(self):
        self.state = "PLAY"
        # 추가
        # "BOSS
        self.boss = None
        self.score = 0
        self.lives = 3

        self.remember_gauge = 0
        self.remember_max = 30

        self.drop_timer = 0
        self.drop_interval = 300  # 5초 (FPS 60 기준)

        self.chapter = 1
        self.max_chapter = 3

        self.orbs = []   # 🔥 오브 리스트 (나중에 사용)

        self.ball = Ball()
        self.paddle = Paddle()
        self.blocks = []


        self.patterns = [
            [[0,1,0],
            [1,1,1],
            [0,1,0]],

            [[1,0,1],
            [0,1,0],
            [1,0,1]],

            [[1,1,1],
            [1,0,1],
            [1,1,1]],

            [[0,1,1],
            [1,1,0],
            [0,1,0]],
        ]

    def spawn_filled_row(self):
        patterns = [
            [[1,1,1],
            [1,1,1],
            [1,1,1]],

            [[1,1],
            [1,1],
            [1,1]],

            [[1],
            [1],
            [1]],
        ]

        col = 0

        while col < COLS:
            pattern = random.choice(patterns)
            width = len(pattern[0])

            if col + width > COLS:
                pattern = [[1],[1],[1]]
                width = 1

            for i in range(len(pattern)):
                for j in range(len(pattern[0])):
                    if pattern[i][j] == 1:
                        self.blocks.append(
                            Block(col + j, i, GRID_SIZE)
                        )

            col += width
            
        
    def drop_blocks(self):
        # 🔥 기존 블록 아래로 이동
        for block in self.blocks:
            block.row += 3   # 🔥 한 번에 3칸 (패턴 높이)

        # 🔥 새 줄 생성 (꽉 채움)
        self.spawn_filled_row()

        # 🔥 게임오버 체크
        self.check_block_gameover()


    def can_spawn_pattern(self, start_x, start_y, block_size):
        for block in self.blocks:
            for i in range(3):
                for j in range(3):
                    x = start_x + j * block_size
                    y = start_y + i * block_size

                    new_rect = pygame.Rect(x, y, block_size, block_size)
                    block_rect = pygame.Rect(block.x, block.y, block.width, block.height)

                    if new_rect.colliderect(block_rect):
                        return False
        return True
 

    def spawn_pattern(self):
        pattern = random.choice(self.patterns)

        start_col = random.randint(0, COLS - 3)
        start_row = 0

        for i in range(3):
            for j in range(3):
                if pattern[i][j] == 1:
                    col = start_col + j
                    row = start_row + i

                    self.blocks.append(Block(col, row, GRID_SIZE))

    def check_block_gameover(self):
        fail_line = self.paddle.y - 20  # 패들 바로 위

        for block in self.blocks:
            if block.row >= PLAY_ROWS:
                self.state = "GAMEOVER"
                return

    def handle_input(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            self.paddle.x -= self.paddle.speed
        if keys[pygame.K_RIGHT]:
            self.paddle.x += self.paddle.speed

        # 🔥 화면 밖 제한
        if self.paddle.x < 0:
            self.paddle.x = 0

        if self.paddle.x + self.paddle.width > WIDTH:
            self.paddle.x = WIDTH - self.paddle.width

       


    def handle_keydown(self, event):
        if event.key == pygame.K_r and self.state == "GAMEOVER":
            self.__init__()

        if self.state == "GAMECLEAR":
            if event.key == pygame.K_r:
                self.__init__()

        # 디버그 커맨드
        if event.key == pygame.K_1:
            self.remember_gauge = self.remember_max

        if event.key == pygame.K_2:
            if self.state == "BOSS" and self.boss:
                self.boss.hp = 0

        # 🔥 블록 강제 하강 (디버그)
        if event.key == pygame.K_3:
            self.drop_blocks()
        
        


    def update(self):
  
        if self.state == "GAMEOVER":
            return

        self.orbs.clear()

        self.handle_input()

        if self.state == "PLAY" or self.state == "BOSS":
            self.ball.update()
            self.paddle.update()

            self.check_collision()

            # 🔥 게이지 → 보스
            if self.state == "PLAY":
                if self.remember_gauge >= self.remember_max:
                    self.spawn_boss()

            # 🔥 블록 하강 타이머
            self.drop_timer += 1
            if self.drop_timer >= self.drop_interval:
                self.drop_blocks()
                self.drop_timer = 0

        for orb in self.orbs:
            orb.update()

        if self.boss:
            if self.boss.hit_timer > 0:
                self.boss.hit_timer -= 1


    def draw(self, screen):
        screen.fill((40, 40, 40))

        # 🔥 GRID (격자)
        grid_size = 50
        grid_color = (80, 80, 80)  # 연한 회색

        # 세로 17칸까지만 그림
        for row in range(15):
            for col in range(12):
                x = col * grid_size
                y = row * grid_size

                pygame.draw.rect(
                    screen,
                    grid_color,
                    (x, y, grid_size, grid_size),
                    1  # 🔥 테두리만
                )

        # 1️⃣ 일반 게임 요소
        self.ball.draw(screen)
        self.paddle.draw(screen)

        # 블록 그리기
        for block in self.blocks:
            block.draw(screen)

        if self.boss:
            self.boss.draw(screen)

            # 🔥 여기 추가 (중요)
        for orb in self.orbs:
            orb.draw(screen)

        # 2️⃣ 상태 기반 UI
        if self.state == "GAMEOVER":
            font = pygame.font.SysFont(None, 60)
            text = font.render("GAME OVER", True, (255, 0, 0))
            screen.blit(text, (WIDTH//2 - 150, HEIGHT//2))

        if self.state == "GAMECLEAR":
            font = pygame.font.SysFont(None, 60)
            text = font.render("CLEAR", True, (0, 255, 0))

            x = WIDTH // 2 - text.get_width() // 2
            y = HEIGHT // 2 - text.get_height() // 2

            screen.blit(text, (x, y))
    
        # 🔥 REMEMBER UI
        font = pygame.font.SysFont(None, 60)

        text_bg = font.render("REMEMBER", True, (100, 100, 100))   # 회색
        text_fill = font.render("REMEMBER", True, (255, 255, 0))   # 노란색

        font = pygame.font.SysFont(None, 30)
        text = font.render(f"CHAPTER {self.chapter}", True, (255,255,255))
        screen.blit(text, (20, 80))

        # 위치 (우상단)
        x = 20
        y = 20

        # 비율 계산
        ratio = self.remember_gauge / self.remember_max
        ratio = max(0, min(1, ratio))   # 0~1 제한

        fill_width = int(text_bg.get_width() * ratio)

        # 1️⃣ 배경 텍스트
        screen.blit(text_bg, (x, y))

        # 2️⃣ 채워지는 텍스트 (잘라서)
        if fill_width > 0:
            fill_rect = pygame.Rect(0, 0, fill_width, text_bg.get_height())
            screen.blit(text_fill, (x, y), fill_rect)

        # 🔥 실패 라인 깜빡임
        fail_line = self.paddle.y - 20

        # 깜빡임 (시간 기반)
        if (pygame.time.get_ticks() // 300) % 2 == 0:
            pygame.draw.line(screen, (255, 0, 0), (0, fail_line), (WIDTH, fail_line), 2)

            
                    
    
    def check_collision(self):

        ball_rect = pygame.Rect(
            self.ball.x - self.ball.radius,
            self.ball.y - self.ball.radius,
            self.ball.radius * 2,
            self.ball.radius * 2
        )

        # 🔥 충돌 여부 체크용
        collided = False

        # 1️⃣ 패들
        paddle_rect = pygame.Rect(
            self.paddle.x,
            self.paddle.y,
            self.paddle.width,
            self.paddle.height
        )

        if ball_rect.colliderect(paddle_rect) and self.ball.vy > 0:
            offset = (self.ball.x - self.paddle.x) / self.paddle.width
            self.ball.vx = (offset - 0.5) * 10   # 좌우 방향
            self.ball.vy *= -1
            collided = True

          # 🔥 BOSS 충돌
        if self.state == "BOSS" and self.boss:
            boss_rect = pygame.Rect(
                self.boss.col * GRID_SIZE,
                self.boss.row * GRID_SIZE,
                self.boss.size,
                self.boss.size
            )

            if ball_rect.colliderect(boss_rect):
                self.ball.vy *= -1
                self.boss.hp -= 1
                self.boss.hit_timer = 10
                collided = True

                if self.boss.hp <= 0:
                    self.boss = None
                    self.remember_gauge = 0

                    # 🔥 챕터 증가
                    self.chapter += 1

                    # 🔥 엔딩 체크
                    if self.chapter > self.max_chapter:
                        self.state = "GAMECLEAR"
                        return

                    # 🔥 다음 챕터
                    self.state = "PLAY"
                     

        # 2️⃣ 블록
       
        if not collided:
            ball_col = self.ball.x // GRID_SIZE
            ball_row = self.ball.y // GRID_SIZE

            for block in self.blocks:
                if block.col == ball_col and block.row == ball_row:
                    block.hp -= 1
                    self.ball.vy *= -1

                    if block.hp <= 0:
                        self.blocks.remove(block)
                        self.remember_gauge += 1

                    break
        

        # 3️⃣ 벽 (마지막)
        # 🔥 3️⃣ 벽 충돌 (반지름 고려)
        if not collided:
            if self.ball.x - self.ball.radius <= 0 or self.ball.x + self.ball.radius >= WIDTH:
                    self.ball.vx *= -1

            if self.ball.y - self.ball.radius <= 0:
                self.ball.vy *= -1

    def spawn_boss(self):
        if self.state == "BOSS":
            return

        self.state = "BOSS"

        # 기존 블록 제거
        self.blocks.clear()

        # 중앙에 보스 생성
        x = WIDTH // 2 - 50
        y = 100

        boss_size = GRID_SIZE * 4
        boss_col = (COLS // 2) - 2   # 중앙 정렬
        boss_row = 2

        self.boss = Block(boss_col, boss_row, boss_size)
        base_hp = 15    
        self.boss.max_hp = base_hp + (self.chapter * 5)
        self.boss.hp = self.boss.max_hp

        

        speed = 5 + self.chapter

        if self.ball.vx == 0:
            self.ball.vx = speed
        else:
            self.ball.vx = speed if self.ball.vx > 0 else -speed

        self.ball.vy = -speed



    def check_gameover(self):
        for block in self.blocks:
            if block.row >= PLAY_ROWS:
                self.state = "GAMEOVER"
                return
# =========================
# Main Loop
# =========================
def main():
    game = GameManager()

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        # 🔥 이거 추가
            if event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.update()
        game.draw(screen)

        pygame.display.flip()


main()