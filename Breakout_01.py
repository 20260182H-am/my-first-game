import random
import math
import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 600, 1000
FPS = 60
GRID_SIZE = 50
COLS = WIDTH // GRID_SIZE   # 12
ROWS = HEIGHT // GRID_SIZE  # 20
PLAY_ROWS = 17

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# =============================================================
# 부드러운 하강 상수
# =============================================================
WAIT_FRAMES  = 270   # 4.5초
SLIDE_FRAMES = 30    # 0.5초
DROP_CYCLE   = WAIT_FRAMES + SLIDE_FRAMES   # 300 = 5초 (일반 블록)

BOSS_WAIT_FRAMES  = 210  # 3.5초
BOSS_SLIDE_FRAMES = 30   # 0.5초
BOSS_DROP_CYCLE   = BOSS_WAIT_FRAMES + BOSS_SLIDE_FRAMES  # 240 = 4초


def slide_offset(timer, wait, slide):
    """timer가 wait~(wait+slide) 구간일 때 0→GRID_SIZE 픽셀 보간"""
    if timer < wait:
        return 0.0
    t = (timer - wait) / slide
    t = max(0.0, min(1.0, t))
    t = 1.0 - (1.0 - t) ** 2   # ease-out
    return t * GRID_SIZE


# =============================================================
# 기본 오브젝트
# =============================================================

class Ball:
    def __init__(self):
        self.x = float(WIDTH // 2)
        self.y = float(HEIGHT // 2)
        self.vx = 7.0
        self.vy = 7.0
        self.radius = 12

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), self.radius)


class Paddle:
    def __init__(self):
        self.width = 140
        self.height = 20
        self.x = WIDTH // 2 - self.width // 2
        self.y = HEIGHT - 50
        self.speed = 10

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 255, 255), (self.x, self.y, self.width, self.height))


class PatternBlock:
    def __init__(self, col, row, pattern, color):
        self.col = col
        self.row = row
        self.pattern = pattern
        self.color = color
        self.blocks = []
        self.hp = 0
        self._build_blocks()
        self.max_hp = self.hp
        self.hit_timer = 0
        self.shake_dx = 0
        self.shake_dy = 0
        self.drop_timer = 0   # WaveManager가 동기화

    def _build_blocks(self):
        self.blocks.clear()
        for i in range(len(self.pattern)):
            for j in range(len(self.pattern[0])):
                if self.pattern[i][j] == 1:
                    self.blocks.append((self.col + j, self.row + i))
        self.hp = max(1, round(len(self.blocks) / 2))

    def move_down_logic(self):
        self.row += 1
        self._build_blocks()

    def pixel_y_offset(self):
        return slide_offset(self.drop_timer, WAIT_FRAMES, SLIDE_FRAMES)

    def take_hit(self):
        self.hit_timer = 12
        direction = random.choice([(3,0),(-3,0),(0,3),(0,-3)])
        self.shake_dx, self.shake_dy = direction

    def draw(self, screen):
        oy = self.pixel_y_offset()
        for (c, r) in self.blocks:
            x = c * GRID_SIZE
            y = r * GRID_SIZE + oy
            if self.hit_timer > 0:
                phase = self.hit_timer % 2
                x += self.shake_dx * phase
                y += self.shake_dy * phase
                color = (255, 255, 255)
            else:
                color = self.color
            pygame.draw.rect(screen, color, (int(x), int(y), GRID_SIZE, GRID_SIZE))


# =============================================================
# WaveManager
# =============================================================

class WaveManager:
    def __init__(self, base_patterns, pattern_colors):
        self.base_patterns = base_patterns
        self.pattern_colors = pattern_colors
        self.all_blocks: list[PatternBlock] = []
        self.drop_timer = 0
        self.next_wave_row = -3
        self._spawn_wave(self.next_wave_row)
        self.next_wave_row -= 3

    def update(self):
        self.drop_timer += 1
        for pb in self.all_blocks:
            pb.drop_timer = self.drop_timer

        if self.drop_timer >= DROP_CYCLE:
            self.drop_timer = 0
            self._do_drop()

    def _do_drop(self):
        for pb in self.all_blocks:
            pb.move_down_logic()
            pb.drop_timer = 0
        self.next_wave_row += 1
        if self.next_wave_row >= -3:
            self._spawn_wave(self.next_wave_row)
            self.next_wave_row -= 3

    def remove_block(self, pb):
        if pb in self.all_blocks:
            self.all_blocks.remove(pb)

    def is_gameover(self, play_rows):
        for pb in self.all_blocks:
            for (_, r) in pb.blocks:
                if r >= play_rows:
                    return True
        return False

    def _spawn_wave(self, start_row):
        col = 0
        while col + 3 <= COLS:
            self._spawn_one_group(col, start_row)
            col += 3

    def _spawn_one_group(self, col, row):
        base = random.choice(self.base_patterns)
        pattern = base
        for _ in range(random.randint(0, 3)):
            pattern = self._rotate(pattern)
        index = self.base_patterns.index(base)
        color = self.pattern_colors[index]
        pb = PatternBlock(col, row, pattern, color)
        self.all_blocks.append(pb)

        filled = {(j,i) for i in range(len(pattern))
                  for j in range(len(pattern[0])) if pattern[i][j]==1}
        holes = [(j,i) for i in range(3) for j in range(3) if (j,i) not in filled]
        for group in self._split_holes(holes):
            hp = [[0]*3 for _ in range(3)]
            for (x,y) in group:
                hp[y][x] = 1
            self.all_blocks.append(PatternBlock(col, row, hp, (80,80,80)))

    @staticmethod
    def _rotate(pattern):
        return [list(row) for row in zip(*pattern[::-1])]

    @staticmethod
    def _split_holes(holes):
        holes_set = set(holes)
        visited = set()
        groups = []
        for cell in holes:
            if cell in visited:
                continue
            stack, group = [cell], []
            while stack:
                x,y = stack.pop()
                if (x,y) in visited:
                    continue
                visited.add((x,y))
                group.append((x,y))
                for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx,ny = x+dx,y+dy
                    if (nx,ny) in holes_set:
                        stack.append((nx,ny))
            groups.append(group)
        return groups


# =============================================================
# 보스 공통 — 부드러운 하강 믹스인
# =============================================================

class BossDropMixin:
    def _init_drop(self, base_py):
        self._drop_timer = 0
        self._base_py = float(base_py)

    def _drop_update(self):
        self._drop_timer += 1
        if self._drop_timer >= BOSS_DROP_CYCLE:
            self._drop_timer = 0
            self._base_py += GRID_SIZE
            self._on_drop_logic()

    def _current_py(self):
        return self._base_py + slide_offset(self._drop_timer, BOSS_WAIT_FRAMES, BOSS_SLIDE_FRAMES)

    def _on_drop_logic(self):
        pass


# =============================================================
# 챕터 1 보스 — 갑옷 + 코어
# =============================================================

class ArmorPiece:
    def __init__(self, cells, color, hp=2):
        self.cells = cells
        self.abs_cells: list[pygame.Rect] = []
        self.color = color
        self.hp = hp
        self.max_hp = hp
        self.hit_timer = 0
        self.shake_dx = 0
        self.shake_dy = 0
        self.alive = True
        # 재생성
        self.regen_timer = 0
        self.REGEN_TOTAL  = 600   # 10초
        self.REGEN_HIDDEN = 420   # 처음 7초 숨김
        # REGEN_BLINK = 마지막 180프레임(3초)

    def update_abs(self, ax, ay):
        self.abs_cells = [
            pygame.Rect(int(ax + dc*GRID_SIZE), int(ay + dr*GRID_SIZE), GRID_SIZE, GRID_SIZE)
            for (dc,dr) in self.cells
        ]

    def take_hit(self):
        if not self.alive:
            return
        self.hit_timer = 12
        self.shake_dx, self.shake_dy = random.choice([(3,0),(-3,0),(0,3),(0,-3)])

    def start_regen(self):
        self.regen_timer = self.REGEN_TOTAL

    def update(self):
        if self.hit_timer > 0:
            self.hit_timer -= 1
        if self.regen_timer > 0:
            self.regen_timer -= 1
            if self.regen_timer == 0:
                self.alive = True
                self.hp = self.max_hp

    def draw(self, screen):
        if not self.alive:
            if self.regen_timer <= 0:
                return
            elapsed = self.REGEN_TOTAL - self.regen_timer
            if elapsed < self.REGEN_HIDDEN:
                return
            # 마지막 3초 깜박 (30% opacity)
            blink_on = (pygame.time.get_ticks() // 200) % 2 == 0
            if not blink_on:
                return
            for rect in self.abs_cells:
                s = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
                s.fill((*self.color, 76))
                screen.blit(s, rect.topleft)
            return

        for rect in self.abs_cells:
            x, y = rect.x, rect.y
            if self.hit_timer > 0:
                phase = self.hit_timer % 2
                x += self.shake_dx * phase
                y += self.shake_dy * phase
                color = (255,255,255)
            else:
                color = self.color
            pygame.draw.rect(screen, color, (x, y, GRID_SIZE, GRID_SIZE))


class Boss1(BossDropMixin):
    NAME = "BOSS 1 — ARMOR"
    ARMOR_COLORS = [(200,80,80),(80,200,80),(80,80,200),(200,200,80)]
    CORE_COLOR   = (255,220,0)

    def __init__(self):
        self.anchor_col = COLS//2 - 2
        self.anchor_row = -4
        self._init_drop(self.anchor_row * GRID_SIZE)

        armor_cells = [
            [(0,0),(1,0),(0,1)],
            [(2,0),(3,0),(3,1)],
            [(0,2),(0,3),(1,3)],
            [(3,2),(2,3),(3,3)],
        ]
        self.armors = [ArmorPiece(cells, self.ARMOR_COLORS[i], hp=2)
                       for i,cells in enumerate(armor_cells)]
        self.core = ArmorPiece([(1,1),(2,1),(1,2),(2,2)], self.CORE_COLOR, hp=5)
        self._refresh_abs()

    def _refresh_abs(self):
        ax = self.anchor_col * GRID_SIZE
        ay = self._current_py()
        for a in self.armors:
            a.update_abs(ax, ay)
        self.core.update_abs(ax, ay)

    def _on_drop_logic(self):
        self.anchor_row += 1

    @property
    def is_dead(self):
        return not self.core.alive

    @property
    def total_hp(self):
        return self.core.hp

    @property
    def max_total_hp(self):
        return self.core.max_hp

    def all_rects(self):
        result = []
        for a in self.armors:
            if a.alive:
                for rect in a.abs_cells:
                    result.append((rect, a))
        if self.core.alive:
            for rect in self.core.abs_cells:
                result.append((rect, self.core))
        return result

    def update(self):
        self._drop_update()
        self._refresh_abs()
        for a in self.armors:
            a.update()
        self.core.update()

    def take_hit(self, piece: ArmorPiece):
        if not piece.alive:
            return
        piece.take_hit()
        piece.hp -= 1
        if piece.hp <= 0:
            piece.alive = False
            if piece is not self.core:
                piece.start_regen()

    def draw(self, screen):
        for a in self.armors:
            a.draw(screen)
        self.core.draw(screen)

    def is_gameover(self):
        return self._current_py() + 4*GRID_SIZE >= PLAY_ROWS * GRID_SIZE


# =============================================================
# 챕터 2 보스 — 회전 보호막 + 코어
# =============================================================

class ShieldOrb:
    def __init__(self, cx, cy, color, hp=2):
        self.cx = float(cx)
        self.cy = float(cy)
        self.color = color
        self.hp = hp
        self.max_hp = hp
        self.hit_timer = 0
        self.alive = True

    @property
    def rect(self):
        hs = GRID_SIZE//2
        return pygame.Rect(int(self.cx)-hs, int(self.cy)-hs, GRID_SIZE, GRID_SIZE)

    def take_hit(self):
        self.hit_timer = 12
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False

    def draw(self, screen):
        if not self.alive:
            return
        color = (255,255,255) if self.hit_timer > 0 else self.color
        pygame.draw.rect(screen, color, self.rect)


class Boss2Core:
    """2x2 코어 — 체력 공유"""
    COLOR = (255,220,0)

    def __init__(self, cx, cy):
        self.cx = float(cx)
        self.cy = float(cy)
        self.hp = 5
        self.max_hp = 5
        self.hit_timer = 0
        self.alive = True
        hs = GRID_SIZE//2
        self.offsets = [(-hs,-hs),(hs,-hs),(-hs,hs),(hs,hs)]

    def rects(self):
        return [pygame.Rect(int(self.cx+ox)-GRID_SIZE//2,
                            int(self.cy+oy)-GRID_SIZE//2,
                            GRID_SIZE, GRID_SIZE)
                for (ox,oy) in self.offsets]

    def take_hit(self):
        self.hit_timer = 12
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False

    def update_pos(self, cx, cy):
        self.cx = cx
        self.cy = cy

    def draw(self, screen):
        if not self.alive:
            return
        color = (255,255,255) if self.hit_timer > 0 else self.COLOR
        for rect in self.rects():
            pygame.draw.rect(screen, color, rect)


class Boss2(BossDropMixin):
    NAME = "BOSS 2 — SHIELD"
    INNER_COLOR = (80,200,255)
    OUTER_COLOR = (255,120,80)

    # 코어: 2x2 → 외곽 반지름 = GRID_SIZE (50px)
    # 안쪽 보호막 중심: 코어외곽(50) + 간격(50) + 블록반(25) = 125 → GRID_SIZE*2.5
    INNER_R = GRID_SIZE * 2.5   # 125px
    # 바깥 보호막 중심: 안쪽중심(125) + 블록(50) + 간격(50) + 블록반(25) = 250 → GRID_SIZE*5
    OUTER_R = GRID_SIZE * 5.0   # 250px

    def __init__(self):
        self.cx = float(WIDTH//2)
        self.cy = float(GRID_SIZE * -4)
        self._init_drop(self.cy)

        self.move_dir = 1
        self.move_speed = 1.2

        self.inner_angle = 0.0
        self.outer_angle = 0.0
        self.inner_speed = 0.018
        self.outer_speed = 0.013

        self.core = Boss2Core(self.cx, self.cy)
        self._build_shields()

    def _build_shields(self):
        self.inner_orbs: list[ShieldOrb] = []
        for i in range(4):
            angle = math.pi/2 * i
            ox = self.cx + self.INNER_R * math.cos(angle)
            oy = self.cy + self.INNER_R * math.sin(angle)
            self.inner_orbs.append(ShieldOrb(ox, oy, self.INNER_COLOR, hp=2))

        self.outer_orbs: list[ShieldOrb] = []
        for i in range(4):
            angle = math.pi/2 * i
            perp = angle + math.pi/2
            for delta in [-1, 1]:
                ox = self.cx + self.OUTER_R*math.cos(angle) + GRID_SIZE*delta*math.cos(perp)
                oy = self.cy + self.OUTER_R*math.sin(angle) + GRID_SIZE*delta*math.sin(perp)
                self.outer_orbs.append(ShieldOrb(ox, oy, self.OUTER_COLOR, hp=2))

    def _update_orb_positions(self):
        for i, orb in enumerate(self.inner_orbs):
            angle = math.pi/2*i + self.inner_angle
            orb.cx = self.cx + self.INNER_R*math.cos(angle)
            orb.cy = self.cy + self.INNER_R*math.sin(angle)

        for i in range(4):
            angle = math.pi/2*i + self.outer_angle
            perp = angle + math.pi/2
            for j, delta in enumerate([-1,1]):
                idx = i*2+j
                self.outer_orbs[idx].cx = self.cx + self.OUTER_R*math.cos(angle) + GRID_SIZE*delta*math.cos(perp)
                self.outer_orbs[idx].cy = self.cy + self.OUTER_R*math.sin(angle) + GRID_SIZE*delta*math.sin(perp)

    def _on_drop_logic(self):
        pass   # cy는 _current_py()로 계산

    @property
    def is_dead(self):
        return not self.core.alive

    @property
    def total_hp(self):
        return self.core.hp

    @property
    def max_total_hp(self):
        return self.core.max_hp

    def all_rects(self):
        result = []
        for orb in self.inner_orbs:
            if orb.alive:
                result.append((orb.rect, orb))
        for orb in self.outer_orbs:
            if orb.alive:
                result.append((orb.rect, orb))
        if self.core.alive:
            for rect in self.core.rects():
                result.append((rect, self.core))
        return result

    def update(self):
        self.inner_angle -= self.inner_speed
        self.outer_angle += self.outer_speed

        # 좌우 이동
        self.cx += self.move_speed * self.move_dir
        max_reach = self.OUTER_R + GRID_SIZE
        if self.cx + max_reach >= WIDTH - GRID_SIZE:
            self.move_dir = -1
        if self.cx - max_reach <= GRID_SIZE:
            self.move_dir = 1

        # 하강
        self._drop_update()
        self.cy = self._current_py()

        self._update_orb_positions()
        self.core.update_pos(self.cx, self.cy)

        for orb in self.inner_orbs + self.outer_orbs:
            if orb.hit_timer > 0:
                orb.hit_timer -= 1
        if self.core.hit_timer > 0:
            self.core.hit_timer -= 1

    def take_hit(self, piece):
        if isinstance(piece, (ShieldOrb, Boss2Core)):
            piece.take_hit()

    def draw(self, screen):
        for orb in self.outer_orbs:
            orb.draw(screen)
        for orb in self.inner_orbs:
            orb.draw(screen)
        self.core.draw(screen)

    def is_gameover(self):
        return self.cy + self.OUTER_R >= PLAY_ROWS * GRID_SIZE


# =============================================================
# 챕터 3 보스 — 분열 보스
# =============================================================

class SplitBlock:
    SIZE_COLORS = {4:(255,220,0), 2:(255,180,30), 1:(255,140,60)}
    SIZE_HP     = {4:4, 2:2, 1:1}
    INVINCIBLE_FRAMES = 60   # 1초 무적

    def __init__(self, px, py, size, drop_timer_ref=None):
        self.px = float(px)
        self.py = float(py)
        self._base_py = float(py)
        self.size = size
        self.px_size = size * GRID_SIZE
        self.max_hp = self.SIZE_HP[size]
        self.hp = self.max_hp
        self.hit_timer = 0
        self.invincible_timer = self.INVINCIBLE_FRAMES
        self.alive = True
        self.color = self.SIZE_COLORS.get(size,(200,200,0))
        self.drop_timer = drop_timer_ref if drop_timer_ref is not None else 0

    @property
    def rect(self):
        oy = slide_offset(self.drop_timer, BOSS_WAIT_FRAMES, BOSS_SLIDE_FRAMES)
        return pygame.Rect(int(self.px), int(self._base_py + oy), self.px_size, self.px_size)

    def take_hit(self):
        if self.invincible_timer > 0:
            return
        self.hit_timer = 12
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False

    def draw(self, screen):
        if not self.alive:
            return
        r = self.rect
        if self.invincible_timer > 0:
            blink = (self.invincible_timer // 5) % 2 == 0
            color = (255,255,255) if blink else self.color
        elif self.hit_timer > 0:
            color = (255,255,255)
        else:
            color = self.color
        pygame.draw.rect(screen, color, r)
        pygame.draw.rect(screen, (40,40,40), r, 2)
        # HP 바 (2x2 이상)
   


class Boss3(BossDropMixin):
    NAME = "BOSS 3 — SPLIT"

    def __init__(self):
        start_px = (COLS//2 - 2) * GRID_SIZE
        start_py = GRID_SIZE * -4
        self._init_drop(start_py)
        b = SplitBlock(start_px, start_py, 4, drop_timer_ref=0)
        b.invincible_timer = 0   # 초기 블록은 즉시 활성
        self.blocks: list[SplitBlock] = [b]

    @property
    def is_dead(self):
        return len(self.blocks) == 0 or all(not b.alive for b in self.blocks)

    @property
    def total_hp(self):
        return sum(b.hp for b in self.blocks if b.alive)

    @property
    def max_total_hp(self):
        # 처음 4x4 기준 최대
        return 4

    def all_rects(self):
        return [(b.rect, b) for b in self.blocks
                if b.alive and b.invincible_timer == 0]

    def update(self):
        self._drop_update()

        to_split = []
        for b in self.blocks:
            b.drop_timer = self._drop_timer
            if b.invincible_timer > 0:
                b.invincible_timer -= 1
            if b.hit_timer > 0:
                b.hit_timer -= 1
            if not b.alive and b.size > 1:
                to_split.append(b)

        for b in to_split:
            self.blocks.remove(b)
            self._split(b)

        # 죽은 1x1 + 무적 끝난 것 제거
        self.blocks = [b for b in self.blocks
                       if b.alive or (not b.alive and b.invincible_timer > 0)]

    def _on_drop_logic(self):
        for b in self.blocks:
            b._base_py += GRID_SIZE

    def _split(self, parent: SplitBlock):
        if parent.size == 4:
            half = parent.px_size // 2   # 100px
            gap  = GRID_SIZE             # 50px
            offsets = [
                (-gap,       -gap),
                (half+gap,   -gap),
                (-gap,       half+gap),
                (half+gap,   half+gap),
            ]
            for (ox,oy) in offsets:
                nx = max(0, min(WIDTH - half,               parent.px + ox))
                ny = max(0, min((PLAY_ROWS-3)*GRID_SIZE,   parent._base_py + oy))
                nb = SplitBlock(nx, ny, 2, self._drop_timer)
                self.blocks.append(nb)

        elif parent.size == 2:
            ps = parent.px_size   # 100px
            candidates = []
            lx = parent.px - GRID_SIZE
            if lx >= 0:
                candidates.append((lx, parent._base_py))
            rx = parent.px + ps
            if rx + GRID_SIZE <= WIDTH:
                candidates.append((rx, parent._base_py))
            for col_off in range(int(ps // GRID_SIZE)):
                ux = parent.px + col_off * GRID_SIZE
                uy = parent._base_py - GRID_SIZE
                if uy >= 0:
                    candidates.append((ux, uy))

            occupied = {(int(b.px), int(b._base_py)) for b in self.blocks if b.alive}
            candidates = [(x,y) for (x,y) in candidates if (int(x),int(y)) not in occupied]
            random.shuffle(candidates)
            for (nx,ny) in candidates[:4]:
                nb = SplitBlock(nx, ny, 1, self._drop_timer)
                self.blocks.append(nb)

    def take_hit(self, block: SplitBlock):
        block.take_hit()

    def draw(self, screen):
        for b in self.blocks:
            b.draw(screen)

    def is_gameover(self):
        for b in self.blocks:
            if b.alive:
                r = b.rect
                if r.bottom >= PLAY_ROWS * GRID_SIZE:
                    return True
        return False


# =============================================================
# 보스 체력 바 UI (우상단)
# =============================================================

def draw_boss_hp_bar(screen, boss):
    bx = WIDTH - 220
    by = 15
    bw = 200
    bh = 22

    name = getattr(boss, 'NAME', 'BOSS')
    font = pygame.font.SysFont(None, 24)
    txt = font.render(name, True, (255,200,100))
    screen.blit(txt, (bx, by - 20))

    total    = getattr(boss, 'total_hp', 0)
    maxtotal = getattr(boss, 'max_total_hp', 1)
    ratio = max(0.0, min(1.0, total / maxtotal)) if maxtotal > 0 else 0.0

    pygame.draw.rect(screen, (60,60,60),    (bx, by, bw, bh))
    pygame.draw.rect(screen, (220,60,60),   (bx, by, int(bw*ratio), bh))
    pygame.draw.rect(screen, (200,200,200), (bx, by, bw, bh), 2)

    hp_txt = font.render(f"{total} / {maxtotal}", True, (255,255,255))
    screen.blit(hp_txt, (bx + bw//2 - hp_txt.get_width()//2, by+3))


# =============================================================
# GameManager
# =============================================================

class GameManager:
    def __init__(self):
        self.state = "PLAY"
        self.boss = None
        self.remember_gauge = 0
        self.remember_max = 20
        self.chapter = 1
        self.max_chapter = 3
        self.ball = Ball()
        self.paddle = Paddle()

        self.base_patterns = [
            [[1,1,1],[1,0,0],[1,0,0]],
            [[1,1,1],[0,0,1],[0,0,1]],
            [[1,1,1],[1,1,1],[1,0,0]],
            [[1,1,0],[0,1,0],[0,1,0]],
            [[1,1,1],[1,0,0],[1,1,1]],
            [[1,1,0],[1,1,1],[0,0,1]],
            [[1,1,0],[1,0,0],[1,1,0]],
        ]
        self.pattern_colors = [
            (255,80,80),(255,200,80),(80,255,80),
            (80,80,255),(200,80,255),(80,255,255),(255,255,80),
        ]
        self.wave_manager = WaveManager(self.base_patterns, self.pattern_colors)

    @property
    def pattern_blocks(self):
        return self.wave_manager.all_blocks

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.paddle.x -= self.paddle.speed
        if keys[pygame.K_RIGHT]:
            self.paddle.x += self.paddle.speed
        self.paddle.x = max(0, min(WIDTH - self.paddle.width, self.paddle.x))

    def handle_keydown(self, event):
        if event.key == pygame.K_r and self.state in ("GAMEOVER","GAMECLEAR"):
            self.__init__()
        if event.key == pygame.K_1:
            self.remember_gauge = self.remember_max
        if event.key == pygame.K_2:
            if self.state == "BOSS" and self.boss:
                self._kill_boss()

    def _kill_boss(self):
        if isinstance(self.boss, Boss1):
            for a in self.boss.armors:
                a.alive = False; a.regen_timer = 0
            self.boss.core.alive = False
        elif isinstance(self.boss, Boss2):
            for o in self.boss.inner_orbs + self.boss.outer_orbs:
                o.alive = False
            self.boss.core.alive = False
        elif isinstance(self.boss, Boss3):
            for b in self.boss.blocks:
                b.alive = False; b.invincible_timer = 0

    def update(self):
        if self.state == "GAMEOVER":
            return

        self.handle_input()

        if self.state in ("PLAY","BOSS"):
            ball = self.ball
            speed = max(abs(ball.vx), abs(ball.vy))
            steps = int(speed) + 1
            dx = ball.vx / steps
            dy = ball.vy / steps

            for _ in range(steps):
                ball.x += dx
                ball.y += dy
                self._check_collision_step()
                if self.state not in ("PLAY","BOSS"):
                    break

            self.check_gameover()

            if self.state == "PLAY":
                if self.remember_gauge >= self.remember_max:
                    self.spawn_boss()
                self.wave_manager.update()
                if self.wave_manager.is_gameover(PLAY_ROWS):
                    self.state = "GAMEOVER"

            if self.state == "BOSS" and self.boss:
                self.boss.update()
                if self.boss.is_dead:
                    self._on_boss_dead()
                elif self.boss.is_gameover():
                    self.state = "GAMEOVER"

        for pb in self.pattern_blocks:
            if pb.hit_timer > 0:
                pb.hit_timer -= 1

    def _check_collision_step(self):
        ball = self.ball
        r = ball.radius
        ball_rect = pygame.Rect(ball.x-r, ball.y-r, r*2, r*2)

        # 벽
        if ball.x - r <= 0:
            ball.vx = abs(ball.vx); ball.x = r+1
        elif ball.x + r >= WIDTH:
            ball.vx = -abs(ball.vx); ball.x = WIDTH-r-1
        if ball.y - r <= 0:
            ball.vy = abs(ball.vy); ball.y = r+1

        # 패들
        paddle_rect = pygame.Rect(self.paddle.x, self.paddle.y, self.paddle.width, self.paddle.height)
        if ball_rect.colliderect(paddle_rect) and ball.vy > 0:
            offset = (ball.x - self.paddle.x) / self.paddle.width
            ball.vx = (offset - 0.5) * 10
            ball.vy = -abs(ball.vy)
            ball.y = self.paddle.y - r - 1
            return

        # 보스
        if self.state == "BOSS" and self.boss:
            for (rect, piece) in self.boss.all_rects():
                if hasattr(piece,'hit_timer') and piece.hit_timer > 0:
                    continue
                if hasattr(piece,'invincible_timer') and piece.invincible_timer > 0:
                    continue
                if ball_rect.colliderect(rect):
                    self._resolve_rect_collision(rect)
                    self.boss.take_hit(piece)
                    return

        # 일반 블록
        ball_col = int(ball.x) // GRID_SIZE
        ball_row = int(ball.y) // GRID_SIZE
        for pb in list(self.pattern_blocks):
            if pb.hit_timer > 0:
                continue
            hit_rect = None
            if (ball_col,ball_row) in pb.blocks:
                
                for (c,rr) in pb.blocks:
                    cr = pygame.Rect(c*GRID_SIZE, rr*GRID_SIZE, GRID_SIZE, GRID_SIZE)
                    if ball_rect.colliderect(cr):
                        hit_rect = cr; break
            else:
                for (c,rr) in pb.blocks:
                    if abs(c-ball_col)<=1 and abs(rr-ball_row)<=1:
                        cr = pygame.Rect(c*GRID_SIZE, rr*GRID_SIZE, GRID_SIZE, GRID_SIZE)
                        if ball_rect.colliderect(cr):
                            hit_rect = cr; break
            if hit_rect is None:
                continue
            self._resolve_rect_collision(hit_rect)
            pb.hp -= 1
            pb.take_hit()
            if pb.hp <= 0:
                self.remember_gauge += pb.max_hp
                self.wave_manager.remove_block(pb)
            return

    def _resolve_rect_collision(self, rect: pygame.Rect):
        ball = self.ball
        r = ball.radius

        ot = (ball.y+r) - rect.top
        ob = rect.bottom - (ball.y-r)
        ol = (ball.x+r) - rect.left
        or_ = rect.right - (ball.x-r)

        candidates = []
        if ball.vy > 0: candidates.append(('top',    ot))
        if ball.vy < 0: candidates.append(('bottom', ob))
        if ball.vx > 0: candidates.append(('left',   ol))
        if ball.vx < 0: candidates.append(('right',  or_))
        if not candidates:
            return

        side, _ = min(candidates, key=lambda x: x[1])
        if side == 'top':
            ball.vy = -abs(ball.vy); ball.y = rect.top - r - 1
        elif side == 'bottom':
            ball.vy =  abs(ball.vy); ball.y = rect.bottom + r + 1
        elif side == 'left':
            ball.vx = -abs(ball.vx); ball.x = rect.left - r - 1
        elif side == 'right':
            ball.vx =  abs(ball.vx); ball.x = rect.right + r + 1

    def spawn_boss(self):
        self.state = "BOSS"
        self.wave_manager.all_blocks.clear()
        self.remember_gauge = 0
        if self.chapter == 1:
            self.boss = Boss1()
        elif self.chapter == 2:
            self.boss = Boss2()
        elif self.chapter == 3:
            self.boss = Boss3()
       

    def _on_boss_dead(self):
        self.boss = None
        self.chapter += 1
        if self.chapter > self.max_chapter:
            self.state = "GAMECLEAR"
        else:
            self.state = "PLAY"
            self.remember_gauge = 0
            self.wave_manager = WaveManager(self.base_patterns, self.pattern_colors)

    def check_gameover(self):
        if self.ball.y > HEIGHT:
            self.state = "GAMEOVER"

    def draw(self, screen):
        screen.fill((40,40,40))
        for row in range(PLAY_ROWS):
            for col in range(COLS):
                pygame.draw.rect(screen, (70,70,70),
                    (col*GRID_SIZE, row*GRID_SIZE, GRID_SIZE, GRID_SIZE), 1)

        self.ball.draw(screen)
        self.paddle.draw(screen)

        if self.state == "PLAY":
            for pb in self.pattern_blocks:
                pb.draw(screen)

        if self.state == "BOSS" and self.boss:
            self.boss.draw(screen)
            draw_boss_hp_bar(screen, self.boss)

        self._draw_ui(screen)

        if self.state == "GAMEOVER":
            self._draw_overlay(screen, "GAME OVER", (255,60,60))
        if self.state == "GAMECLEAR":
            self._draw_overlay(screen, "CLEAR!", (60,255,120))

    def _draw_ui(self, screen):
        font_big = pygame.font.SysFont(None, 52)
        text_bg   = font_big.render("REMEMBER", True, (100,100,100))
        text_fill = font_big.render("REMEMBER", True, (255,220,0))

        ux, uy = 20, 860
        ratio = max(0, min(1, self.remember_gauge / self.remember_max))
        fill_w = int(text_bg.get_width() * ratio)
        screen.blit(text_bg, (ux, uy))
        if fill_w > 0:
            screen.blit(text_fill, (ux, uy), pygame.Rect(0,0,fill_w,text_bg.get_height()))

        font_sm = pygame.font.SysFont(None, 30)
        screen.blit(font_sm.render(f"CHAPTER  {self.chapter} / {self.max_chapter}", True, (255,255,255)), (ux, uy-28))

        state_color = {"PLAY":(120,255,120),"BOSS":(255,100,100)}.get(self.state,(200,200,200))
        screen.blit(font_sm.render(self.state, True, state_color), (WIDTH-80, uy-28))

        fail_y = self.paddle.y - 50
        if (pygame.time.get_ticks()//300)%2==0:
            pygame.draw.line(screen,(255,0,0),(0,fail_y),(WIDTH,fail_y),2)

    def _draw_overlay(self, screen, text, color):
        overlay = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,140))
        screen.blit(overlay, (0,0))
        font = pygame.font.SysFont(None, 80)
        t = font.render(text, True, color)
        screen.blit(t, (WIDTH//2-t.get_width()//2, HEIGHT//2-t.get_height()//2))
        font2 = pygame.font.SysFont(None, 34)
        t2 = font2.render("R키로 재시작", True, (200,200,200))
        screen.blit(t2, (WIDTH//2-t2.get_width()//2, HEIGHT//2+60))


# =============================================================
# Main
# =============================================================

def main():
    game = GameManager()
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                game.handle_keydown(event)
        game.update()
        game.draw(screen)
        pygame.display.flip()

main()

