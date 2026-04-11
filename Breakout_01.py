import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 600, 1000
FPS = 60

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
    def __init__(self, x, y, width=60, height=20):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.hp = 1
        self.hit_timer = 0

    def update(self):
        pass

    def draw(self, screen):
        color = (255, 0, 0)

         # 🔥 피격 시 색 변경
        if self.hit_timer > 0:
            color = (255, 255, 255)

        pygame.draw.rect(
            screen,
            color,
            (self.x, self.y, self.width - 5, self.height - 5)
        )
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
        
        self.create_blocks()

    def create_blocks(self):
        self.blocks.clear()
        cols = 10
        rows = 5

        gap = 5

        # 🔥 화면 기준으로 자동 계산
        block_width = (WIDTH - gap * (cols - 1)) // cols
        block_height = 20

        start_x = 0
        start_y = 50

        for i in range(rows):
            for j in range(cols):
                x = start_x + j * (block_width + gap)
                y = start_y + i * (block_height + gap)

                self.blocks.append(Block(x, y, block_width, block_height))

    def drop_blocks(self):
        block_height = 20 + 5  # height + gap

        # 🔥 기존 블록 전부 아래로 이동
        for block in self.blocks:
            block.y += block_height

    def spawn_block_row(self):
        cols = 10
        gap = 5

        block_width = (WIDTH - gap * (cols - 1)) // cols
        block_height = 20

        start_y = 50

        for j in range(cols):
            x = j * (block_width + gap)
            y = start_y

            self.blocks.append(Block(x, y, block_width, block_height))

    def check_block_gameover(self):
        fail_line = self.paddle.y - 20  # 패들 바로 위

        for block in self.blocks:
            if block.y + block.height >= fail_line:
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

        
        


    def update(self):

        if self.state == "GAMEOVER":
            return5
    
        self.orbs.clear()

       # 🔥 입력은 항상 받는다
        self.handle_input()

    # 🔥 게임 진행 상태
        if self.state == "PLAY":
            self.ball.update()
            self.paddle.update()

            self.check_collision()
            self.check_gameover()

            # 🔥 게이지 체크는 PLAY에서만
            if self.state == "PLAY":
                if self.remember_gauge >= self.remember_max:
                    self.spawn_boss()

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
                self.boss.x,
                self.boss.y,
                self.boss.width,
                self.boss.height
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
                    self.create_blocks()  
                    
                return

        # 2️⃣ 블록
        if not collided:
            for block in self.blocks:
                block_rect = pygame.Rect(
                    block.x,
                    block.y,
                    block.width,
                    block.height
                )

                if ball_rect.colliderect(block_rect):
                    block.hp -= 1
                    self.ball.vy *= -1

                    if block.hp <= 0:
                        self.blocks.remove(block)
                        self.score += 10 # 내부 유지

                        self.remember_gauge += 1

                         # 🔥 오브 생성 (지금은 그냥 생성만)
                    
                    collided = True
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

        self.boss = Block(x, y, 200, 80)
        base_hp = 15    
        self.boss.max_hp = base_hp + (self.chapter * 5)
        self.boss.hp = self.boss.max_hp

        self.boss.x = WIDTH // 2 - self.boss.width // 2

        speed = 5 + self.chapter

        self.ball.vx = speed if self.ball.vx > 0 else -speed
        self.ball.vy = -speed

    def check_gameover(self):
        if self.ball.y >= HEIGHT:
            self.state = "GAMEOVER"

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