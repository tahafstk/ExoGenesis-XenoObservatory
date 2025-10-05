import pygame
import random
import math

# --- Pygame Başlat ---
pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Microgravity Simulation")

clock = pygame.time.Clock()
FPS = 60

# --- Nesne Sınıfı ---
class FloatObj:
    def __init__(self, x, y, r=20):
        self.x = x
        self.y = y
        self.r = r
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-1.5, 1.5)
        self.color = (200, 200, 255)

    def update(self):
        """Nesnenin konumunu güncelle ve kenarlardan sekmesini sağla."""
        self.x += self.vx
        self.y += self.vy

        # Kenarlardan sekme
        if self.x - self.r < 0 or self.x + self.r > WIDTH:
            self.vx *= -1
        if self.y - self.r < 0 or self.y + self.r > HEIGHT:
            self.vy *= -1

    def draw(self, surf):
        """Nesneyi ekrana çiz."""
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (100, 100, 120), (int(self.x), int(self.y)), self.r, 2)

# --- Nesneleri Oluştur ---
objs = [
    FloatObj(
        random.randint(50, WIDTH - 50),
        random.randint(50, HEIGHT - 50),
        random.randint(15, 30)
    )
    for _ in range(10)
]

font = pygame.font.SysFont("Arial", 24)

# --- Ana Döngü ---
running = True
while running:
    clock.tick(FPS)

    # Olaylar
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            for o in objs:
                if math.hypot(o.x - mx, o.y - my) <= o.r:
                    # Nesneye tıklanınca hızını değiştir
                    o.vx += random.uniform(-3, 3)
                    o.vy += random.uniform(-3, 3)

    # Güncelleme
    for o in objs:
        o.update()

    # Çizim
    screen.fill((10, 20, 30))
    text = font.render("Microgravity Demo: Nesnelere tıkla, süzülsünler!", True, (220, 220, 220))
    screen.blit(text, (10, 10))

    for o in objs:
        o.draw(screen)

    pygame.display.flip()

pygame.quit()
