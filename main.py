#!/usr/bin/env python3
# banner_scrambler_ultra.py
# All-in-one FIGlet/toilet-style ASCII banner animator with menu, hotkeys, effects, export, ASCII image mode.
# Deps: pyfiglet, rich, pillow, imageio, rapidfuzz (optional but recommended)

import os, sys, math, time, json, random
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional

from pyfiglet import Figlet, FigletFont
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.live import Live

from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio

try:
    from rapidfuzz import process as rf_process
except Exception:
    rf_process = None

console = Console(highlight=False, soft_wrap=False)
CFG_PATH = os.path.join(os.path.expanduser("~"), ".banner_scrambler.json")

# ----------------------- Options & Presets -----------------------
GRADIENTS = ["rainbow", "ocean", "fire", "retro_green", "retro_amber", "neon", "none"]
GRADIENT_DIRS = ["lr", "rl", "tb", "bt", "d1", "d2"]
MODES = ["scramble", "typewriter", "glitch", "matrix"]

CHARSETS = {
    "ascii":  ''.join(chr(i) for i in range(33, 127)),
    "blocks": " .:-=+*#%@",  # ordered light->dark for ASCII image mapping & matrix
    "binary": "01",
    "hex":    "0123456789ABCDEF",
    "letters":"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
}

THEMES = {
    "phosphor": dict(gradient="retro_green", gradient_dir="lr", outline=True, shadow=False, monochrome=False),
    "neon_grid": dict(gradient="neon", gradient_dir="d1", outline=True, shadow=True, monochrome=False),
    "sunset": dict(gradient="fire", gradient_dir="tb", outline=False, shadow=True, monochrome=False),
    "mono_bold": dict(gradient="none", gradient_dir="lr", outline=True, shadow=True, monochrome=True),
}

# ----------------------- Utils / Color -----------------------
def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v
def lerp(a, b, t): return a + (b - a) * t
def ease_out_expo(t: float) -> float: return 1 - pow(2, -10 * t) if t < 1 else 1

def supports_truecolor() -> bool:
    return os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")

def hsv_to_rgb(h, s, v):
    i = int(h * 6)
    f = h * 6 - i
    p = int(255 * v * (1 - s))
    q = int(255 * v * (1 - f * s))
    t = int(255 * v * (1 - (1 - f) * s))
    v = int(255 * v)
    i %= 6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    return (v, p, q)

def grad_rgb(t: float, scheme: str) -> Tuple[int,int,int]:
    t = clamp(t, 0.0, 1.0)
    if scheme == "rainbow":      return hsv_to_rgb(t, 1.0, 1.0)
    if scheme == "ocean":        return hsv_to_rgb(lerp(0.55, 0.65, t), 0.75, 1.0)
    if scheme == "fire":         return hsv_to_rgb(lerp(0.02, 0.12, t), 1.0, 1.0)
    if scheme == "retro_green":  return (int(40+30*t), int(220-20*(1-t)), int(40+10*t))
    if scheme == "retro_amber":  return (int(255*lerp(0.7,1.0,t)), int(180*lerp(0.4,0.8,t)), 0)
    if scheme == "neon":         return hsv_to_rgb(lerp(0.75, 0.95, t), 1.0, 1.0)
    return (255,255,255)

def grad_t(x:int, y:int, w:int, h:int, direction:str) -> float:
    if w <= 1: w = 2
    if h <= 1: h = 2
    if direction == "lr":  return x / (w-1)
    if direction == "rl":  return 1 - x / (w-1)
    if direction == "tb":  return y / (h-1)
    if direction == "bt":  return 1 - y / (h-1)
    if direction == "d1":  return (x + y) / ((w-1)+(h-1))
    return (x + (h-1-y)) / ((w-1)+(h-1))

# ----------------------- Rendering blocks -----------------------
def render_figlet_block(message: str, font: str, width: int, justify: str) -> List[str]:
    f = Figlet(font=font, width=width, justify=justify)
    art = f.renderText(message if message.strip() else " ")
    return art.rstrip("\n").split("\n")

def ascii_from_image(path:str, out_width:int=120, charset:str=CHARSETS["blocks"]) -> List[str]:
    img = Image.open(path).convert("L")
    w, h = img.size
    aspect = 0.45  # char cell ratio
    new_w = max(10, out_width)
    new_h = max(5, int(h * (new_w / w) * aspect))
    img = img.resize((new_w, new_h))
    px = img.load()
    n = len(charset)-1
    lines = []
    for y in range(new_h):
        row = []
        for x in range(new_w):
            val = px[x,y] / 255.0
            row.append(charset[int(val * n)])
        lines.append("".join(row))
    return lines

def measure_block(block: List[str]) -> Tuple[int, int]:
    h = len(block)
    w = max((len(line) for line in block), default=0)
    return w, h

def pad_block(block: List[str], width:int) -> List[str]:
    return [line.ljust(width) for line in block]

def center_block(block: List[str], term_w:int, term_h:int) -> List[str]:
    w, h = measure_block(block)
    left_pad = max(0, (term_w - w)//2)
    top_pad  = max(0, (term_h - h)//2)
    padded_lines = [(" " * left_pad) + line for line in block]
    return ([""] * top_pad) + padded_lines

# ----------------------- Outline / Shadow / Merge -----------------------
OUTLINE_CHARS = {1:"·", 2:"∙", 3:"•"}

def outline_block(block: List[str]) -> List[str]:
    h, w = len(block), max((len(l) for l in block), default=0)
    pad = pad_block(block, w)
    out = [list(row) for row in pad]
    for y in range(h):
        for x in range(w):
            if pad[y][x] != " ":
                continue
            n = 0
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if dx==0 and dy==0: continue
                    ny,nx=y+dy,x+dx
                    if 0<=ny<h and 0<=nx<w and pad[ny][nx]!=" ":
                        n += 1
            if n:
                out[y][x] = OUTLINE_CHARS[min(3, n)]
    return ["".join(row) for row in out]

def shadow_block(block: List[str], dx:int=1, dy:int=1, char:str="▒") -> List[str]:
    h, w = len(block), max((len(l) for l in block), default=0)
    canvas = [list(" "*(w+dx)) for _ in range(h+dy)]
    for y, line in enumerate(block):
        for x, ch in enumerate(line):
            if ch != " ":
                sy, sx = y+dy, x+dx
                if 0 <= sy < len(canvas) and 0 <= sx < len(canvas[0]):
                    canvas[sy][sx] = char
    return ["".join(r) for r in canvas]

def merge_blocks(base: List[str], overlay: List[str]) -> List[str]:
    h = max(len(base), len(overlay))
    w = max(measure_block(base)[0], measure_block(overlay)[0])
    base = pad_block(base + [""]*(h - len(base)), w)
    overlay = pad_block(overlay + [""]*(h - len(overlay)), w)
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            ch = overlay[y][x] if overlay[y][x] != " " else base[y][x]
            row.append(ch)
        out.append("".join(row))
    return out

# ----------------------- Modes -----------------------
def phased_progress(col_idx: int, total_cols: int, t: float, wave_ms=450.0):
    offset = (col_idx / max(1, total_cols - 1)) * (wave_ms/1000.0)
    return clamp(ease_out_expo(t - offset), 0.0, 1.0)

def scramble_frame(block: List[str], charset: str, t: float, settle_bias: float=0.70, wave_ms=450.0) -> List[str]:
    w, _ = measure_block(block)
    out = []
    rnd = random.random; pick = random.choice
    for line in block:
        buf = []
        for x, ch in enumerate(line):
            if ch == " ":
                buf.append(" ")
            else:
                phase = phased_progress(x, w, t, wave_ms=wave_ms)
                if phase < 0.999 and rnd() < (settle_bias if phase < 0.9 else 0.15):
                    buf.append(pick(charset))
                else:
                    buf.append(ch)
        out.append("".join(buf))
    return out

def typewriter_frame(block: List[str], t: float, cps:int=150) -> List[str]:
    coords = [(y,x) for y,row in enumerate(block) for x,ch in enumerate(row) if ch != " "]
    n = int(min(len(coords), t * cps))
    revealed = set(coords[:n])
    out = []
    for y,row in enumerate(block):
        buf=[]
        for x,ch in enumerate(row):
            buf.append(ch if (y,x) in revealed else " ")
        out.append("".join(buf))
    return out

def glitch_frame(block: List[str], t: float, intensity: float=0.3) -> List[str]:
    out=[]
    for line in block:
        buf=[]
        for ch in line:
            if ch != " " and random.random() < intensity*(1.0 - t):
                buf.append(random.choice(CHARSETS["ascii"]))
            else:
                buf.append(ch)
        out.append("".join(buf))
    return out

def matrix_frame(block: List[str], t: float, density: float=0.08) -> List[str]:
    # Rain over the block area, then settle to text as t→1
    w,h = measure_block(block)
    out=[]
    rain = CHARSETS["blocks"]
    for y,line in enumerate(block):
        buf=[]
        for x,ch in enumerate(line):
            if ch != " ":
                # settle probability grows with t
                if random.random() < t:
                    buf.append(ch)
                else:
                    buf.append(random.choice(rain))
            else:
                # sparse rain in empty space
                buf.append(random.choice(rain) if random.random() < density*(1.0 - t) else " ")
        out.append("".join(buf))
    return out

# ----------------------- Colorize & print -----------------------
def colorize_block(block: List[str], scheme: str, direction: str) -> List[Text]:
    w, h = measure_block(block)
    styled: List[Text] = []
    if scheme == "none" or not supports_truecolor():
        # monochrome / fallback: just print, maybe bold later
        return [Text(line) for line in block]
    for y, line in enumerate(block):
        t = Text()
        for x, ch in enumerate(line):
            if ch == " ": t.append(" "); continue
            tt = grad_t(x, y, w, h, direction)
            r,g,b = grad_rgb(tt, scheme)
            t.append(ch, style=f"rgb({r},{g},{b})")
        styled.append(t)
    return styled

def diff_print(prev: List[str], curr: List[str]):
    # Print only changed runs; 1-based coordinates for ANSI
    rows = max(len(prev), len(curr))
    for y in range(rows):
        a = prev[y] if y < len(prev) else ""
        b = curr[y] if y < len(curr) else ""
        if a == b: continue
        la, lb = len(a), len(b)
        if lb > la: a = a.ljust(lb)
        elif la > lb: b = b.ljust(la)
        i = 0
        while i < len(b):
            if a[i] != b[i]:
                j = i
                while j < len(b) and a[j] != b[j]:
                    j += 1
                console.print(f"\x1b[{y+1};{i+1}H" + b[i:j], end="")
                i = j
            else:
                i += 1

# ----------------------- Export -----------------------
def find_mono_font() -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/Library/Fonts/Menlo.ttc",
        "C:\\Windows\\Fonts\\consola.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, 18)
            except Exception: pass
    return ImageFont.load_default()

def render_frame_to_image(block: List[str], scheme:str, direction:str, outline_on:bool, shadow_on:bool) -> Image.Image:
    font = find_mono_font()
    base = block[:]
    if outline_on: base = merge_blocks(outline_block(block), base)
    if shadow_on:  base = merge_blocks(shadow_block(block,1,1,"▒"), base)
    bbox = font.getbbox("M")
    cell_w = max(1, bbox[2]-bbox[0]); cell_h = max(1, bbox[3]-bbox[1])
    w, h = measure_block(base)
    img = Image.new("RGB", (max(1,w*cell_w), max(1,h*cell_h)), (0,0,0))
    draw = ImageDraw.Draw(img)
    truecolor = (scheme != "none") and supports_truecolor()
    for y, line in enumerate(base):
        for x, ch in enumerate(line):
            if ch == " ": continue
            if truecolor:
                tt = grad_t(x,y,w,h,direction)
                r,g,b = grad_rgb(tt, scheme)
                draw.text((x*cell_w, y*cell_h), ch, fill=(r,g,b), font=font)
            else:
                draw.text((x*cell_w, y*cell_h), ch, fill=(255,255,255), font=font)
    return img

def export_animation(frames: List[List[str]], scheme:str, direction:str, path:str, fps:int, outline_on:bool, shadow_on:bool):
    ext = os.path.splitext(path)[1].lower()
    imgs=[]
    for blk in frames:
        imgs.append(render_frame_to_image(blk, scheme, direction, outline_on, shadow_on))
    if ext == ".gif":
        imageio.mimsave(path, imgs, duration=1/max(1,fps))
    else:
        arrs = [imageio.core.util.Array(img) for img in imgs]
        try:
            imageio.mimwrite(path, arrs, fps=fps, codec="h264_nvenc", quality=7)
        except Exception:
            imageio.mimwrite(path, arrs, fps=fps, codec="libx264", quality=8)

# ----------------------- Config -----------------------
@dataclass
class Config:
    # Content
    message: str = "ZeroDay Labs"
    use_image: bool = False
    image_path: Optional[str] = None
    image_width: int = 120
    # FIGlet
    font: str = "standard"
    width: int = 120
    align: str = "left"
    # Animation
    mode: str = "scramble"
    fps: int = 60
    duration: float = 3.0
    charset_key: str = "ascii"
    gradient: str = "rainbow"
    gradient_dir: str = "lr"
    seed: Optional[int] = None
    wave_ms: float = 450.0
    typewriter_cps: int = 150
    glitch_intensity: float = 0.3
    # Effects
    outline: bool = True
    shadow: bool = True
    # Layout / Accessibility
    auto_center: bool = True
    monochrome: bool = False
    # Export
    export_path: Optional[str] = None

    def clamp(self):
        self.width      = clamp(self.width, 40, 300)
        self.fps        = clamp(self.fps, 10, 240)
        self.duration   = clamp(self.duration, 0.5, 60.0)
        self.align      = self.align if self.align in ("left","center","right") else "left"
        self.mode       = self.mode if self.mode in MODES else "scramble"
        self.charset_key= self.charset_key if self.charset_key in CHARSETS else "ascii"
        self.gradient   = self.gradient if self.gradient in GRADIENTS else "rainbow"
        self.gradient_dir= self.gradient_dir if self.gradient_dir in GRADIENT_DIRS else "lr"
        self.wave_ms    = clamp(self.wave_ms, 0.0, 2000.0)
        self.typewriter_cps = clamp(self.typewriter_cps, 10, 1000)
        self.glitch_intensity= clamp(self.glitch_intensity, 0.0, 1.0)
        if self.font not in FigletFont.getFonts(): self.font = "standard"

def load_config() -> Config:
    if os.path.exists(CFG_PATH):
        try:
            data = json.load(open(CFG_PATH, "r", encoding="utf-8"))
            cfg = Config(**data)  # type: ignore
            cfg.clamp()
            return cfg
        except Exception:
            pass
    cfg = Config(); cfg.clamp(); return cfg

def save_config(cfg: Config):
    try:
        json.dump(asdict(cfg), open(CFG_PATH, "w", encoding="utf-8"), indent=2)
    except Exception as e:
        console.print(f"[red]Failed to save config:[/red] {e}")

# ----------------------- UI helpers -----------------------
def header(cfg: Config):
    hud = Text()
    hud.append("ASCII Banner Ultra  ", style="bold cyan")
    hud.append(f"[{cfg.mode}]  ", style="magenta")
    hud.append(f"Font:{cfg.font}  Grad:{cfg.gradient}/{cfg.gradient_dir}  FPS:{cfg.fps}  Dur:{cfg.duration}s  ")
    if cfg.seed is not None: hud.append(f"Seed:{cfg.seed}  ", style="dim")
    if cfg.monochrome: hud.append("MONO  ")
    console.print(Panel(hud, border_style="cyan"))

def get_term_size() -> Tuple[int,int]:
    size = console.size
    return size.width, size.height

def build_base_block(cfg: Config) -> List[str]:
    if cfg.use_image and cfg.image_path:
        try:
            return ascii_from_image(cfg.image_path, cfg.image_width, CHARSETS["blocks"])
        except Exception as e:
            console.print(f"[red]Image load failed:[/red] {e}. Falling back to text.")
    return render_figlet_block(cfg.message, cfg.font, cfg.width, cfg.align)

def compose_layers(block: List[str], cfg: Config) -> List[str]:
    composed = block[:]
    if cfg.outline: composed = merge_blocks(outline_block(block), composed)
    if cfg.shadow:  composed = merge_blocks(shadow_block(block,1,1,"▒"), composed)
    return composed

def preview(cfg: Config):
    if cfg.seed is not None: random.seed(cfg.seed)
    base = build_base_block(cfg)
    if cfg.auto_center:
        tw, th = get_term_size()
        base = center_block(base, tw, th-8)
    composed = compose_layers(base, cfg)
    scheme = "none" if cfg.monochrome or not supports_truecolor() else cfg.gradient
    styled = colorize_block(composed, scheme, cfg.gradient_dir)
    console.print(Panel(Text("Live Preview (hotkeys below)", style="bold"), border_style="magenta"))
    for tline in styled:
        console.print(tline, overflow="crop", no_wrap=True)
    console.print()

def run_animation(cfg: Config, record: bool=False):
    if cfg.seed is not None: random.seed(cfg.seed)
    base = build_base_block(cfg)
    if cfg.auto_center:
        tw, th = get_term_size()
        base = center_block(base, tw, th-2)

    frames: List[List[str]] = []
    prev_for_diff: List[str] = []
    start = time.perf_counter()
    frame_dt = 1.0 / max(1, cfg.fps)

    # prepare screen
    console.print("\x1b[2J\x1b[H", end="")  # clear + home

    while True:
        now = time.perf_counter()
        t = clamp((now - start) / max(0.001, cfg.duration), 0.0, 1.0)
        if cfg.mode == "scramble":
            blk = scramble_frame(base, CHARSETS[cfg.charset_key], t, wave_ms=cfg.wave_ms)
        elif cfg.mode == "typewriter":
            blk = typewriter_frame(base, t, cps=cfg.typewriter_cps)
        elif cfg.mode == "glitch":
            blk = glitch_frame(base, t, intensity=cfg.glitch_intensity)
        else:
            blk = matrix_frame(base, t)

        comp = compose_layers(blk, cfg)
        frames.append(comp)

        # Live render with diff
        if not record:
            scheme = "none" if cfg.monochrome or not supports_truecolor() else cfg.gradient
            if prev_for_diff:
                # print raw strings for diff; color via styled pass for fixed sections
                diff_print(prev_for_diff, comp)
            else:
                console.print("\x1b[H", end="")
                for line in comp: console.print(line, end="\n")
            prev_for_diff = comp
        # pace
        target = start + (math.floor((now - start) / frame_dt) + 1) * frame_dt
        delay = max(0.0, target - time.perf_counter())
        if delay: time.sleep(delay)
        if t >= 1.0: break

    # Final reveal
    final = compose_layers(base, cfg)
    if not record:
        scheme = "none" if cfg.monochrome or not supports_truecolor() else cfg.gradient
        console.print("\x1b[H", end="")
        for tl in colorize_block(final, scheme, cfg.gradient_dir):
            tl.stylize("bold")
            console.print(tl, overflow="crop", no_wrap=True)
        console.print("\n[green]Done.[/green] Press Enter to return.")
        try: input()
        except EOFError: pass

    if record and cfg.export_path:
        scheme = "none" if cfg.monochrome or not supports_truecolor() else cfg.gradient
        console.print(f"[cyan]Exporting to {cfg.export_path}…[/cyan]")
        export_animation(frames, scheme, cfg.gradient_dir, cfg.export_path, cfg.fps, cfg.outline, cfg.shadow)
        console.print(f"[green]Saved {cfg.export_path}[/green]")

# ----------------------- Menus & Hotkeys -----------------------
def fonts_list(): return sorted(FigletFont.getFonts())

def pick_font_interactive() -> Optional[str]:
    fonts = fonts_list()
    per_page, page = 20, 0
    total = len(fonts)
    while True:
        console.clear()
        header(Config())
        start = page * per_page
        chunk = fonts[start:start + per_page]
        table = Table(title=f"FIGlet Fonts (page {page+1}/{(total-1)//per_page+1})")
        table.add_column("#", justify="right", style="cyan", width=6)
        table.add_column("Font", style="white")
        for i,name in enumerate(chunk, start=start): table.add_row(str(i), name)
        console.print(table)
        console.print("[dim]n=next p=prev q=quit  |  / search  |  index to pick[/dim]")
        choice = Prompt.ask("Choice", default="q").strip()
        if choice == "n": page = (page + 1) % ((total-1)//per_page + 1)
        elif choice == "p": page = (page - 1) % ((total-1)//per_page + 1)
        elif choice == "q": return None
        elif choice == "/":
            q = Prompt.ask("Search")
            if rf_process:
                matches = [m[0] for m in rf_process.extract(q, fonts, limit=30)]
            else:
                matches = [f for f in fonts if q.lower() in f.lower()][:30]
            console.print(", ".join(matches) if matches else "[red]No matches[/red]")
            pick = Prompt.ask("Pick exact name or 'back'", default="back")
            if pick in fonts: return pick
        elif choice.isdigit():
            idx=int(choice)
            if 0<=idx<total: return fonts[idx]

def header_hotkeys():
    console.print("[dim]Hotkeys: F font  G gradient  D dir  M mode  O outline  S shadow  C center  P play  X export  T theme  Q back[/dim]")

def main_menu():
    cfg = load_config()
    while True:
        console.clear()
        header(cfg)
        preview(cfg)
        header_hotkeys()

        menu = Table.grid(padding=1)
        menu.add_row("[bold]1[/bold] Text/Image", "[bold]2[/bold] Font/Width/Align", "[bold]3[/bold] Gradients/Colors")
        menu.add_row("[bold]4[/bold] Mode/Timings", "[bold]5[/bold] Effects", "[bold]6[/bold] Layout/Mono")
        menu.add_row("[bold]7[/bold] Export", "[bold]8[/bold] Run", "[bold]9[/bold] Save Profile")
        menu.add_row("[bold]0[/bold] Exit", "", "")
        console.print(Panel(menu, title="Menu", border_style="blue"))

        choice = Prompt.ask("Select (or press a hotkey)", default="8").strip()

        # Hotkeys first
        if choice.upper() == "F":
            picked = pick_font_interactive()
            if picked: cfg.font = picked
            continue
        if choice.upper() == "G":
            i = (GRADIENTS.index(cfg.gradient)+1) % len(GRADIENTS)
            cfg.gradient = GRADIENTS[i]; continue
        if choice.upper() == "D":
            i = (GRADIENT_DIRS.index(cfg.gradient_dir)+1) % len(GRADIENT_DIRS)
            cfg.gradient_dir = GRADIENT_DIRS[i]; continue
        if choice.upper() == "M":
            i = (MODES.index(cfg.mode)+1) % len(MODES)
            cfg.mode = MODES[i]; continue
        if choice.upper() == "O":
            cfg.outline = not cfg.outline; continue
        if choice.upper() == "S":
            cfg.shadow = not cfg.shadow; continue
        if choice.upper() == "C":
            cfg.auto_center = not cfg.auto_center; continue
        if choice.upper() == "P":
            cfg.clamp(); run_animation(cfg); continue
        if choice.upper() == "X":
            path = Prompt.ask("Export to (.gif/.mp4)")
            if path.strip():
                cfg.export_path = path.strip()
                cfg.clamp()
                run_animation(cfg, record=True)
            continue
        if choice.upper() == "T":
            console.print(f"Available themes: {', '.join(THEMES)}")
            name = Prompt.ask("Theme name", choices=list(THEMES.keys()), default="phosphor")
            for k,v in THEMES[name].items(): setattr(cfg, k, v)
            continue
        if choice.upper() == "Q":
            continue

        # Menu flow
        if choice == "1":
            cfg.use_image = Confirm.ask("Use ASCII image mode?", default=cfg.use_image)
            if cfg.use_image:
                p = Prompt.ask("Image path", default=cfg.image_path or "")
                cfg.image_path = p if p.strip() else None
                iw = IntPrompt.ask("ASCII image width (40..300)", default=cfg.image_width)
                cfg.image_width = clamp(iw, 40, 300)
            else:
                msg = Prompt.ask("Enter message (\\n for newline)", default=cfg.message.replace("\n","\\n"))
                cfg.message = msg.replace("\\n","\n")
        elif choice == "2":
            sub = Prompt.ask("a) pick font  b) search font  c) width/align", choices=["a","b","c"], default="a")
            if sub == "a":
                picked = pick_font_interactive()
                if picked: cfg.font = picked
            elif sub == "b":
                q = Prompt.ask("Search")
                fonts = fonts_list()
                if rf_process:
                    matches = [m[0] for m in rf_process.extract(q, fonts, limit=30)]
                else:
                    matches = [f for f in fonts if q.lower() in f.lower()][:30]
                console.print(", ".join(matches) if matches else "[red]No matches[/red]")
                pick = Prompt.ask("Exact name or 'back'", default="back")
                if pick in fonts: cfg.font = pick
            else:
                w = IntPrompt.ask("FIGlet width (40..300)", default=cfg.width)
                a = Prompt.ask("Align", choices=["left","center","right"], default=cfg.align)
                cfg.width, cfg.align = clamp(w,40,300), a
        elif choice == "3":
            g = Prompt.ask("Gradient", choices=GRADIENTS, default=cfg.gradient)
            d = Prompt.ask("Direction", choices=GRADIENT_DIRS, default=cfg.gradient_dir)
            mono = Confirm.ask("Monochrome mode?", default=cfg.monochrome)
            cfg.gradient, cfg.gradient_dir, cfg.monochrome = g, d, mono
        elif choice == "4":
            m = Prompt.ask("Mode", choices=MODES, default=cfg.mode)
            cfg.mode = m
            fps = IntPrompt.ask("FPS (10..240)", default=cfg.fps)
            dur = float(Prompt.ask("Duration seconds (0.5..60)", default=str(cfg.duration)))
            cfg.fps, cfg.duration = clamp(fps,10,240), clamp(dur,0.5,60.0)
            if m == "scramble":
                wav = float(Prompt.ask("Wave delay ms (0..2000)", default=str(cfg.wave_ms)))
                cfg.wave_ms = clamp(wav, 0.0, 2000.0)
                ck = Prompt.ask("Scramble charset", choices=list(CHARSETS.keys()), default=cfg.charset_key)
                cfg.charset_key = ck
            elif m == "typewriter":
                cps = IntPrompt.ask("Characters per second (10..1000)", default=cfg.typewriter_cps)
                cfg.typewriter_cps = clamp(cps, 10, 1000)
            elif m == "glitch":
                gi = float(Prompt.ask("Glitch intensity 0..1", default=str(cfg.glitch_intensity)))
                cfg.glitch_intensity = clamp(gi, 0.0, 1.0)
        elif choice == "5":
            cfg.outline = Confirm.ask("Outline on?", default=cfg.outline)
            cfg.shadow  = Confirm.ask("Shadow on?",  default=cfg.shadow)
        elif choice == "6":
            cfg.auto_center = Confirm.ask("Auto center to terminal?", default=cfg.auto_center)
            cfg.monochrome  = Confirm.ask("Monochrome (ignore gradients)?", default=cfg.monochrome)
            if Confirm.ask("Use a fixed random seed?", default=(cfg.seed is not None)):
                seed = IntPrompt.ask("Seed", default=cfg.seed if cfg.seed is not None else 1337)
                cfg.seed = int(seed)
            else:
                cfg.seed = None
        elif choice == "7":
            path = Prompt.ask("Export path (.gif or .mp4), blank to disable", default=(cfg.export_path or ""))
            cfg.export_path = path.strip() or None
        elif choice == "8":
            cfg.clamp(); run_animation(cfg)
        elif choice == "9":
            cfg.clamp(); save_config(cfg); console.print(f"[green]Saved to {CFG_PATH}[/green]"); time.sleep(1)
        elif choice == "0":
            break

# ----------------------- Entrypoint -----------------------
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[dim]Bye.[/dim]")
