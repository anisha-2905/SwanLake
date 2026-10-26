import math
import random
import sys
import pygame

# ---------------------------- Settings ---------------------------------------
WIDTH, HEIGHT = 1024, 1024
FPS = 30
CELL_W, CELL_H = 7, 11
COLS, ROWS = WIDTH // CELL_W, HEIGHT // CELL_H
SCENE_W, SCENE_H = 320, 320

BLACK = (2, 5, 3)

random.seed(21)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Swan - Colored ASCII Lake")
clock = pygame.time.Clock()
MONO = "consolas,dejavusansmono,couriernew,monospace"
font = pygame.font.SysFont(MONO, 10)
small_font = pygame.font.SysFont(MONO, 12)

scene = pygame.Surface((SCENE_W, SCENE_H))
background = pygame.Surface((SCENE_W, SCENE_H))   # static layer, built once
ascii_surface = pygame.Surface((WIDTH, HEIGHT))

CHARSET = " .,:;!|/\\()[]{}itlfjrcvunxzXYUJCLQ0OZmwqpdbkhao*#%@"

# Fixed per-cell noise so characters do not flicker randomly every frame.
NOISE = [[random.random() for _ in range(COLS)] for _ in range(ROWS)]
TEXTURE_CHARS = ".,:;|/\\!it"
BRIGHT_CHARS = "o*#@%+"
GAIN = 1.9          # overall brightness of the forest characters
SWAN_CHARS = "#@%8&*o"
SWAN_EDGE = "*o#+"
glyph_cache = {}


def clamp(value, low=0, high=255):
    return max(low, min(high, int(value)))


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(clamp(a[i] * (1 - t) + b[i] * t) for i in range(3))


def glow_circle(surface, x, y, radius, color, strength=1.0):
    for ring in range(4, 0, -1):
        r = max(1, int(radius * ring * 1.9))
        pygame.draw.circle(surface, mix((4, 9, 5), color, strength / (ring * 1.15)),
                           (int(x), int(y)), r)
    pygame.draw.circle(surface, color, (int(x), int(y)), max(1, int(radius)))


# ---------------------------- Static background ------------------------------
def soft_blur(surf, factor=5):
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(2, w // factor), max(2, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


def gold(rng, lo=.25, hi=1.0):
    return mix((70, 85, 24), (238, 226, 112), rng.uniform(lo, hi))


def build_background():
    bg = background
    rng = random.Random(7)

    # Deep green gradient, a little lighter in the middle distance.
    for y in range(SCENE_H):
        v = y / SCENE_H
        base = mix((3, 8, 4), (11, 24, 11), min(1, v * 1.4))
        for x in range(SCENE_W):
            edge = abs(x - SCENE_W * 0.55) / (SCENE_W * 0.55)
            shade = 1 - 0.55 * edge ** 1.3
            bg.set_at((x, y), tuple(clamp(c * shade) for c in base))

    # Soft god-rays leaning from the upper right toward the lower left.
    rays = pygame.Surface((SCENE_W, SCENE_H))
    for i in range(10):
        x_top = rng.randint(110, 400)
        w = rng.randint(14, 44)
        shift = rng.randint(100, 190)
        k = rng.randint(7, 17)
        pygame.draw.polygon(rays, (k, int(k * 1.6), int(k * .5)), [
            (x_top, -10), (x_top + w, -10),
            (x_top + w - shift + 25, SCENE_H), (x_top - shift, SCENE_H)])
    bg.blit(soft_blur(rays, 6), (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # Dark far trunks and heavy canopy silhouettes.
    for i in range(18):
        x = (i * 53 + (i % 4) * 17) % SCENE_W
        width = rng.randint(4, 14)
        top = rng.randint(-20, 30)
        bottom = rng.randint(190, 330)
        color = rng.choice([(2, 6, 3), (4, 10, 5), (7, 16, 7), (10, 21, 9)])
        pygame.draw.polygon(bg, color, [
            (x, top), (x + width, top - 5), (x + width + 6, bottom), (x - 5, bottom + 8)])
    for i in range(190):
        x = rng.randint(-10, SCENE_W + 10)
        y = rng.randint(-15, 120)
        size = rng.randint(3, 14)
        col = rng.choice([(3, 9, 4), (7, 16, 7), (12, 26, 11), (18, 34, 14)])
        pygame.draw.ellipse(bg, col, (x, y, int(size * 1.6), size))

    # Weeping-willow strands, with gold leaves clustered in the upper left
    # and upper right where the light slips through.
    def gold_weight(x, y):
        d1 = math.hypot(x - 60, y - 70) / 70
        d2 = math.hypot(x - 255, y - 45) / 55
        return max(math.exp(-d1 * d1), .8 * math.exp(-d2 * d2))

    for i in range(150):
        x0 = rng.uniform(-5, SCENE_W + 5)
        length = rng.randint(45, 210)
        amp = rng.uniform(1, 4)
        ph = rng.uniform(0, 6.28)
        pts = [(int(x0 + math.sin(j / 12 * 2.2 + ph) * amp + j * .15),
                int(j / 12 * length)) for j in range(13)]
        pygame.draw.lines(bg, (rng.randint(14, 30), rng.randint(30, 52), rng.randint(9, 20)),
                          False, pts, 1)
        for j in range(1, 13):
            if rng.random() < gold_weight(*pts[j]) * .9:
                pygame.draw.circle(bg, gold(rng), pts[j], rng.choice([1, 1, 2]))

    # Dense golden foliage glittering at the upper left and upper right.
    for cx, cy, sx, sy, n in ((55, 65, 38, 45, 330), (250, 45, 34, 28, 150),
                               (150, 120, 40, 22, 40)):
        for _ in range(n):
            x, y = rng.gauss(cx, sx), rng.gauss(cy, sy)
            pygame.draw.circle(bg, gold(rng, .1, 1), (int(x), int(y)), rng.choice([1, 1, 1, 2]))

    # Black masses at the lower left and lower right, like a cave mouth.
    pygame.draw.polygon(bg, (2, 5, 3), [(255, 175), (320, 125), (320, 320), (240, 320), (262, 250)])
    pygame.draw.polygon(bg, (2, 5, 3), [(0, 205), (48, 262), (30, 320), (0, 320)])

    # Dark pool for the water.
    pygame.draw.ellipse(bg, (6, 15, 9), (50, 256, 210, 56))

    # Low mist hovering above the water.
    mist = pygame.Surface((SCENE_W, SCENE_H))
    for i in range(7):
        pygame.draw.ellipse(mist, (10, 17, 9),
                            (rng.randint(-40, 160), rng.randint(214, 256),
                             rng.randint(120, 220), rng.randint(14, 30)))
    bg.blit(soft_blur(mist, 5), (0, 0), special_flags=pygame.BLEND_RGB_ADD)


# Warm moonlit glow behind the swan (additive), built once.
glow_layer = pygame.Surface((SCENE_W, SCENE_H))
for _r in range(90, 0, -3):
    _k = (1 - _r / 90) ** 1.6
    pygame.draw.circle(glow_layer, (int(56 * _k), int(50 * _k), int(24 * _k)), (140, 245), _r)
glow_layer = soft_blur(glow_layer, 3)


# ---------------------------- Animated layers --------------------------------
def draw_hanging_vines(t):
    for i in range(25):
        x0 = (i * 17 + (i % 5) * 7) % SCENE_W
        length = 28 + (i * 19 % 100)
        sway = math.sin(t * .45 + i * 1.7) * (2 + i % 4)
        points = []
        for j in range(13):
            f = j / 12
            x = x0 + math.sin(f * 3 + t * .3 + i) * 2 + sway * f
            points.append((int(x), int(f * length)))
        col = (30 + i % 3 * 6, 43 + i % 4 * 4, 17 + i % 3 * 2)
        pygame.draw.lines(scene, col, False, points, 1)
        for j in range(3 + i % 5):
            yy = 4 + ((j * 17 + i * 9) % max(8, int(length)))
            xx = x0 + math.sin(yy * .08 + t * .3 + i) * 3 + sway * yy / max(1, length)
            twinkle = .5 + .5 * math.sin(t * 2.2 + i * 4 + j * 2)
            if twinkle > .32:
                pygame.draw.circle(scene, mix((38, 49, 20), (230, 218, 126), twinkle),
                                   (int(xx), int(yy)), 1)


def bezier(p0, p1, p2, p3, u):
    a = (1 - u) ** 3
    b = 3 * (1 - u) ** 2 * u
    c = 3 * (1 - u) * u ** 2
    d = u ** 3
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def catmull(points, steps_per=12):
    """Smooth curve passing through every key point."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(steps_per):
            u = k / steps_per
            u2, u3 = u * u, u * u * u
            out.append(tuple(.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * u +
                                   (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u2 +
                                   (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u3)
                             for j in range(2)))
    out.append(tuple(points[-1]))
    return out


def draw_swan_raw(surf, t):
    bob = math.sin(t * 1.15) * 0.8
    WATER = 262 + bob

    # ---- Body: a long teardrop riding low in the water, tail lifted at left.
    body = [
        (84, WATER - 16), (92, WATER - 12), (104, WATER - 18), (120, WATER - 24),
        (138, WATER - 27), (156, WATER - 25), (170, WATER - 19), (180, WATER - 11),
        (182, WATER - 3), (172, WATER + 3), (150, WATER + 5), (120, WATER + 5),
        (96, WATER + 2), (86, WATER - 6),
    ]
    pygame.draw.polygon(surf, (200, 198, 165), body)

    # ---- Raised "busking" wings: two arched feather masses over the back.
    wing = [
        (100, WATER - 10), (104, WATER - 19), (116, WATER - 29), (134, WATER - 35),
        (152, WATER - 31), (164, WATER - 23), (168, WATER - 15), (150, WATER - 14),
        (128, WATER - 12), (112, WATER - 8),
    ]
    pygame.draw.polygon(surf, (242, 239, 207), wing)

    # Feather rows following the arch of the wing.
    for row in range(5):
        pts = []
        for i in range(15):
            u = i / 14
            x = 108 + u * 54
            y = (WATER - 13) - row * 4 - 12 * math.sin(u * math.pi) * (1 - row * .12) + 6 * u
            pts.append((int(x), int(y)))
        shade = 255 - row * 9
        pygame.draw.lines(surf, (shade, shade - 3, shade - 30), False, pts, 2)

    # Wing tips curling up at the rear.
    pygame.draw.line(surf, (255, 252, 228), (104, int(WATER - 22)),
                     (93, int(WATER - 28)), 3)
    pygame.draw.line(surf, (255, 252, 228), (110, int(WATER - 25)),
                     (101, int(WATER - 35)), 2)

    # ---- Neck: tall, slender S-curve. It leans forward out of the chest,
    # sweeps back through the middle, then arches over into a downward-tilted head.
    key = [(165, -8), (183, -15), (193, -32), (190, -52), (178, -72),
           (167, -92), (166, -109), (174, -119), (184, -118)]
    sway = 0.0   # head stays perfectly still
    curve = catmull([(x, 262 + dy * NECK_LEN) for x, dy in key], 12)   # fixed anchor: head never bobs
    n = len(curve) - 1
    pts = []
    for i, (x, y) in enumerate(curve):
        u = i / n
        radius = 3.2 + 3.2 * (1 - u) ** 1.7      # slim, widening into the chest
        pts.append((x + sway * u, y + bob * (1 - u) ** 4, radius))
    for x, y, r in pts:
        pygame.draw.circle(surf, (190, 188, 153), (int(x), int(y)), int(r + .9))
    for x, y, r in pts:
        pygame.draw.circle(surf, (240, 237, 206), (int(x), int(y)), max(1, int(r)))
    for x, y, r in pts:
        pygame.draw.circle(surf, (255, 253, 232), (int(x - .5), int(y - .5)),
                           max(1, int(r * .45)))

    # ---- Head (static): small and rounded, with a slim bill sloping down-forward.
    hx, hy, _ = pts[-1]
    hx, hy = int(hx), int(hy)
    pygame.draw.ellipse(surf, (236, 233, 200), (hx - 6, hy - 5, 12, 10))   # shade
    pygame.draw.ellipse(surf, (255, 255, 244), (hx - 6, hy - 6, 11, 9))    # head
    # Bill: long, slender, angled ~40 degrees downward.
    pygame.draw.polygon(surf, (255, 132, 30),
                        [(hx + 2, hy - 4), (hx + 19, hy + 9), (hx + 16, hy + 12), (hx + 1, hy + 2)])
    pygame.draw.line(surf, (80, 45, 18), (hx + 2, hy + 1), (hx + 17, hy + 11), 1)   # lower edge
    pygame.draw.circle(surf, (28, 20, 15), (hx + 3, hy - 2), 2)                      # black knob
    pygame.draw.circle(surf, (28, 20, 15), (hx + 18, hy + 10), 1)                    # bill tip
    pygame.draw.circle(surf, (20, 20, 16), (hx - 1, hy - 3), 1)                      # eye

    # Moonlit rim highlight along the top of the wing.
    for k in range(10):
        u = k / 9
        pygame.draw.circle(surf, (255, 254, 236),
                           (int(112 + u * 46), int(WATER - 29 - 7 * math.sin(u * math.pi) + 6 * u)), 1)


SWAN_SCALE = 0.78
NECK_LEN = 0.74      # 1.0 = full-length neck; lower = shorter
ANCHOR = (135, 262)          # waterline point the swan is scaled around
swan_layer = pygame.Surface((SCENE_W, SCENE_H), pygame.SRCALPHA)
swan_cells = pygame.Surface((COLS, ROWS), pygame.SRCALPHA)


def draw_swan(t):
    swan_layer.fill((0, 0, 0, 0))
    draw_swan_raw(swan_layer, t)
    size = (int(SCENE_W * SWAN_SCALE), int(SCENE_H * SWAN_SCALE))
    scaled = pygame.transform.smoothscale(swan_layer, size)
    pos = (ANCHOR[0] - ANCHOR[0] * SWAN_SCALE, ANCHOR[1] - ANCHOR[1] * SWAN_SCALE)
    scene.blit(scaled, (int(pos[0]), int(pos[1])))
    full = pygame.Surface((SCENE_W, SCENE_H), pygame.SRCALPHA)
    full.blit(scaled, (int(pos[0]), int(pos[1])))
    global swan_cells
    swan_cells = pygame.transform.smoothscale(full, (COLS, ROWS))


def draw_wake(t):
    """Ripples spreading from the swan plus a V-shaped wake trailing behind."""
    bow_x, bow_y = 172, 264
    # Expanding elliptical rings centred on the body.
    for k in range(5):
        ph = (t * 0.22 + k / 5) % 1.0
        rx = 38 + ph * 95
        ry = 3 + ph * 15
        fade = (1 - ph) ** 1.3
        col = mix((12, 26, 15), (190, 196, 150), fade * .75)
        rect = (int(133 - rx), int(266 - ry), int(rx * 2), int(ry * 2))
        pygame.draw.ellipse(scene, col, rect, 1)
    # V wake: two diverging lines of sparkles streaming back from the bow.
    for side in (-1, 1):
        for i in range(26):
            u = i / 25
            x = bow_x - 6 - u * 125
            y = bow_y + side * (2 + u * 26) + 3
            flick = .5 + .5 * math.sin(t * 2.4 - i * .9)
            col = mix((20, 38, 22), (225, 225, 175), flick * (1 - u) * .9)
            ln = 3 + int(5 * (1 - u))
            pygame.draw.line(scene, col, (int(x), int(y)), (int(x + ln), int(y)), 1)
    # Little bow wave right in front of the chest.
    for k in range(3):
        wob = math.sin(t * 3 + k)
        pygame.draw.line(scene, (205, 210, 165),
                         (int(bow_x + 2 + k * 3), int(bow_y + 2 + k * 2 + wob)),
                         (int(bow_x + 12 + k * 4), int(bow_y + 2 + k * 2 + wob)), 1)


def draw_water(t):
    water_y = 262
    for row in range(26):
        yy = water_y + row
        if yy >= SCENE_H:
            continue
        taper = max(0.0, 1 - row / 29)
        center = 135 + math.sin(row * .25 + t * 1.2) * (2 + row * .12)
        half = (34 + row * .6) * taper
        if half > 1:
            col = mix((10, 22, 12), (168, 163, 118), .40 * taper)
            x1, x2 = int(center - half), int(center + half)
            pygame.draw.line(scene, col, (x1, yy), (x2, yy), 1)
            if row % 3 == 0:
                pygame.draw.line(scene, (210, 201, 142), (x1 + 6, yy),
                                 (min(x2, x1 + 14 + row % 5), yy), 1)

    for i in range(68):
        x = random.Random(i * 13).randint(60, 250)
        y = random.Random(i * 17).randint(268, 309)
        wave = math.sin(t * 2.1 + i * .7)
        length = random.Random(i * 19).randint(2, 12)
        x = int(x + wave * 2)
        col = random.Random(i + 9).choice(
            [(27, 43, 22), (54, 66, 34), (93, 94, 57), (142, 134, 84)])
        pygame.draw.line(scene, col, (x, y), (x + length, y), 1)


def draw_fireflies(t):
    for i in range(110):
        r = random.Random(i * 41 + 7)
        if i % 4 == 0:
            x0, y0 = r.randint(0, SCENE_W), r.randint(0, 105)
        elif i % 4 == 1:
            x0, y0 = r.choice([r.randint(0, 65), r.randint(250, 319)]), r.randint(20, 250)
        elif i % 4 == 2:
            x0, y0 = r.randint(0, 320), r.randint(255, 305)
        else:
            x0, y0 = r.randint(20, 300), r.randint(40, 220)
        x = x0 + math.sin(t * .5 + i) * 1.8
        y = y0 + math.sin(t * .7 + i * 2) * 1.6
        pulse = .5 + .5 * math.sin(t * (1.2 + i % 3) + i * 2.4)
        if pulse > .52:
            color = mix((54, 66, 28), (250, 235, 144), pulse)
            pygame.draw.circle(scene, color, (int(x), int(y)), 1 if pulse < .85 else 2)


# ---------------------------- ASCII conversion -------------------------------
def get_glyph(char, color):
    # Quantise colours so the glyph cache stays small and rendering stays fast.
    key = (char, color[0] >> 3, color[1] >> 3, color[2] >> 3)
    g = glyph_cache.get(key)
    if g is None:
        qc = (min(255, (key[1] << 3) + 4), min(255, (key[2] << 3) + 4),
              min(255, (key[3] << 3) + 4))
        g = font.render(char, True, qc)
        glyph_cache[key] = g
    return g


def make_ascii(t):
    scene.blit(background, (0, 0))
    draw_hanging_vines(t)
    draw_fireflies(t)
    draw_water(t)
    scene.blit(glow_layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    draw_wake(t)
    draw_swan(t)

    # Average the scene down to one pixel per character cell.
    small = pygame.transform.smoothscale(scene, (COLS, ROWS))

    ascii_surface.fill(BLACK)
    n = len(CHARSET) - 1
    for row in range(ROWS):
        for col in range(COLS):
            sw = swan_cells.get_at((col, row))
            if sw[3] >= 45:
                k = 255.0 / sw[3]
                color = mix((min(255, sw[0] * k), min(255, sw[1] * k), min(255, sw[2] * k)),
                            (255, 250, 225), .15)
                chars = SWAN_CHARS if sw[3] >= 85 else SWAN_EDGE
                ch = chars[int(NOISE[row][col] * len(chars)) % len(chars)]
                ascii_surface.blit(get_glyph(ch, color), (col * CELL_W, row * CELL_H))
                continue
            r, g, b = small.get_at((col, row))[:3]
            r, g, b = min(255, int(r * GAIN)), min(255, int(g * GAIN)), min(255, int(b * GAIN))
            lum = r * .22 + g * .65 + b * .13
            noise = NOISE[row][col]
            if lum < 8 and noise < .6:
                continue
            char = CHARSET[int(max(0, min(n, lum / 255 * n)))]
            if 22 < lum < 100 and noise < .28:
                char = TEXTURE_CHARS[int(noise / .28 * len(TEXTURE_CHARS)) % len(TEXTURE_CHARS)]
            if lum > 125:
                char = BRIGHT_CHARS[int(noise * len(BRIGHT_CHARS)) % len(BRIGHT_CHARS)]
            ascii_surface.blit(get_glyph(char, (r, g, b)), (col * CELL_W, row * CELL_H))

    label = small_font.render("SWAN / ASCII LAKE", True, (105, 111, 83))
    footer = small_font.render("COLORED ASCII RECONSTRUCTION", True, (89, 98, 73))
    ascii_surface.blit(label, (18, HEIGHT - 42))
    ascii_surface.blit(footer, (WIDTH - footer.get_width() - 18, HEIGHT - 42))


def main():
    build_background()
    start = pygame.time.get_ticks() / 1000
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                running = False

        t = pygame.time.get_ticks() / 1000 - start
        make_ascii(t)
        screen.blit(ascii_surface, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()