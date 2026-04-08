import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 800, 600
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
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hp = 1
        self.width = 60
        self.height = 20

    def update(self):
        pass

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y, self.width, self.height))


# =========================
# GameManager
# =========================
class GameManager:
    def __init__(self):
        self.state = "PLAY"
        self.score = 0
        self.lives = 3

        self.ball = Ball()
        self.paddle = Paddle()
        self.blocks = []

        self.create_blocks()

    def create_blocks(self):
        for i in range(5):
            for j in range(10):
                self.blocks.append(Block(j * 65, i * 25 + 50))

    def handle_input(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            self.paddle.x -= self.paddle.speed
        if keys[pygame.K_RIGHT]:
            self.paddle.x += self.paddle.speed

    def update(self):
        if self.state == "PLAY":
            self.handle_input()

            self.ball.update()
            self.paddle.update()

            self.check_collision()
            self.check_gameover()

    def draw(self, screen):
        screen.fill((40, 40, 40))

        self.ball.draw(screen)
        self.paddle.draw(screen)

        for block in self.blocks:
            block.draw(screen)

    def check_collision(self):
        # 여기서 충돌 처리
        pass

    def check_gameover(self):
        # 여기서 게임오버 판정
        pass


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

        game.update()
        game.draw(screen)

        pygame.display.flip()


main()