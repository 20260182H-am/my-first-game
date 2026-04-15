import random
import math
import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 600, 1000
FPS = 60
GRID_SIZE = 50
COLS = WIDTH // GRID_SIZE
ROWS = HEIGHT // GRID_SIZE
PLAY_ROWS = 16

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

def kr_font(size):
    try:
        return pygame.font.Font("C:/Windows/Fonts/malgun.ttf", size)
    except:
        return pygame.font.SysFont("malgungothic", size)

# =============================================================
# 하강 상수
# =============================================================
WAIT_FRAMES   = 330
SLIDE_FRAMES  = 30
DROP_CYCLE    = WAIT_FRAMES + SLIDE_FRAMES

BOSS_WAIT_FRAMES  = 390
BOSS_SLIDE_FRAMES = 30
BOSS_DROP_CYCLE   = BOSS_WAIT_FRAMES + BOSS_SLIDE_FRAMES

BALL_BASE_SPEED = 8.5

def slide_offset(timer, wait, slide):
    if timer < wait:
        return 0.0
    t = (timer - wait) / slide
    t = max(0.0, min(1.0, t))
    t = 1.0 - (1.0 - t) ** 2
    return t * GRID_SIZE


# =============================================================
# 디버프 시스템
# =============================================================

DEBUFF_DURATION    = 300
DEBUFF_BLINK_START = 240

DEBUFF_REVERSE     = "reverse"
DEBUFF_BLIND       = "blind"
DEBUFF_SPEED_UP    = "speed_up"
DEBUFF_SPEED_DOWN  = "speed_down"
DEBUFF_PADDLE_SLOW = "paddle_slow"
DEBUFF_FAKE_BALL   = "fake_ball"

DEBUFF_COLORS = {
    DEBUFF_REVERSE:    (180,  60, 255),
    DEBUFF_BLIND:      (255, 220,   0),
    DEBUFF_SPEED_UP:   ( 60, 120, 255),
    DEBUFF_SPEED_DOWN: (255,  60,  60),
    DEBUFF_PADDLE_SLOW:(  60, 200,  80),
    DEBUFF_FAKE_BALL:  (255, 120, 200),
}

DEBUFF_NAMES = {
    DEBUFF_REVERSE:    "조작 반전",
    DEBUFF_BLIND:      "시야 제한",
    DEBUFF_SPEED_UP:   "공 가속",
    DEBUFF_SPEED_DOWN: "공 감속",
    DEBUFF_PADDLE_SLOW:"패들 둔화",
    DEBUFF_FAKE_BALL:  "가짜 공",
}

ALL_DEBUFFS = [
    DEBUFF_REVERSE, DEBUFF_BLIND, DEBUFF_SPEED_UP,
    DEBUFF_SPEED_DOWN, DEBUFF_PADDLE_SLOW, DEBUFF_FAKE_BALL,
]

# 챕터3(갑옷) 보스 상시 고정 디버프 후보
BOSS3_PERMANENT_DEBUFFS = [DEBUFF_FAKE_BALL, DEBUFF_REVERSE, DEBUFF_BLIND]


class ActiveDebuff:
    def __init__(self, kind):
        self.kind  = kind
        self.timer = 0

    @property
    def alive(self):
        return self.timer < DEBUFF_DURATION

    @property
    def blinking(self):
        return self.timer >= DEBUFF_BLINK_START

    def update(self):
        self.timer += 1


class PermanentDebuff:
    """챕터3 보스 1회 분열 후 상시 유지되는 디버프"""
    def __init__(self, kind):
        self.kind  = kind
        self.timer = 0

    @property
    def alive(self):
        return True

    @property
    def blinking(self):
        return False

    def update(self):
        pass


# =============================================================
# DebuffManager
# =============================================================

class DebuffManager:
    def __init__(self, chapter, mode="none", interval_params=None):
        self.chapter      = chapter
        self.mode         = mode
        self.active       = []
        self.permanent    = []
        self._pending_fake= False
        self._iv_state    = "delay"
        self._iv_timer    = 0
        self._iv_params   = interval_params or (600, 300, 600)
        self._iv_current  = None
        self._boss3_split_done = False
        self._boss3_perm_kind  = None
        self._pending_popup    = None

    def set_mode(self, mode, interval_params=None):
        self.mode       = mode
        self._iv_state  = "delay"
        self._iv_timer  = 0
        if interval_params:
            self._iv_params = interval_params
        if self._iv_current:
            self.active = [d for d in self.active if d.kind != self._iv_current]
            self._iv_current = None

    def add_permanent(self, kind):
        if any(p.kind == kind for p in self.permanent):
            return
        self.permanent.append(PermanentDebuff(kind))
        if kind == DEBUFF_FAKE_BALL:
            self._pending_fake = True
        self._boss3_perm_kind = kind

    def update(self):
        for p in self.permanent:
            p.update()
        for d in self.active:
            d.update()
        self.active = [d for d in self.active if d.alive]
        if self.mode in ("interval", "boss3"):
            self._update_interval()

    def _update_interval(self):
        delay_f, duration_f, cooldown_f = self._iv_params
        self._iv_timer += 1
        if self._iv_state == "delay":
            if self._iv_timer >= delay_f:
                self._iv_timer = 0
                self._iv_state = "active"
                self._trigger_interval(duration_f)
        elif self._iv_state == "active":
            if self._iv_timer >= duration_f:
                self._iv_timer = 0
                self._iv_state = "cooldown"
                if self._iv_current:
                    self.active = [d for d in self.active if d.kind != self._iv_current]
                    self._iv_current = None
        elif self._iv_state == "cooldown":
            if self._iv_timer >= cooldown_f:
                self._iv_timer = 0
                self._iv_state = "active"
                self._trigger_interval(duration_f)

    def _trigger_interval(self, duration_f):
        perm_kinds = {p.kind for p in self.permanent}
        available  = [k for k in ALL_DEBUFFS if k not in perm_kinds]
        if not available:
            available = ALL_DEBUFFS[:]
        kind = random.choice(available)
        d = ActiveDebuff(kind)
        self.active.append(d)
        self._iv_current = kind
        if kind == DEBUFF_FAKE_BALL:
            self._pending_fake = True
        self._pending_popup = kind

    def is_active(self, kind):
        if any(p.kind == kind for p in self.permanent):
            return True
        return any(d.kind == kind for d in self.active)

    def pop_fake_ball_request(self):
        if self._pending_fake:
            self._pending_fake = False
            return True
        return False

    def pop_popup_request(self):
        kind = self._pending_popup
        self._pending_popup = None
        return kind

    @property
    def all_active(self):
        return list(self.permanent) + list(self.active)


# =============================================================
# 디버프 팝업
# =============================================================

class DebuffPopup:
    SHOW_FRAMES = 70

    def __init__(self):
        self.timer = 0
        self.kind  = None

    @property
    def active(self):
        return self.kind is not None and self.timer < self.SHOW_FRAMES

    def show(self, kind):
        self.kind  = kind
        self.timer = 0

    def update(self):
        if self.active:
            self.timer += 1
        else:
            self.kind = None

    def draw(self, screen):
        if not self.active or self.kind is None:
            return
        t = self.timer / self.SHOW_FRAMES
        if t < 0.15:
            alpha = int(255 * (t / 0.15))
        elif t < 0.8:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (t - 0.8) / 0.2))
        alpha = max(0, min(255, alpha))

        color = DEBUFF_COLORS.get(self.kind, (200, 200, 200))
        name  = DEBUFF_NAMES.get(self.kind, self.kind)
        cx = WIDTH // 2
        cy = HEIGHT // 2 - 60

        bg = pygame.Surface((220, 90), pygame.SRCALPHA)
        bg.fill((0, 0, 0, int(160 * alpha / 255)))
        screen.blit(bg, (cx - 110, cy - 10))

        circle_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(circle_surf, (*color, alpha), (25, 25), 22)
        pygame.draw.circle(circle_surf, (255, 255, 255, alpha), (25, 25), 22, 2)
        screen.blit(circle_surf, (cx - 25, cy))

        font = kr_font(22)
        txt  = font.render(name, True, (*color[:3],))
        txt_surf = pygame.Surface(txt.get_size(), pygame.SRCALPHA)
        txt_surf.blit(txt, (0, 0))
        txt_surf.set_alpha(alpha)
        screen.blit(txt_surf, (cx - txt.get_width() // 2, cy + 55))


# =============================================================
# 시야 축소 오버레이
# =============================================================

class BlindOverlay:
    RAMP_FRAMES = 120

    def __init__(self):
        self._cache = {}

    def draw(self, screen, debuff_timer):
        progress  = min(1.0, debuff_timer / self.RAMP_FRAMES)
        max_alpha = 180
        alpha     = int(max_alpha * progress)
        if alpha <= 0:
            return
        if alpha not in self._cache:
            self._cache[alpha] = self._make_vignette(alpha)
        screen.blit(self._cache[alpha], (0, 0))

    def _make_vignette(self, alpha):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cx, cy  = WIDTH // 2, HEIGHT // 2
        max_r   = math.sqrt(cx**2 + cy**2)
        step    = 8
        for y in range(0, HEIGHT, step):
            for x in range(0, WIDTH, step):
                dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                t    = min(1.0, dist / max_r) ** 1.5
                a    = max(0, min(255, int(alpha * t)))
                surf.fill((0, 0, 0, a), (x, y, step, step))
        return surf


blind_overlay = BlindOverlay()


# =============================================================
# 페이드 / 연출
# =============================================================

class FadeOverlay:
    PHASE_IDLE     = 0
    PHASE_FADE_IN  = 1
    PHASE_HOLD     = 2
    PHASE_FADE_OUT = 3

    def __init__(self):
        self.phase           = self.PHASE_IDLE
        self.alpha           = 0
        self.timer           = 0
        self.label           = ""
        self.sub_label       = ""
        self.on_done         = None
        self.shake_t         = 0.0
        self.FADE_IN_FRAMES  = 30
        self.HOLD_FRAMES     = 90
        self.FADE_OUT_FRAMES = 30
        self._surf           = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    def start(self, label, sub_label="", on_done=None):
        self.label     = label
        self.sub_label = sub_label
        self.on_done   = on_done
        self.phase     = self.PHASE_FADE_IN
        self.alpha     = 0
        self.timer     = 0
        self.shake_t   = 0.0

    @property
    def active(self):
        return self.phase != self.PHASE_IDLE

    def update(self):
        if self.phase == self.PHASE_IDLE:
            return
        self.timer   += 1
        self.shake_t += 0.18
        if self.phase == self.PHASE_FADE_IN:
            self.alpha = int(200 * self.timer / self.FADE_IN_FRAMES)
            if self.timer >= self.FADE_IN_FRAMES:
                self.alpha = 200; self.timer = 0
                self.phase = self.PHASE_HOLD
        elif self.phase == self.PHASE_HOLD:
            if self.timer >= self.HOLD_FRAMES:
                self.timer = 0; self.phase = self.PHASE_FADE_OUT
        elif self.phase == self.PHASE_FADE_OUT:
            self.alpha = int(200 * (1 - self.timer / self.FADE_OUT_FRAMES))
            if self.timer >= self.FADE_OUT_FRAMES:
                self.alpha = 0; self.phase = self.PHASE_IDLE
                if self.on_done:
                    self.on_done()

    def draw(self, screen):
        if self.phase == self.PHASE_IDLE:
            return
        self._surf.fill((0, 0, 0, self.alpha))
        screen.blit(self._surf, (0, 0))
        if self.label:
            font = kr_font(52)
            sx   = math.sin(self.shake_t * 2.1) * 3
            sy   = math.cos(self.shake_t * 1.7) * 2
            t    = font.render(self.label, True, (255, 220, 60))
            screen.blit(t, (int(WIDTH//2 - t.get_width()//2 + sx),
                            int(HEIGHT//2 - t.get_height()//2 + sy)))
        if self.sub_label:
            t2 = kr_font(28).render(self.sub_label, True, (200, 200, 200))
            screen.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 60))


# =============================================================
# 기본 오브젝트
# =============================================================

def random_ball_velocity(speed=None):
    if speed is None:
        speed = BALL_BASE_SPEED
    angle_deg = random.uniform(210, 330)
    angle_rad = math.radians(angle_deg)
    vx = speed * math.cos(angle_rad)
    vy = abs(speed * math.sin(angle_rad))
    return vx, vy


class Ball:
    INVINCIBLE_FRAMES = 30

    def __init__(self):
        self.x = float(WIDTH // 2)
        self.y = float(HEIGHT // 2)
        self.vx, self.vy = random_ball_velocity()
        self.radius    = 12
        self.invincible = 0

    def draw(self, screen):
        if self.invincible > 0:
            if (self.invincible // 4) % 2 == 0:
                return
        pygame.draw.circle(screen, (255, 255, 255),
                           (int(self.x), int(self.y)), self.radius)


class FakeBall:
    def __init__(self):
        self.x      = float(WIDTH // 2)
        self.y      = float(HEIGHT // 2 - 50)
        self.vx, self.vy = random_ball_velocity(BALL_BASE_SPEED * 0.9)
        self.radius = 12

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 120, 200),
                           (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (255, 200, 230),
                           (int(self.x), int(self.y)), self.radius, 2)


class Paddle:
    BASE_SPEED = 10

    def __init__(self):
        self.width  = 160
        self.height = 20
        self.x      = WIDTH // 2 - self.width // 2
        self.y      = HEIGHT - 170

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 255, 255),
                         (self.x, self.y, self.width, self.height))


# =============================================================
# PatternBlock  ★ HP = 블럭 수 // 2 (내림)
# =============================================================

class PatternBlock:
    def __init__(self, col, row, pattern, color):
        self.col     = col
        self.row     = row
        self.pattern = pattern
        self.color   = color
        self.blocks  = []
        self.hp      = 0
        self._build_blocks()
        self.max_hp    = self.hp
        self.hit_timer = 0
        self.shake_dx  = 0
        self.shake_dy  = 0
        self.drop_timer = 0

    def _build_blocks(self):
        self.blocks.clear()
        for i in range(len(self.pattern)):
            for j in range(len(self.pattern[0])):
                if self.pattern[i][j] == 1:
                    self.blocks.append((self.col + j, self.row + i))
        # ★ 내림 나누기 (// 2), 최소 1
        self.hp = max(1, len(self.blocks) // 2)

    def move_down_logic(self):
        self.row += 1
        self._build_blocks()

    def pixel_y_offset(self):
        return slide_offset(self.drop_timer, WAIT_FRAMES, SLIDE_FRAMES)

    def take_hit(self):
        self.hit_timer = 12
        self.shake_dx, self.shake_dy = random.choice(
            [(3,0),(-3,0),(0,3),(0,-3)])

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
            pygame.draw.rect(screen, color,
                             (int(x), int(y), GRID_SIZE, GRID_SIZE))


# =============================================================
# WaveManager
# =============================================================

class WaveManager:
    def __init__(self, base_patterns, pattern_colors):
        self.hole_colors = [
            (180, 180, 180),
            (120, 120, 120),
            (200, 200, 255),
            (255, 200, 200),
            (200, 255, 200),
            (255, 255, 180),
        ]
        self.base_patterns  = base_patterns
        self.pattern_colors = pattern_colors
        self.all_blocks     = []
        self.drop_timer     = 0
        self.next_wave_row  = -3
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

    def split_holes(self, holes):
        visited = set()
        groups  = []
        for h in holes:
            if h in visited:
                continue
            stack = [h]
            group = []
            while stack:
                x, y = stack.pop()
                if (x, y) in visited:
                    continue
                visited.add((x, y))
                group.append((x, y))
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nx, ny = x+dx, y+dy
                    if (nx, ny) in holes and (nx, ny) not in visited:
                        stack.append((nx, ny))
            groups.append(group)
        return groups

    def _spawn_one_group(self, col, row):
        base    = random.choice(self.base_patterns)
        pattern = base
        for _ in range(random.randint(0, 3)):
            pattern = self._rotate(pattern)
        index = self.base_patterns.index(base)
        color = self.pattern_colors[index]
        self.all_blocks.append(PatternBlock(col, row, pattern, color))

        filled = {(j,i) for i in range(len(pattern))
                  for j in range(len(pattern[0])) if pattern[i][j]==1}
        holes  = [(i,j) for i in range(3)
                  for j in range(3) if (i,j) not in filled]
        hole_color = random.choice(self.hole_colors)
        for group in self.split_holes(holes):
            hp_pat = [[0]*3 for _ in range(3)]
            for (x,y) in group:
                hp_pat[y][x] = 1
            self.all_blocks.append(
                PatternBlock(col, row, hp_pat, hole_color))

    @staticmethod
    def _rotate(pattern):
        return [list(row) for row in zip(*pattern[::-1])]


# =============================================================
# 보스 공통
# =============================================================

class BossDropMixin:
    def _init_drop(self, base_py):
        self._drop_timer = 0
        self._base_py    = float(base_py)

    def _drop_update(self):
        self._drop_timer += 1
        if self._drop_timer >= BOSS_DROP_CYCLE:
            self._drop_timer = 0
            self._base_py   += GRID_SIZE
            self._on_drop_logic()

    def _current_py(self):
        return self._base_py + slide_offset(
            self._drop_timer, BOSS_WAIT_FRAMES, BOSS_SLIDE_FRAMES)

    def _on_drop_logic(self):
        pass


class BossEntrance:
    ENTRANCE_FRAMES = 90

    def __init__(self):
        self.active   = False
        self.timer    = 0
        self.start_py = 0.0
        self.end_py   = 0.0
        self.offset   = 0.0

    def begin(self, start_py, end_py):
        self.active   = True; self.timer = 0
        self.start_py = float(start_py)
        self.end_py   = float(end_py)
        self.offset   = self.start_py

    def update(self):
        if not self.active:
            return
        self.timer += 1
        t = min(1.0, self.timer / self.ENTRANCE_FRAMES)
        t = 1.0 - (1.0 - t) ** 3
        self.offset = self.start_py + (self.end_py - self.start_py) * t
        if self.timer >= self.ENTRANCE_FRAMES:
            self.active = False
            self.offset = self.end_py


# =============================================================
# ★ Boss1 → 챕터1: 분열 보스  (체력 3, 전체 27)
# =============================================================

class SplitBlock:
    SIZE_COLORS       = {4:(255,220,0), 2:(255,180,30), 1:(255,140,60)}
    # size4(3) + size2×4(8) + size1×16(16) = 27
    SIZE_HP           = {4:3, 2:2, 1:1}
    INVINCIBLE_FRAMES = 60

    def __init__(self, px, py, size, drop_timer_ref=None):
        self.px       = float(round(px / GRID_SIZE) * GRID_SIZE)
        _py           = float(round(py / GRID_SIZE) * GRID_SIZE)
        self.py       = _py
        self._base_py = _py
        self.size     = size
        self.px_size  = size * GRID_SIZE
        self.max_hp   = self.SIZE_HP[size]; self.hp = self.max_hp
        self.hit_timer = 0
        self.invincible_timer = self.INVINCIBLE_FRAMES
        self.alive = True
        self.color = self.SIZE_COLORS.get(size, (200,200,0))
        self.drop_timer = drop_timer_ref if drop_timer_ref is not None else 0

    @property
    def rect(self):
        oy = slide_offset(self.drop_timer, BOSS_WAIT_FRAMES, BOSS_SLIDE_FRAMES)
        return pygame.Rect(int(self.px), int(self._base_py + oy),
                           self.px_size, self.px_size)

    def take_hit(self):
        if self.invincible_timer > 0: return
        self.hit_timer = 12; self.hp -= 1
        if self.hp <= 0: self.alive = False

    def draw(self, screen):
        if not self.alive: return
        r = self.rect
        if self.invincible_timer > 0:
            color = (255,255,255) if (self.invincible_timer//5)%2==0 else self.color
        elif self.hit_timer > 0:
            color = (255,255,255)
        else:
            color = self.color
        pygame.draw.rect(screen, color, r)
        pygame.draw.rect(screen, (40,40,40), r, 2)


class Boss1(BossDropMixin):
    """챕터1 — 분열 보스"""
    NAME         = "BOSS 1"
    DISPLAY_NAME = "분열 보스"
    # size4(3) + size2×4(8) + size1×16(16) = 27
    MAX_TOTAL_HP = 27

    def __init__(self):
        start_px = (COLS//2 - 2) * GRID_SIZE
        start_py = GRID_SIZE * -4
        self._init_drop(start_py)
        self.entrance = BossEntrance()
        self.entrance.begin(start_py, 0.0)
        self._entering = True
        b = SplitBlock(start_px, start_py, 4, drop_timer_ref=0)
        b.invincible_timer = 0
        self.blocks = [b]
        self._split_count       = 0
        self._perm_debuff_added = False
        self._debuff_phase_triggered = False  # 체력 절반 디버프 (보스1은 미사용, 호환성용)

    @property
    def is_dead(self):
        return not self.blocks or all(not b.alive for b in self.blocks)

    @property
    def total_hp(self):
        alive_hp = sum(b.hp for b in self.blocks if b.alive)
        potential = 0
        if self._split_count == 0:
            potential = 8 + 16
        elif self._split_count == 1:
            size2_alive = sum(1 for b in self.blocks if b.alive and b.size == 2)
            potential = size2_alive * 4
        return alive_hp + potential

    @property
    def max_total_hp(self):
        return self.MAX_TOTAL_HP

    @property
    def split_count(self):
        return self._split_count

    def pop_perm_debuff_request(self):
        # 챕터1 보스에서는 사용 안 함 (호환성 유지)
        return False

    @property
    def debuff_phase_should_trigger(self):
        return False  # 챕터1 분열 보스는 디버프 없음

    def all_rects(self):
        if self._entering: return []
        return [(b.rect, b) for b in self.blocks
                if b.alive and b.invincible_timer == 0]

    def update(self):
        if self._entering:
            self.entrance.update()
            for b in self.blocks: b._base_py = self.entrance.offset
            if not self.entrance.active:
                self._entering = False
                self._base_py = 0.0; self._drop_timer = 0
                for b in self.blocks: b._base_py = 0.0
            return
        self._drop_update()
        to_split = []
        for b in self.blocks:
            b.drop_timer = self._drop_timer
            if b.invincible_timer > 0: b.invincible_timer -= 1
            if b.hit_timer > 0: b.hit_timer -= 1
            if not b.alive and b.size > 1: to_split.append(b)
        for b in to_split:
            self.blocks.remove(b)
            self._split(b)
            self._split_count += 1
        self.blocks = [b for b in self.blocks
                       if b.alive or (not b.alive and b.invincible_timer > 0)]

    def _on_drop_logic(self):
        for b in self.blocks: b._base_py += GRID_SIZE

    def _split(self, parent):
        if parent.size == 4:
            unit     = 2 * GRID_SIZE
            occupied = set()
            for b in self.blocks:
                if b.alive or b.invincible_timer > 0:
                    gx = round(b.px / unit)
                    gy = round(b._base_py / unit)
                    for di in range(b.size // 2):
                        for dj in range(b.size // 2):
                            occupied.add((gx + dj, gy + di))
            pcx = round(parent.px / unit)
            pcy = round(parent._base_py / unit)
            candidates = []
            for dr in range(-3, 4):
                for dc in range(-3, 4):
                    gx = pcx + dc
                    gy = pcy + dr
                    nx = gx * unit
                    ny = gy * unit
                    if nx < 0 or nx + unit > WIDTH: continue
                    if ny < 0 or ny + unit > (PLAY_ROWS - 2) * GRID_SIZE: continue
                    if (gx, gy) in occupied: continue
                    candidates.append((gx, gy, nx, ny))
            random.shuffle(candidates)
            placed = 0
            for (gx, gy, nx, ny) in candidates:
                if placed >= 4: break
                if (gx, gy) in occupied: continue
                nb = SplitBlock(nx, ny, 2, self._drop_timer)
                self.blocks.append(nb)
                occupied.add((gx, gy))
                placed += 1

        elif parent.size == 2:
            unit     = GRID_SIZE
            occupied = set()
            for b in self.blocks:
                if b.alive or b.invincible_timer > 0:
                    gx = round(b.px / unit)
                    gy = round(b._base_py / unit)
                    for di in range(b.size):
                        for dj in range(b.size):
                            occupied.add((gx + dj, gy + di))
            pcx = round(parent.px / unit)
            pcy = round(parent._base_py / unit)
            candidates = []
            for dr in range(-4, 5):
                for dc in range(-4, 5):
                    gx = pcx + dc
                    gy = pcy + dr
                    nx = gx * unit
                    ny = gy * unit
                    if nx < 0 or nx + unit > WIDTH: continue
                    if ny < 0 or ny + unit > (PLAY_ROWS - 1) * GRID_SIZE: continue
                    if (gx, gy) in occupied: continue
                    candidates.append((gx, gy, nx, ny))
            random.shuffle(candidates)
            placed = 0
            for (gx, gy, nx, ny) in candidates:
                if placed >= 4: break
                if (gx, gy) in occupied: continue
                nb = SplitBlock(nx, ny, 1, self._drop_timer)
                self.blocks.append(nb)
                occupied.add((gx, gy))
                placed += 1

    def take_hit(self, block): block.take_hit()

    def draw(self, screen):
        for b in self.blocks: b.draw(screen)

    def is_gameover(self):
        if self._entering: return False
        for b in self.blocks:
            if b.alive and b.rect.bottom >= PLAY_ROWS * GRID_SIZE:
                return True
        return False


# =============================================================
# Boss 2 — 궤도 보스 (챕터2, 변경 없음)
# =============================================================

class ShieldOrb:
    def __init__(self, cx, cy, color, hp=2):
        self.cx = float(cx); self.cy = float(cy)
        self.color = color; self.hp = hp; self.max_hp = hp
        self.hit_timer = 0; self.alive = True

    @property
    def rect(self):
        hs = GRID_SIZE // 2
        return pygame.Rect(int(self.cx)-hs, int(self.cy)-hs,
                           GRID_SIZE, GRID_SIZE)

    def take_hit(self):
        self.hit_timer = 12; self.hp -= 1
        if self.hp <= 0: self.alive = False

    def draw(self, screen):
        if not self.alive: return
        color = (255,255,255) if self.hit_timer > 0 else self.color
        pygame.draw.rect(screen, color, self.rect)


class Boss2Core:
    COLOR  = (255,220,0)
    MAX_HP = 4

    def __init__(self, cx, cy):
        self.cx = float(cx); self.cy = float(cy)
        self.hp = self.MAX_HP; self.max_hp = self.MAX_HP
        self.hit_timer = 0; self.alive = True
        hs = GRID_SIZE // 2
        self.offsets = [(-hs,-hs),(hs,-hs),(-hs,hs),(hs,hs)]

    def rects(self):
        return [pygame.Rect(int(self.cx+ox)-GRID_SIZE//2,
                            int(self.cy+oy)-GRID_SIZE//2,
                            GRID_SIZE, GRID_SIZE)
                for (ox,oy) in self.offsets]

    def take_hit(self):
        self.hit_timer = 12; self.hp -= 1
        if self.hp <= 0: self.alive = False

    def update_pos(self, cx, cy):
        self.cx = cx; self.cy = cy

    def draw(self, screen):
        if not self.alive: return
        color = (255,255,255) if self.hit_timer > 0 else self.COLOR
        for rect in self.rects():
            pygame.draw.rect(screen, color, rect)


class Boss2(BossDropMixin):
    NAME        = "BOSS 2"
    DISPLAY_NAME = "궤도 보스"
    INNER_COLOR = (80,200,255)
    OUTER_COLOR = (255,120,80)
    INNER_R     = GRID_SIZE * 1.5
    OUTER_R     = GRID_SIZE * 2.8

    def __init__(self):
        self.cx = float(WIDTH // 2)
        self.cy = float(GRID_SIZE * -4)
        self._init_drop(self.cy)
        self.entrance = BossEntrance()
        self.entrance.begin(GRID_SIZE * -4, GRID_SIZE * 2.0)
        self._entering   = True
        self.move_dir    = 1
        self.move_speed  = 1.5
        self.inner_angle = 0.0; self.outer_angle = 0.0
        self.inner_speed = 0.022; self.outer_speed = 0.015
        self.core = Boss2Core(self.cx, self.cy)
        self._build_shields()
        self._debuff_phase_triggered = False

    def _build_shields(self):
        self.inner_orbs = []
        for i in range(4):
            a = math.pi/2*i
            self.inner_orbs.append(ShieldOrb(
                self.cx + self.INNER_R*math.cos(a),
                self.cy + self.INNER_R*math.sin(a),
                self.INNER_COLOR, hp=2))
        self.outer_orbs = []
        for i in range(4):
            a = math.pi/2*i; p = a + math.pi/2
            for delta in [-1,1]:
                self.outer_orbs.append(ShieldOrb(
                    self.cx + self.OUTER_R*math.cos(a) + GRID_SIZE*0.6*delta*math.cos(p),
                    self.cy + self.OUTER_R*math.sin(a) + GRID_SIZE*0.6*delta*math.sin(p),
                    self.OUTER_COLOR, hp=2))

    def _get_cy(self):
        return self.entrance.offset if self._entering else self._current_py()

    def _update_orb_positions(self):
        for i,orb in enumerate(self.inner_orbs):
            a = math.pi/2*i + self.inner_angle
            orb.cx = self.cx + self.INNER_R*math.cos(a)
            orb.cy = self.cy + self.INNER_R*math.sin(a)
        for i in range(4):
            a = math.pi/2*i + self.outer_angle; p = a + math.pi/2
            for j,delta in enumerate([-1,1]):
                idx = i*2+j
                self.outer_orbs[idx].cx = (self.cx + self.OUTER_R*math.cos(a)
                                           + GRID_SIZE*0.6*delta*math.cos(p))
                self.outer_orbs[idx].cy = (self.cy + self.OUTER_R*math.sin(a)
                                           + GRID_SIZE*0.6*delta*math.sin(p))

    def _on_drop_logic(self): pass

    @property
    def is_dead(self): return not self.core.alive
    @property
    def total_hp(self): return self.core.hp
    @property
    def max_total_hp(self): return self.core.MAX_HP

    @property
    def debuff_phase_should_trigger(self):
        if not self._debuff_phase_triggered and self.core.hp <= 2:
            self._debuff_phase_triggered = True
            return True
        return False

    def all_rects(self):
        if self._entering: return []
        result = []
        for orb in self.inner_orbs:
            if orb.alive: result.append((orb.rect, orb))
        for orb in self.outer_orbs:
            if orb.alive: result.append((orb.rect, orb))
        if self.core.alive:
            for rect in self.core.rects(): result.append((rect, self.core))
        return result

    def update(self):
        self.inner_angle -= self.inner_speed
        self.outer_angle += self.outer_speed
        if self._entering:
            self.entrance.update()
            if not self.entrance.active:
                self._entering = False
                self._base_py = GRID_SIZE*2.0; self._drop_timer = 0
        else:
            self.cx += self.move_speed * self.move_dir
            max_reach = self.OUTER_R + GRID_SIZE
            if self.cx + max_reach >= WIDTH - GRID_SIZE:
                self.move_dir = -1; self.cx = WIDTH - GRID_SIZE - max_reach
            if self.cx - max_reach <= GRID_SIZE:
                self.move_dir = 1; self.cx = GRID_SIZE + max_reach
            self._drop_update()
        self.cy = self._get_cy()
        self._update_orb_positions()
        self.core.update_pos(self.cx, self.cy)
        for orb in self.inner_orbs + self.outer_orbs:
            if orb.hit_timer > 0: orb.hit_timer -= 1
        if self.core.hit_timer > 0: self.core.hit_timer -= 1

    def take_hit(self, piece):
        if isinstance(piece, (ShieldOrb, Boss2Core)): piece.take_hit()

    def draw(self, screen):
        for orb in self.outer_orbs: orb.draw(screen)
        for orb in self.inner_orbs: orb.draw(screen)
        self.core.draw(screen)

    def is_gameover(self):
        if self._entering: return False
        return self.cy + self.OUTER_R >= PLAY_ROWS * GRID_SIZE


# =============================================================
# ★ Boss3 → 챕터3: 갑옷 보스  (원래 Boss1이었던 것)
# =============================================================

class ArmorPiece:
    def __init__(self, cells, color, hp=2):
        self.cells       = cells
        self.abs_cells   = []
        self.color       = color
        self.hp          = hp
        self.max_hp      = hp
        self.hit_timer   = 0
        self.shake_dx    = 0
        self.shake_dy    = 0
        self.alive       = True
        self.regen_timer = 0
        self.REGEN_TOTAL  = 600
        self.REGEN_HIDDEN = 420

    def update_abs(self, ax, ay):
        self.abs_cells = [
            pygame.Rect(int(ax+dc*GRID_SIZE), int(ay+dr*GRID_SIZE),
                        GRID_SIZE, GRID_SIZE)
            for (dc,dr) in self.cells
        ]

    def take_hit(self):
        if not self.alive: return
        self.hit_timer = 12
        self.shake_dx, self.shake_dy = random.choice(
            [(3,0),(-3,0),(0,3),(0,-3)])

    def start_regen(self):
        self.regen_timer = self.REGEN_TOTAL

    def update(self):
        if self.hit_timer > 0: self.hit_timer -= 1
        if self.regen_timer > 0:
            self.regen_timer -= 1
            if self.regen_timer == 0:
                self.alive = True
                self.hp    = self.max_hp

    def draw(self, screen):
        if not self.alive:
            if self.regen_timer <= 0: return
            elapsed = self.REGEN_TOTAL - self.regen_timer
            if elapsed < self.REGEN_HIDDEN: return
            if not (pygame.time.get_ticks()//200)%2==0: return
            for rect in self.abs_cells:
                s = pygame.Surface((GRID_SIZE,GRID_SIZE), pygame.SRCALPHA)
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


class Boss3(BossDropMixin):
    """챕터3 — 갑옷 보스  (챕터1에 있던 갑옷 보스를 챕터3으로 이동)"""
    NAME         = "BOSS 3"
    DISPLAY_NAME = "갑옷 보스"
    ARMOR_COLORS = [(200,80,80),(80,200,80),(80,80,200),(200,200,80)]
    CORE_COLOR   = (255,220,0)
    CORE_MAX_HP  = 4

    def __init__(self):
        self.anchor_col = COLS//2 - 2
        self.anchor_row = -4
        self._init_drop(self.anchor_row * GRID_SIZE)
        self.entrance = BossEntrance()
        self.entrance.begin(self.anchor_row * GRID_SIZE, 0.0)
        self._entering = True
        armor_cells = [
            [(0,0),(1,0),(0,1)], [(2,0),(3,0),(3,1)],
            [(0,2),(0,3),(1,3)], [(3,2),(2,3),(3,3)],
        ]
        self.armors = [ArmorPiece(cells, self.ARMOR_COLORS[i], hp=2)
                       for i,cells in enumerate(armor_cells)]
        self.core = ArmorPiece([(1,1),(2,1),(1,2),(2,2)], self.CORE_COLOR,
                               hp=self.CORE_MAX_HP)
        self._refresh_abs()
        self._debuff_phase_triggered = False

    def _get_ay(self):
        return self.entrance.offset if self._entering else self._current_py()

    def _refresh_abs(self):
        ax = self.anchor_col * GRID_SIZE; ay = self._get_ay()
        for a in self.armors: a.update_abs(ax, ay)
        self.core.update_abs(ax, ay)

    def _on_drop_logic(self): self.anchor_row += 1

    @property
    def is_dead(self): return not self.core.alive
    @property
    def total_hp(self): return self.core.hp
    @property
    def max_total_hp(self): return self.CORE_MAX_HP

    @property
    def debuff_phase_should_trigger(self):
        """체력 2 이하 → 디버프 인터벌 발동 (최초 1회)"""
        if not self._debuff_phase_triggered and self.core.hp <= 2:
            self._debuff_phase_triggered = True
            return True
        return False

    # 호환성용 (분열 보스에서 쓰는 메서드)
    def pop_perm_debuff_request(self):
        return False

    def all_rects(self):
        if self._entering: return []
        result = []
        for a in self.armors:
            if a.alive:
                for rect in a.abs_cells: result.append((rect, a))
        if self.core.alive:
            for rect in self.core.abs_cells: result.append((rect, self.core))
        return result

    def update(self):
        if self._entering:
            self.entrance.update()
            if not self.entrance.active:
                self._entering = False
                self._base_py = 0.0; self._drop_timer = 0
        else:
            self._drop_update()
        self._refresh_abs()
        for a in self.armors: a.update()
        self.core.update()

    def take_hit(self, piece):
        if not piece.alive: return
        piece.take_hit(); piece.hp -= 1
        if piece.hp <= 0:
            piece.alive = False
            if piece is not self.core: piece.start_regen()

    def draw(self, screen):
        for a in self.armors: a.draw(screen)
        self.core.draw(screen)

    def is_gameover(self):
        if self._entering: return False
        return self._get_ay() + 4*GRID_SIZE >= PLAY_ROWS * GRID_SIZE


# =============================================================
# UI 헬퍼
# =============================================================

def draw_boss_hp_bar(screen, boss):
    bx = WIDTH-220; by = 15; bw = 200; bh = 22
    font = kr_font(18)
    screen.blit(font.render(getattr(boss,'NAME','BOSS'), True, (255,200,100)),
                (bx, by-22))
    total    = getattr(boss,'total_hp',0)
    maxtotal = getattr(boss,'max_total_hp',1)
    ratio = max(0.0, min(1.0, total/maxtotal)) if maxtotal > 0 else 0.0
    pygame.draw.rect(screen,(60,60,60),   (bx,by,bw,bh))
    pygame.draw.rect(screen,(220,60,60),  (bx,by,int(bw*ratio),bh))
    pygame.draw.rect(screen,(200,200,200),(bx,by,bw,bh),2)
    hp_txt = font.render(f"{total} / {maxtotal}", True, (255,255,255))
    screen.blit(hp_txt, (bx+bw//2-hp_txt.get_width()//2, by+3))


def draw_remember_gauge(screen, gauge, gauge_max, scale=1.0):
    ratio    = max(0.0, min(1.0, gauge/gauge_max))
    font_big = kr_font(int(60*scale))
    base_txt = font_big.render("REMEMBER", True, (100,100,100))
    ux = WIDTH//2 - base_txt.get_width()//2
    uy = HEIGHT - 100
    screen.blit(base_txt, (ux, uy))
    if ratio < 0.5:
        fill_color = (255, 220, 0)
    elif ratio < 1.0:
        t = (ratio-0.5)/0.5
        fill_color = (255, int(220*(1-t)+80*t), 0)
    else:
        fill_color = (255, 60, 60)
    fill_txt = font_big.render("REMEMBER", True, fill_color)
    fill_w = int(base_txt.get_width() * ratio)
    if fill_w > 0:
        screen.blit(fill_txt, (ux, uy),
                    pygame.Rect(0, 0, fill_w, base_txt.get_height()))


def draw_lives(screen, lives, max_lives=3):
    fail_y  = PLAY_ROWS * GRID_SIZE
    x_start = WIDTH - 16; size = 18; gap = 6
    for i in range(max_lives):
        x = x_start - (i+1)*(size+gap)
        color = (255,80,80) if i < lives else (60,60,60)
        pygame.draw.rect(screen, color,        (x, fail_y+6, size, size))
        pygame.draw.rect(screen, (200,200,200),(x, fail_y+6, size, size), 1)


def draw_debuff_indicators(screen, debuff_mgr: DebuffManager):
    all_d = debuff_mgr.all_active
    if not all_d:
        return
    fail_y = PLAY_ROWS * GRID_SIZE
    r      = 11
    gap    = 10
    base_x = 16 + r
    cy     = fail_y + 6 + r
    for i, d in enumerate(all_d):
        cx    = base_x + i*(r*2+gap)
        color = DEBUFF_COLORS.get(d.kind, (200,200,200))
        if d.blinking:
            if not (pygame.time.get_ticks()//120)%2==0:
                continue
        pygame.draw.circle(screen, color,       (cx, cy), r)
        pygame.draw.circle(screen, (255,255,255),(cx, cy), r, 2)
        if isinstance(d, PermanentDebuff):
            pygame.draw.circle(screen, (255,255,255),(cx, cy), 3)


# =============================================================
# FakeBall 물리
# =============================================================

def update_fake_ball(fb: FakeBall, pattern_blocks):
    r     = fb.radius
    speed = max(abs(fb.vx), abs(fb.vy))
    steps = int(speed) + 1
    dx = fb.vx / steps; dy = fb.vy / steps
    for _ in range(steps):
        fb.x += dx; fb.y += dy
        if fb.x-r <= 0:
            fb.vx = abs(fb.vx); fb.x = r+1
        elif fb.x+r >= WIDTH:
            fb.vx = -abs(fb.vx); fb.x = WIDTH-r-1
        if fb.y-r <= 0:
            fb.vy = abs(fb.vy); fb.y = r+1
        if fb.y+r >= HEIGHT:
            fb.vy = -abs(fb.vy); fb.y = HEIGHT-r-1
        ball_rect = pygame.Rect(fb.x-r, fb.y-r, r*2, r*2)
        bc = int(fb.x)//GRID_SIZE; br = int(fb.y)//GRID_SIZE
        hit = False
        for pb in pattern_blocks:
            if hit: break
            for (c, rr) in pb.blocks:
                if abs(c-bc)<=1 and abs(rr-br)<=1:
                    cr = pygame.Rect(c*GRID_SIZE, rr*GRID_SIZE,
                                     GRID_SIZE, GRID_SIZE)
                    if ball_rect.colliderect(cr):
                        fb.vy = -fb.vy; fb.y += fb.vy*2
                        hit = True; break


# =============================================================
# AI 모드 컨트롤러
# =============================================================

class AIController:
    """
    G키로 토글하는 오토 모드.

    두 가지 역할을 동시에 수행:

    [수비] 공이 내려올 때 낙하 지점을 벽 반사까지 시뮬레이션하여 예측.
           패들이 그 지점에 정확히 위치해 절대 공을 놓치지 않는다.

    [공격] 공을 받는 순간의 패들 위치가 반사각을 결정하므로,
           아웃라인(PLAY_ROWS)에 가장 가까운 '위험 블럭'의 x 중앙을
           목표로 설정하여 조준한 뒤 공을 맞는다.
           - 일반 PLAY 상태: PatternBlock 중 row가 가장 큰 블럭
           - BOSS 상태: 보스의 가장 아래쪽 히트박스

    패들 이동은 실제 물리 패들 이동으로 처리 (순간이동 없음).
    공 속도보다 항상 빠른 속도로 이동해 절대 놓치지 않음을 보장.
    """

    # 수비 우선인지 공격 우선인지 판단하는 y 임계값
    # 공이 패들 y의 이 비율 이상 내려오면 수비 모드
    DEFENSE_THRESHOLD = 0.55   # 화면 세로의 55% 아래면 수비 우선

    def __init__(self):
        self.enabled       = False
        self._target_x     = None   # 최종 패들 목표 x (패들 왼쪽 기준)
        self._attack_x     = None   # 공격 조준 x (공이 위로 갈 때 계산)

    def toggle(self):
        self.enabled = not self.enabled

    # ── 공의 낙하 지점 예측 (벽 반사 포함) ──
    @staticmethod
    def _predict_landing(ball: Ball, paddle: Paddle) -> float:
        """
        현재 공의 위치·속도로 패들 y에 닿을 때의 x를 계산.
        벽 반사를 정확히 시뮬레이션한다.
        """
        if ball.vy <= 0:
            # 올라가는 중 → 천장 반사 후 내려오는 지점 계산
            # 천장까지 거리
            t_ceil  = ball.y / max(abs(ball.vy), 0.001)
            x_ceil  = ball.x + ball.vx * t_ceil
            y_after = 0.0
            vx_after = ball.vx
            vy_after = abs(ball.vy)   # 반사 후 아래 방향
        else:
            x_ceil   = ball.x
            y_after  = ball.y
            vx_after = ball.vx
            vy_after = ball.vy

        # 패들 y까지 내려오는 시뮬레이션 (벽 반사만 처리, 블럭 무시)
        target_y = paddle.y
        x        = x_ceil
        vx       = vx_after
        remaining_y = target_y - y_after

        if remaining_y <= 0:
            remaining_y = target_y - ball.y
            x           = ball.x
            vx          = ball.vx

        while remaining_y > 0:
            if vx == 0:
                break
            # 다음 벽까지 x 거리
            if vx > 0:
                dx_to_wall = (WIDTH - ball.radius) - x
            else:
                dx_to_wall = x - ball.radius

            # 그 거리에 도달할 때 y 이동량
            dy_for_wall = abs(dx_to_wall / vx) * abs(vy_after)

            if dy_for_wall >= remaining_y:
                # 패들에 먼저 닿음
                fraction = remaining_y / max(dy_for_wall, 0.001)
                x += vx * abs(remaining_y / max(abs(vy_after), 0.001))
                remaining_y = 0
            else:
                # 벽에 먼저 닿음 → 반사
                x = WIDTH - ball.radius if vx > 0 else ball.radius
                vx = -vx
                remaining_y -= dy_for_wall

        # 화면 안으로 클램프
        x = max(ball.radius, min(WIDTH - ball.radius, x))
        return float(x)

    # ── 위험 블럭 선정 ──
    @staticmethod
    def _find_danger_target(game_state) -> float | None:
        """
        PLAY: PatternBlock 중 가장 아래쪽(row 최대) 블럭의 x 중앙.
        BOSS: 보스의 all_rects() 중 가장 아래쪽 rect의 x 중앙.
        없으면 None.
        """
        state = game_state.get('state')
        if state == 'PLAY':
            blocks = game_state.get('pattern_blocks', [])
            if not blocks:
                return None
            # 아웃라인에 가장 가까운 블럭 = row가 가장 큰 셀
            best_row = -999
            best_cx  = None
            for pb in blocks:
                oy = pb.pixel_y_offset()
                for (c, r) in pb.blocks:
                    actual_r = r * GRID_SIZE + oy
                    if actual_r > best_row:
                        best_row = actual_r
                        best_cx  = c * GRID_SIZE + GRID_SIZE // 2
            return float(best_cx) if best_cx is not None else None

        elif state == 'BOSS':
            boss = game_state.get('boss')
            if boss is None:
                return None
            rects_pieces = boss.all_rects()
            if not rects_pieces:
                return None
            # 가장 아래쪽 rect
            best_bottom = -1
            best_cx     = None
            for (rect, _) in rects_pieces:
                if rect.bottom > best_bottom:
                    best_bottom = rect.bottom
                    best_cx     = rect.centerx
            return float(best_cx) if best_cx is not None else None

        return None

    # ── 패들을 목표 x로 빠르게 이동 (절대 놓치지 않는 속도) ──
    @staticmethod
    def _move_paddle(paddle: Paddle, target_center_x: float):
        """
        목표 x(패들 중앙 기준)로 패들을 이동.
        속도는 공보다 항상 빠름 (BALL_BASE_SPEED * 2 이상).
        """
        target_left = target_center_x - paddle.width // 2
        target_left = max(0.0, min(float(WIDTH - paddle.width), target_left))
        diff = target_left - paddle.x
        # 남은 거리만큼 한 번에 이동 (순간이동이 아닌 물리적 이동이지만
        # 공보다 빠르게 설정해 절대 놓치지 않도록 보장)
        max_step = max(BALL_BASE_SPEED * 2.5, abs(diff))
        step = min(abs(diff), max_step)
        if diff > 0:
            paddle.x += step
        elif diff < 0:
            paddle.x -= step
        paddle.x = max(0, min(WIDTH - paddle.width, paddle.x))

    # ── 메인 업데이트 ──
    def update(self, paddle: Paddle, ball: Ball, game_state: dict):
        if not self.enabled:
            return

        pred_x   = self._predict_landing(ball, paddle)
        danger_x = self._find_danger_target(game_state)

        if ball.vy > 0:
            # 공이 내려오고 있음 → 수비 + 조준 혼합
            # 공이 화면 아래쪽에 있을수록 수비(낙하지점)에 비중을 더 높임
            defense_ratio = min(1.0,
                max(0.0, (ball.y - HEIGHT * 0.3) / (HEIGHT * 0.4)))

            if danger_x is not None and defense_ratio < 0.9:
                # 공격 조준: 목표 블럭을 향해 공을 보내기 위한 패들 x 계산
                # 패들에서 목표 블럭까지의 오프셋 → offset=(target-paddle_center)/paddle_half
                # 반사각 공식 역산: paddle_center = target_block_x (단순 근사)
                aim_center = danger_x
                # 수비/공격 비율로 혼합
                final_center = (pred_x * defense_ratio
                                + aim_center * (1.0 - defense_ratio))
            else:
                # 수비 전담: 낙하 지점으로 패들 이동
                final_center = pred_x

            self._move_paddle(paddle, final_center)

        else:
            # 공이 올라가고 있음 → 다음 공격 준비
            # 여유롭게 위험 블럭 쪽으로 조금씩 이동
            if danger_x is not None:
                self._move_paddle(paddle, danger_x)
            else:
                # 타겟 없으면 중앙 대기
                self._move_paddle(paddle, WIDTH / 2)


# =============================================================
# GameManager
# =============================================================

class GameManager:
    MAX_LIVES = 3

    def __init__(self, from_restart=False):
        self.state              = "PLAY_INTRO" if from_restart else "LOBBY"
        self.boss               = None
        self.remember_gauge     = 0
        self.remember_max       = 20
        self.chapter            = 1
        self.max_chapter        = 3
        self.ball               = Ball()
        self.paddle             = Paddle()
        self.lives              = self.MAX_LIVES
        self.gauge_scale        = 1.0
        self.gauge_scale_target = 1.0
        self.fade               = FadeOverlay()
        self.fake_ball          = None
        self.debuff_popup       = DebuffPopup()
        self.ai                 = AIController()

        self.debuff_mgr = DebuffManager(self.chapter, mode="none")

        self.base_patterns = [
            [[1,1,1],[1,0,0],[1,0,0]], [[1,1,1],[0,0,1],[0,0,1]],
            [[1,1,1],[1,1,1],[1,0,0]], [[1,1,0],[0,1,0],[0,1,0]],
            [[1,1,1],[1,0,0],[1,1,1]], [[1,1,0],[1,1,1],[0,0,1]],
            [[1,1,0],[1,0,0],[1,1,0]],
        ]
        self.pattern_colors = [
            (255,80,80),(255,200,80),(80,255,80),
            (80,80,255),(200,80,255),(80,255,255),(255,255,80),
        ]
        self.wave_manager = WaveManager(self.base_patterns, self.pattern_colors)

        if from_restart:
            self.fade.start("게임 시작", on_done=self._on_play_intro_done)

    @property
    def pattern_blocks(self):
        return self.wave_manager.all_blocks

    def _ball_speed_mult(self):
        if self.debuff_mgr.is_active(DEBUFF_SPEED_UP):   return 1.5
        if self.debuff_mgr.is_active(DEBUFF_SPEED_DOWN): return 0.6
        return 1.0

    def handle_input(self):
        # AI 모드일 때는 패들 자동 제어 (키 입력 무시)
        if self.ai.enabled:
            game_state = {
                'state':          self.state,
                'pattern_blocks': self.pattern_blocks,
                'boss':           self.boss,
            }
            self.ai.update(self.paddle, self.ball, game_state)
            return

        keys      = pygame.key.get_pressed()
        reverse   = self.debuff_mgr.is_active(DEBUFF_REVERSE)
        slow      = self.debuff_mgr.is_active(DEBUFF_PADDLE_SLOW)
        speed     = int(Paddle.BASE_SPEED * 0.45) if slow else Paddle.BASE_SPEED
        left_key  = pygame.K_RIGHT if reverse else pygame.K_LEFT
        right_key = pygame.K_LEFT  if reverse else pygame.K_RIGHT
        if keys[left_key]:  self.paddle.x -= speed
        if keys[right_key]: self.paddle.x += speed
        self.paddle.x = max(0, min(WIDTH - self.paddle.width, self.paddle.x))

    def handle_keydown(self, event):
        # ★ 엔터키 통일: 로비 시작 + 게임오버/클리어 재시작
        if event.key == pygame.K_RETURN:
            if self.state == "LOBBY":
                self.state = "PLAY_INTRO"
                self.fade.start("게임 시작", on_done=self._on_play_intro_done)
                return
            if self.state in ("GAMEOVER", "GAMECLEAR"):
                self.__init__(from_restart=True)
                return

        # G키: AI 모드 토글
        if event.key == pygame.K_g:
            self.ai.toggle()
            return

        if event.key == pygame.K_1: self.remember_gauge = self.remember_max
        if event.key == pygame.K_2:
            if self.state == "BOSS" and self.boss: self._kill_boss()

    def _on_play_intro_done(self): self.state = "PLAY"

    def _kill_boss(self):
        if isinstance(self.boss, Boss1):   # 챕터1: 분열 보스
            for b in self.boss.blocks: b.alive=False; b.invincible_timer=0
        elif isinstance(self.boss, Boss2):
            for o in self.boss.inner_orbs+self.boss.outer_orbs: o.alive=False
            self.boss.core.alive = False
        elif isinstance(self.boss, Boss3):  # 챕터3: 갑옷 보스
            for a in self.boss.armors: a.alive=False; a.regen_timer=0
            self.boss.core.alive = False

    def _make_debuff_mgr_for_chapter(self, chapter):
        if chapter == 1:
            return DebuffManager(chapter, mode="none")
        elif chapter == 2:
            return DebuffManager(chapter, mode="interval",
                                 interval_params=(600, 240, 600))
        elif chapter == 3:
            return DebuffManager(chapter, mode="interval",
                                 interval_params=(300, 240, 300))
        return DebuffManager(chapter, mode="none")

    def update(self):
        self.fade.update()
        self.debuff_popup.update()

        if self.state == "LOBBY": return
        if self.state in ("PLAY_INTRO","BOSS_INTRO","BOSS_CLEAR"): return
        if self.state == "GAMEOVER": return

        self.gauge_scale += (self.gauge_scale_target - self.gauge_scale) * 0.12
        if abs(self.gauge_scale - self.gauge_scale_target) < 0.001:
            self.gauge_scale = self.gauge_scale_target

        if self.ball.invincible > 0: self.ball.invincible -= 1

        self.handle_input()
        self.debuff_mgr.update()

        popup_kind = self.debuff_mgr.pop_popup_request()
        if popup_kind:
            self.debuff_popup.show(popup_kind)

        if self.debuff_mgr.pop_fake_ball_request():
            self.fake_ball = FakeBall()
        if self.fake_ball and not self.debuff_mgr.is_active(DEBUFF_FAKE_BALL):
            self.fake_ball = None

        mult       = self._ball_speed_mult()
        target_spd = BALL_BASE_SPEED * mult
        cur_spd    = math.sqrt(self.ball.vx**2 + self.ball.vy**2)
        if cur_spd > 0 and abs(cur_spd - target_spd) > 0.5:
            ratio = target_spd / cur_spd
            self.ball.vx *= ratio
            self.ball.vy *= ratio

        if self.state in ("PLAY","BOSS"):
            ball  = self.ball
            speed = max(abs(ball.vx), abs(ball.vy))
            steps = int(speed)+1
            dx = ball.vx/steps; dy = ball.vy/steps
            for _ in range(steps):
                ball.x += dx; ball.y += dy
                self._check_collision_step()
                if self.state not in ("PLAY","BOSS"): break

            self.check_floor()

            if self.fake_ball:
                update_fake_ball(self.fake_ball, self.pattern_blocks)

            if self.state == "PLAY":
                if self.remember_gauge >= self.remember_max:
                    self.gauge_scale_target = 1.2
                    self._start_boss_intro()
                else:
                    self.wave_manager.update()
                    if self.wave_manager.is_gameover(PLAY_ROWS):
                        self.state = "GAMEOVER"

            if self.state == "BOSS" and self.boss:
                self.boss.update()

                # 챕터2 보스: 체력 절반 이하 시 디버프
                if isinstance(self.boss, Boss2):
                    if self.boss.debuff_phase_should_trigger:
                        self.debuff_mgr.set_mode("interval",
                            interval_params=(0, 300, 300))

                # 챕터3 갑옷 보스: 체력 절반 이하 시 디버프
                if isinstance(self.boss, Boss3):
                    if self.boss.debuff_phase_should_trigger:
                        self.debuff_mgr.set_mode("interval",
                            interval_params=(0, 300, 300))

                if self.boss.is_dead:         self._start_boss_clear()
                elif self.boss.is_gameover(): self.state = "GAMEOVER"

        for pb in self.pattern_blocks:
            if pb.hit_timer > 0: pb.hit_timer -= 1

    def _start_boss_intro(self):
        self.state = "BOSS_INTRO"
        self.fade.start(f"보스 {self.chapter}", on_done=self._on_boss_intro_done)

    def _on_boss_intro_done(self):
        self.wave_manager.all_blocks.clear()
        self.remember_gauge     = self.remember_max
        self.gauge_scale        = 1.2
        self.gauge_scale_target = 1.2

        if self.chapter == 1:
            self.boss = Boss1()          # 분열 보스
            self.debuff_mgr = DebuffManager(self.chapter, mode="none")
        elif self.chapter == 2:
            self.boss = Boss2()          # 궤도 보스
            self.debuff_mgr = DebuffManager(self.chapter, mode="none")
        elif self.chapter == 3:
            self.boss = Boss3()          # 갑옷 보스
            self.debuff_mgr = DebuffManager(self.chapter, mode="none")

        self.state = "BOSS"

    def _start_boss_clear(self):
        self.state = "BOSS_CLEAR"
        self.fade.start(f"보스 {self.chapter} 클리어",
                        on_done=self._on_boss_clear_done)

    def _on_boss_clear_done(self):
        self.boss = None
        self.chapter += 1
        if self.chapter > self.max_chapter:
            self.state = "GAMECLEAR"
        else:
            self.state              = "PLAY"
            self.remember_gauge     = 0
            self.gauge_scale        = 1.0
            self.gauge_scale_target = 1.0
            self.wave_manager       = WaveManager(self.base_patterns,
                                                  self.pattern_colors)
            self.debuff_mgr = self._make_debuff_mgr_for_chapter(self.chapter)

    def _check_collision_step(self):
        ball = self.ball; r = ball.radius
        ball_rect = pygame.Rect(ball.x-r, ball.y-r, r*2, r*2)

        if ball.x-r <= 0:
            ball.vx = abs(ball.vx); ball.x = r+1
        elif ball.x+r >= WIDTH:
            ball.vx = -abs(ball.vx); ball.x = WIDTH-r-1
        if ball.y-r <= 0:
            ball.vy = abs(ball.vy); ball.y = r+1

        if ball.invincible == 0:
            pr = pygame.Rect(self.paddle.x, self.paddle.y,
                             self.paddle.width, self.paddle.height)
            if ball_rect.colliderect(pr) and ball.vy > 0:
                offset   = (ball.x - self.paddle.x) / self.paddle.width
                ball.vx  = (offset-0.5) * 2 * BALL_BASE_SPEED
                ball.vy  = -BALL_BASE_SPEED
                ball.y   = self.paddle.y - r - 1
                return

        if self.state == "BOSS" and self.boss:
            for (rect, piece) in self.boss.all_rects():
                if hasattr(piece,'hit_timer') and piece.hit_timer > 0: continue
                if hasattr(piece,'invincible_timer') and piece.invincible_timer > 0: continue
                if ball_rect.colliderect(rect):
                    self._resolve_rect_collision(rect)
                    self.boss.take_hit(piece)
                    return

        ball_col = int(ball.x)//GRID_SIZE
        ball_row = int(ball.y)//GRID_SIZE
        for pb in list(self.pattern_blocks):
            if pb.hit_timer > 0: continue
            hit_rect = None
            if (ball_col,ball_row) in pb.blocks:
                for (c,rr) in pb.blocks:
                    cr = pygame.Rect(c*GRID_SIZE, rr*GRID_SIZE, GRID_SIZE, GRID_SIZE)
                    if ball_rect.colliderect(cr): hit_rect=cr; break
            else:
                for (c,rr) in pb.blocks:
                    if abs(c-ball_col)<=1 and abs(rr-ball_row)<=1:
                        cr = pygame.Rect(c*GRID_SIZE, rr*GRID_SIZE, GRID_SIZE, GRID_SIZE)
                        if ball_rect.colliderect(cr): hit_rect=cr; break
            if hit_rect is None: continue
            self._resolve_rect_collision(hit_rect)
            pb.hp -= 1; pb.take_hit()
            if pb.hp <= 0:
                self.remember_gauge = min(
                    self.remember_gauge + pb.max_hp, self.remember_max)
                self.wave_manager.remove_block(pb)
            return

    def _resolve_rect_collision(self, rect):
        ball = self.ball; r = ball.radius
        ot   = (ball.y+r)-rect.top;   ob  = rect.bottom-(ball.y-r)
        ol   = (ball.x+r)-rect.left;  or_ = rect.right-(ball.x-r)
        candidates = []
        if ball.vy > 0: candidates.append(('top',    ot))
        if ball.vy < 0: candidates.append(('bottom', ob))
        if ball.vx > 0: candidates.append(('left',   ol))
        if ball.vx < 0: candidates.append(('right',  or_))
        if not candidates: return
        side,_ = min(candidates, key=lambda x:x[1])
        if side=='top':     ball.vy=-abs(ball.vy); ball.y=rect.top-r-1
        elif side=='bottom':ball.vy=abs(ball.vy);  ball.y=rect.bottom+r+1
        elif side=='left':  ball.vx=-abs(ball.vx); ball.x=rect.left-r-1
        elif side=='right': ball.vx=abs(ball.vx);  ball.x=rect.right+r+1

    def check_floor(self):
        ball = self.ball
        if ball.y + ball.radius >= HEIGHT:
            ball.y   = HEIGHT - ball.radius - 1
            ball.vy  = -abs(ball.vy)
            self.lives -= 1
            ball.invincible = Ball.INVINCIBLE_FRAMES
            if self.lives <= 0: self.state = "GAMEOVER"

    # ── 드로우 ──

    def draw(self, screen):
        screen.fill((40,40,40))
        for row in range(PLAY_ROWS):
            for col in range(COLS):
                pygame.draw.rect(screen,(70,70,70),
                                 (col*GRID_SIZE,row*GRID_SIZE,
                                  GRID_SIZE,GRID_SIZE),1)

        if self.state == "LOBBY":
            self._draw_lobby(screen)
            self.fade.draw(screen)
            return

        self.ball.draw(screen)
        self.paddle.draw(screen)
        if self.fake_ball: self.fake_ball.draw(screen)

        if self.state in ("PLAY","PLAY_INTRO"):
            for pb in self.pattern_blocks: pb.draw(screen)

        if self.state in ("BOSS","BOSS_INTRO","BOSS_CLEAR") and self.boss:
            self.boss.draw(screen)
            draw_boss_hp_bar(screen, self.boss)

        self._draw_ui(screen)

        blind_d = next((d for d in self.debuff_mgr.all_active
                        if d.kind == DEBUFF_BLIND), None)
        if blind_d:
            timer = blind_d.timer if isinstance(blind_d, ActiveDebuff) else DEBUFF_DURATION
            blind_overlay.draw(screen, timer)

        self.debuff_popup.draw(screen)

        if self.state == "GAMEOVER":
            self._draw_overlay(screen,"GAME OVER",(255,60,60),"엔터키로 재시작")
        if self.state == "GAMECLEAR":
            self._draw_overlay(screen,"CLEAR!",(60,255,120),"엔터키로 재시작")

        self.fade.draw(screen)

    def _draw_lobby(self, screen):
        screen.fill((20,20,30))
        title = kr_font(60).render("기억의 파편", True, (255,220,60))
        screen.blit(title,(WIDTH//2-title.get_width()//2, HEIGHT//2-60))
        if (pygame.time.get_ticks()//500)%2==0:
            sub = kr_font(28).render("엔터키를 눌러 시작", True, (200,200,200))
            screen.blit(sub,(WIDTH//2-sub.get_width()//2, HEIGHT//2+40))

    def _draw_ui(self, screen):
        font_sm  = kr_font(22)
        ch_names = {1:"CHAPTER 1",2:"CHAPTER 2",3:"CHAPTER 3"}
        ch_surf  = font_sm.render(
            ch_names.get(self.chapter, f"CHAPTER {self.chapter}"),
            True,(255,255,255))
        screen.blit(ch_surf,(15,12))
        if self.state == "PLAY":
            screen.blit(font_sm.render("PLAY",True,(120,255,120)),
                        (15,12+ch_surf.get_height()+4))
        elif self.state == "BOSS":
            screen.blit(font_sm.render("BOSS",True,(255,100,100)),
                        (15,12+ch_surf.get_height()+4))

        # AI 모드 표시
        if self.ai.enabled:
            ai_surf = kr_font(18).render("AI MODE  [G]", True, (80, 255, 200))
            screen.blit(ai_surf, (WIDTH//2 - ai_surf.get_width()//2,
                                  PLAY_ROWS * GRID_SIZE + 30))

        fail_y = PLAY_ROWS * GRID_SIZE
        if (pygame.time.get_ticks()//300)%2==0:
            pygame.draw.line(screen,(255,0,0),(0,fail_y),(WIDTH,fail_y),2)

        draw_lives(screen, self.lives)
        draw_debuff_indicators(screen, self.debuff_mgr)

        if self.state in ("PLAY","BOSS"):
            draw_remember_gauge(screen, self.remember_gauge,
                                self.remember_max, scale=self.gauge_scale)

    def _draw_overlay(self, screen, text, color, sub=""):
        ov = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        ov.fill((0,0,0,140)); screen.blit(ov,(0,0))
        t = kr_font(64).render(text, True, color)
        screen.blit(t,(WIDTH//2-t.get_width()//2, HEIGHT//2-t.get_height()//2))
        if sub:
            t2 = kr_font(26).render(sub, True,(200,200,200))
            screen.blit(t2,(WIDTH//2-t2.get_width()//2, HEIGHT//2+55))


# =============================================================
# Main
# =============================================================

def main():
    pygame.display.set_caption("기억의 파편")
    game = GameManager(from_restart=False)
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                game.handle_keydown(event)
        game.update()
        game.draw(screen)
        pygame.display.flip()

main()