import pygame
import sys
import random

pygame.init()

# 화면 설정
WIDTH = 400
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dodge Game")

# 색상
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
PURPLE = (255, 0, 255)
WHITE = (255, 255, 255)

# FPS
clock = pygame.time.Clock()

# 칸 설정
cols = 6
cell_width = WIDTH // cols

# 플레이어
player_radius = 20
y = 460

# 폰트
font = pygame.font.SysFont(None, 30)
big_font = pygame.font.SysFont(None, 60)

# 최고 점수
high_score = 0


def reset_game():
    return {
        "grid_x": 3,
        "can_move": True,
        "obstacles": [],
        "spawn_rate": 2,
        "fall_speed": 2,
        "spawn_timer": 0,
        "score": 0,
        "score_timer": 0,
        "game_over": False
    }


game = reset_game()

running = True

while running:
    dt = clock.tick(60) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 🔥 좌우 이동 (칸 이동)
        if not game["game_over"]:
            if event.type == pygame.KEYDOWN and game["can_move"]:
                if event.key == pygame.K_LEFT:
                    game["grid_x"] -= 1
                    game["can_move"] = False
                if event.key == pygame.K_RIGHT:
                    game["grid_x"] += 1
                    game["can_move"] = False

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    game["can_move"] = True

        # 🔥 게임 재시작
        if game["game_over"]:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game = reset_game()

    if not game["game_over"]:
        # 범위 제한
        game["grid_x"] = max(0, min(cols - 1, game["grid_x"]))

        # 좌표 계산
        x = game["grid_x"] * cell_width + cell_width // 2

        # 🔥 장애물 생성 (칸 중앙)
        game["spawn_timer"] += dt
        if game["spawn_timer"] >= 1 / game["spawn_rate"]:
            game["spawn_timer"] = 0

            col = random.randint(0, cols - 1)
            obj_x = col * cell_width + cell_width // 2
            obj_y = -10

            game["obstacles"].append([obj_x, obj_y])

        # 🔥 장애물 이동
        for obj in game["obstacles"]:
            obj[1] += game["fall_speed"]

        # 🔥 충돌 체크
        for obj in game["obstacles"]:
            dx = x - obj[0]
            dy = y - obj[1]
            distance = (dx**2 + dy**2) ** 0.5
            if distance < player_radius + 8:
                game["game_over"] = True
                high_score = max(high_score, game["score"])

        # 🔥 점수 증가
        game["score_timer"] += dt
        if game["score_timer"] >= 0.1:
            game["score"] += 10
            game["score_timer"] = 0

        # 🔥 난이도 증가
        level = game["score"] // 1000
        game["spawn_rate"] = 1 + level
        game["fall_speed"] = 2 + level

    # 🔥 화면 그리기
    screen.fill(BLACK)

    # 세로선
    for i in range(1, cols):
        pygame.draw.line(screen, GREEN, (i * cell_width, 0), (i * cell_width, HEIGHT), 2)

    # 플레이어 위치
    x = game["grid_x"] * cell_width + cell_width // 2

    pygame.draw.circle(screen, RED, (x, y), player_radius)

    # 장애물
    for obj in game["obstacles"]:
        pygame.draw.circle(screen, PURPLE, (obj[0], obj[1]), 8)

    # 점수
    score_text = font.render(f"{game['score']}", True, WHITE)
    screen.blit(score_text, (WIDTH - 80, 10))

    # 🔥 게임 오버 UI
    if game["game_over"]:
        over_text = big_font.render("GAME OVER", True, WHITE)
        screen.blit(over_text, (WIDTH // 2 - 150, HEIGHT // 2 - 60))

        sub_text = font.render(f"Score: {game['score']}  High: {high_score}", True, WHITE)
        screen.blit(sub_text, (WIDTH // 2 - 120, HEIGHT // 2 + 10))

        restart_text = font.render("Press ENTER to Restart", True, WHITE)
        screen.blit(restart_text, (WIDTH // 2 - 130, HEIGHT // 2 + 40))

    pygame.display.flip()

pygame.quit()
sys.exit()