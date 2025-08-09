#!/usr/bin/env python3
# banner_scrambler_pro.py
# Maxed-out FIGlet/toilet-style ASCII banner animator with TUI, effects, export, and ASCII image mode.
# Deps: pyfiglet, rich, pillow, imageio

import os, sys, math, time, json, random, io
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional

from pyfiglet import Figlet, FigletFont
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm

from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio

console = Console(highlight=False, soft_wrap=False)

# -------------------------- Globals / Options --------------------------

CFG_PATH = os.path.join(os.path.expanduser("~"), ".banner_scrambler.json")

GRADIENTS = ["rainbow", "ocean", "fire", "retro_green", "retro_amber", "neon", "none"]
GRADIENT_DIRS = ["lr", "rl", "tb", "bt", "d1", "d2"]  # left->right, right->left, top->bottom, etc.
MODES = ["scramble", "typewriter", "glitch"]

CHARSETS = {
    "ascii":  ''.join(chr(i) for i in range(33, 127)),
    "blocks": " .:-=+*#%@",  # ordered light->dark for ASCII image mapping
    "binary": "01",
    "hex":    "0123456789ABCDEF",
    "letters":"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
}

# -------------------------- Math & Color helpers --------------------------

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def ease_out_expo(t: float) -> float:
    return 1 - pow(2, -10 * t) if t < 1 else 1

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
    if scheme == "rainbow":
        return hsv_to_rgb(t, 1.0, 1.0)
    if scheme == "ocean":
        return hsv_to_rgb(lerp(0.55, 0.65, t), 0.75, 1.0)
    if scheme == "fire":
        return hsv_to_rgb(lerp(0.02, 0.12, t), 1.0, 1.0)
    if scheme == "retro_green":
        # phosphor green sweep
        r,g,b = (int(40+30*t), int(220-20*(1-t)), int(40+10*t))
        return (r,g,b)
    if scheme == "retro_amber":
        r,g,b = (int(255*lerp(0.7, 1.0, t)), int(180*lerp(0.4, 0.8, t)), int(0))
        return (r,g,b)
    if scheme == "neon":
        return hsv_to_rgb(lerp(0.75, 0.95, t), 1.0, 1.0)
    return (255,255,255)

def grad_t(x:int, y:int, w:int, h:int, direction:str) -> float:
    if w <= 1: w = 2
    if h <= 1: h = 2
    if direction == "lr":  return x / (w-1)
    if direction == "rl":  return 1 - x / (w-1)
    if direction == "tb":  return y / (h-1)
    if direction == "bt":  return 1 - y / (h-1)
    if direction == "d1":  return (x + y) / ((w-1)+(h-1))
    # d2
    return (x + (h-1-y)) / ((w-1)+(h-1))

# -------------------------- FIGlet / ASCII image render --------------------------

def render_figlet_block(message: str, font: str, width: int, justify: str) -> List[str]:
    f = Figlet(font=font, width=width, justify=justify)
    art = f.renderText(message if message.strip() else " ")
    return art.rstrip("\n").split("\n")

def ascii_from_image(path:str, out_width:int=120, charset:str=CHARSETS["blocks"]) -> List[str]:
    # Load & convert image to ASCII block using luminance
    img = Image.open(path).convert("L")
    w, h = img.size
    # maintain aspect: characters are ~2:1 height:width, so adjust height
    aspect = 0.45
    new_w = max(10, out_width)
    new_h = max(5, int(h * (new_w / w) * aspect))
    img = img.resize((new_w, new_h))
    px = img.load()
    # Map luminance to charset (dark->light aligns with charset order)
    n = len(charset)-1
    lines = []
    for y in range(new_h):
        row = []
        for x in range(new_w):
            val = px[x,y] / 255.0
            idx = int(val * n)
            row.append(charset[idx])
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

# -------------------------- Effects: outline / shadow / compose --------------------------

def outline_block(block: List[str]) -> List[str]:
    h, w = len(block), max((len(l) for l in block), default=0)
    pad = pad_block(block, w)
    out = [list(row) for row in pad]
    for y in range(h):
        for x in range(w):
            if pad[y][x] != " ":
                continue
            # if any neighbor is non-space -> outline dot
            found = False
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if dy == 0 and dx == 0: continue
                    ny, nx = y+dy, x+dx
                    if 0 <= ny < h and 0 <= nx < w and pad[ny][nx] != " ":
                        out[y][x] = "·"
                        found = True
                        break
                if found: break
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

# -------------------------- Modes: scramble / typewriter / glitch --------------------------

def phased_progress(col_idx: int, total_cols: int, t: float, wave_ms=450.0):
    offset = (col_idx / max(1, total_cols - 1)) * (wave_ms/1000.0)
    return clamp(ease_out_expo(t - offset), 0.0, 1.0)

def scramble_frame(block: List[str], charset: str, t: float, settle_bias: float=0.70, wave_ms=450.0) -> List[str]:
    w, h = measure_block(block)
    out = []
    rnd = random.random
    pick = random.choice
    for y, line in enumerate(block):
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
    # intensity controls how many characters temporarily flip each frame
    w,h = measure_block(block)
    out=[]
    for y,line in enumerate(block):
        buf=[]
        for x,ch in enumerate(line):
            if ch != " " and random.random() < intensity*(1.0 - t):
                buf.append(random.choice(CHARSETS["ascii"]))
            else:
                buf.append(ch)
        out.append("".join(buf))
    return out

# -------------------------- Colorize & print --------------------------

def colorize_block(block: List[str], scheme: str, direction: str) -> List[Text]:
    w, h = measure_block(block)
    styled: List[Text] = []
    for y, line in enumerate(block):
        t = Text()
        for x, ch in enumerate(line):
            if ch == " ":
                t.append(" ")
            else:
                tt = grad_t(x, y, w, h, direction)
                r,g,b = grad_rgb(tt, scheme)
                t.append(ch, style=f"rgb({r},{g},{b})")
        styled.append(t)
    return styled

# -------------------------- Export (GIF/MP4) --------------------------

def find_mono_font() -> ImageFont.FreeTypeFont:
    # Try common monospace fonts; fallback to PIL default
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/Library/Fonts/Menlo.ttc",
        "C:\\Windows\\Fonts\\consola.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, 18)
            except Exception:
                pass
    return ImageFont.load_default()

def render_frame_to_image(block: List[str], scheme:str, direction:str, outline_on:bool, shadow_on:bool) -> Image.Image:
    # Compose layers in-memory and paint to an image using a monospace font
    font = find_mono_font()
    # Compose layers
    base = block[:]
    if outline_on:
        base = merge_blocks(outline_block(block), base)
    if shadow_on:
        base = merge_blocks(shadow_block(block, dx=1, dy=1, char="▒"), base)
    # Measure cell size
    # crude estimate: use font.getbbox for 'M'
    bbox = font.getbbox("M")
    cell_w = bbox[2]-bbox[0]
    cell_h = bbox[3]-bbox[1]
    w, h = measure_block(base)
    img = Image.new("RGB", (max(1,w*cell_w), max(1,h*cell_h)), (0,0,0))
    draw = ImageDraw.Draw(img)
    for y, line in enumerate(base):
        for x, ch in enumerate(line):
            if ch == " ":
                continue
            tt = grad_t(x,y,w,h,direction)
            r,g,b = grad_rgb(tt, scheme)
            draw.text((x*cell_w, y*cell_h), ch, fill=(r,g,b), font=font)
    return img

def export_animation(frames: List[List[str]], scheme:str, direction:str, path:str, fps:int, outline_on:bool, shadow_on:bool):
    ext = os.path.splitext(path)[1].lower()
    imgs=[]
    for blk in frames:
        imgs.append(render_frame_to_image(blk, scheme, direction, outline_on, shadow_on))
    if ext in (".gif",):
        imageio.mimsave(path, imgs, duration=1/max(1,fps))
    else:
        # mp4 or others
        arrs = [imageio.core.util.Array(img) for img in imgs]
        imageio.mimwrite(path, arrs, fps=fps, codec="libx264", quality=8)

# -------------------------- Config --------------------------

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
    mode: str = "scramble"     # scramble | typewriter | glitch
    fps: int = 60
    duration: float = 3.0
    charset_key: str = "ascii"
    gradient: str = "rainbow"
    gradient_dir: str = "lr"   # lr, rl, tb, bt, d1, d2
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
    high_contrast: bool = False
    # Export
    export_path: Optional[str] = None  # e.g., out.gif or out.mp4

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
        if self.font not in FigletFont.getFonts():
            self.font = "standard"

def load_config() -> Config:
    if os.path.exists(CFG_PATH):
        try:
            data = json.load(open(CFG_PATH, "r", encoding="utf-8"))
            cfg = Config(**data)  # type: ignore
            cfg.clamp()
            return cfg
        except Exception:
            pass
    cfg = Config()
    cfg.clamp()
    return cfg

def save_config(cfg: Config):
    try:
        json.dump(asdict(cfg), open(CFG_PATH, "w", encoding="utf-8"), indent=2)
    except Exception as e:
        console.print(f"[red]Failed to save config:[/red] {e}")

# -------------------------- UI helpers --------------------------

def header(cfg: Config):
    hud = Text()
    hud.append("ASCII Banner Pro  ", style="bold cyan")
    hud.append(f"[{cfg.mode}]  ", style="magenta")
    hud.append(f"Font: {cfg.font}  ")
    hud.append(f"Grad: {cfg.gradient}/{cfg.gradient_dir}  ")
    hud.append(f"FPS: {cfg.fps}  Dur: {cfg.duration}s  ")
    if cfg.seed is not None:
        hud.append(f"Seed: {cfg.seed}  ", style="dim")
    hud.append("(mono)  " if cfg.monochrome else "")
    console.print(Panel(hud, border_style="cyan"))

def list_fonts_paginated() -> Optional[str]:
    fonts = sorted(FigletFont.getFonts())
    per_page = 20
    total = len(fonts)
    page = 0
    while True:
        console.clear()
        header(Config())  # temp
        start = page * per_page
        chunk = fonts[start:start + per_page]
        table = Table(title=f"FIGlet Fonts (page {page+1}/{(total-1)//per_page+1})")
        table.add_column("#", justify="right", style="cyan", width=6)
        table.add_column("Font", style="white")
        for i,name in enumerate(chunk, start=start):
            table.add_row(str(i), name)
        console.print(table)
        console.print("[dim]n=next p=prev q=quit  |  Search: type text and press Enter  |  Or enter an index[/dim]")
        choice = Prompt.ask("Choice", default="q").strip()
        if choice.lower() == "n":
            page = (page + 1) % ((total-1)//per_page + 1)
        elif choice.lower() == "p":
            page = (page - 1) % ((total-1)//per_page + 1)
        elif choice.lower() == "q":
            return None
        elif choice.isdigit():
            idx=int(choice)
            if 0<=idx<total: return fonts[idx]
        else:
            # substring search
            matches = [f for f in fonts if choice.lower() in f.lower()]
            if not matches:
                console.print("[red]No matches.[/red]"); time.sleep(1); continue
            console.clear(); header(Config())
            t2 = Table(title=f"Matches for '{choice}'")
            t2.add_column("Font")
            for n in matches[:50]:
                t2.add_row(n)
            console.print(t2)
            picked = Prompt.ask("Pick exact name or 'back'", default="back")
            if picked in matches: return picked

def build_base_block(cfg: Config) -> List[str]:
    if cfg.use_image and cfg.image_path:
        try:
            return ascii_from_image(cfg.image_path, cfg.image_width, CHARSETS["blocks"])
        except Exception as e:
            console.print(f"[red]Image load failed:[/red] {e}. Falling back to text.")
    return render_figlet_block(cfg.message, cfg.font, cfg.width, cfg.align)

def get_term_size() -> Tuple[int,int]:
    size = console.size
    return size.width, size.height

def preview(cfg: Config):
    if cfg.seed is not None:
        random.seed(cfg.seed)
    base = build_base_block(cfg)
    # Compose toilets: outline + shadow (dim), then main
    composed = base[:]
    if cfg.outline:
        composed = merge_blocks(outline_block(base), composed)
    if cfg.shadow:
        composed = merge_blocks(shadow_block(base,1,1,"▒"), composed)

    if cfg.auto_center:
        tw, th = get_term_size()
        composed = center_block(composed, tw, th-8)  # leave space for HUD

    scheme = "none" if cfg.monochrome else cfg.gradient
    styled = colorize_block(composed, scheme, cfg.gradient_dir)
    console.print(Panel(Text("Live Preview", style="bold"), border_style="magenta"))
    for tline in styled:
        console.print(tline, overflow="crop", no_wrap=True)
    console.print()

def run_animation(cfg: Config, export_only:bool=False):
    if cfg.seed is not None:
        random.seed(cfg.seed)
    base = build_base_block(cfg)
    if cfg.auto_center:
        tw, th = get_term_size()
        base = center_block(base, tw, th-2)

    frames: List[List[str]] = []
    start = time.perf_counter()
    frame_dt = 1.0 / max(1, cfg.fps)
    total_time = cfg.duration

    while True:
        now = time.perf_counter()
        t = clamp((now - start) / max(0.001, total_time), 0.0, 1.0)
        if cfg.mode == "scramble":
            blk = scramble_frame(base, CHARSETS[cfg.charset_key], t, wave_ms=cfg.wave_ms)
        elif cfg.mode == "typewriter":
            blk = typewriter_frame(base, t, cps=cfg.typewriter_cps)
        else:
            blk = glitch_frame(base, t, intensity=cfg.glitch_intensity)

        # Outline/shadow compositing per-frame for nicer feel
        comp = blk[:]
        if cfg.outline: comp = merge_blocks(outline_block(blk), comp)
        if cfg.shadow:  comp = merge_blocks(shadow_block(blk,1,1,"▒"), comp)
        frames.append(comp)

        if t >= 1.0: break
        # pace to FPS
        target = start + (math.floor((now - start) / frame_dt) + 1) * frame_dt
        delay = max(0.0, target - time.perf_counter())
        if not export_only and delay:
            # live print
            scheme = "none" if cfg.monochrome else cfg.gradient
            styled = colorize_block(comp, scheme, cfg.gradient_dir)
            console.print("\x1b[H", end="")
            for tl in styled:
                console.print(tl, overflow="crop", no_wrap=True)
            time.sleep(delay)
        elif delay:
            time.sleep(delay)

    # Final reveal frame
    frames[-1] = base if not (cfg.outline or cfg.shadow) else frames[-1]

    # Live final render (if not exporting only)
    if not export_only:
        scheme = "none" if cfg.monochrome else cfg.gradient
        styled = colorize_block(frames[-1], scheme, cfg.gradient_dir)
        console.print("\x1b[H", end="")
        for tl in styled:
            tl.stylize("bold")
            console.print(tl, overflow="crop", no_wrap=True)
        console.print("\n[green]Done.[/green] Press Enter to return to menu.")
        try: input()
        except EOFError: pass

    # Export if requested
    if cfg.export_path:
        console.print(f"[cyan]Exporting to {cfg.export_path}…[/cyan]")
        export_animation(frames, scheme if not cfg.monochrome else "none", cfg.gradient_dir,
                         cfg.export_path, cfg.fps, cfg.outline, cfg.shadow)
        console.print(f"[green]Saved {cfg.export_path}[/green]")

# -------------------------- Main Menu --------------------------

def main_menu():
    cfg = load_config()
    while True:
        console.clear()
        header(cfg)
        preview(cfg)

        menu = Table.grid(padding=1)
        menu.add_row("[bold]1[/bold] Set text / image", "[bold]2[/bold] Font / width / align", "[bold]3[/bold] Gradients")
        menu.add_row("[bold]4[/bold] Mode & timings",  "[bold]5[/bold] Effects (outline/shadow)", "[bold]6[/bold] Layout & accessibility")
        menu.add_row("[bold]7[/bold] Export (GIF/MP4)", "[bold]8[/bold] Run animation", "[bold]9[/bold] Save profile")
        menu.add_row("[bold]0[/bold] Exit", "", "")
        console.print(Panel(menu, title="Menu", border_style="blue"))

        choice = Prompt.ask("Select", choices=[str(i) for i in range(10)], default="8")

        if choice == "1":
            use_img = Confirm.ask("Use ASCII image mode instead of FIGlet text?", default=cfg.use_image)
            cfg.use_image = use_img
            if use_img:
                p = Prompt.ask("Image path", default=(cfg.image_path or ""))
                cfg.image_path = p if p.strip() else None
                iw = IntPrompt.ask("ASCII image width (40..300)", default=cfg.image_width)
                cfg.image_width = clamp(iw, 40, 300)
            else:
                msg = Prompt.ask("Enter message (\\n for newline)", default=cfg.message.replace("\n","\\n"))
                cfg.message = msg.replace("\\n","\n")
        elif choice == "2":
            sub = Prompt.ask("a) choose font  b) search font  c) set width/align", choices=["a","b","c"], default="a")
            if sub == "a":
                picked = list_fonts_paginated()
                if picked: cfg.font = picked
            elif sub == "b":
                q = Prompt.ask("Substring to search")
                fonts = [f for f in FigletFont.getFonts() if q.lower() in f.lower()]
                if not fonts:
                    console.print("[red]No matches[/red]"); time.sleep(1)
                else:
                    console.print(", ".join(fonts[:30]))
                    pick = Prompt.ask("Type exact font name or 'back'", default="back")
                    if pick in fonts: cfg.font = pick
            else:
                w = IntPrompt.ask("FIGlet width (40..300)", default=cfg.width)
                a = Prompt.ask("Align", choices=["left","center","right"], default=cfg.align)
                cfg.width, cfg.align = clamp(w,40,300), a
        elif choice == "3":
            g = Prompt.ask("Gradient", choices=GRADIENTS, default=cfg.gradient)
            d = Prompt.ask("Direction", choices=GRADIENT_DIRS, default=cfg.gradient_dir)
            mono = Confirm.ask("Monochrome (ignore gradient colors)?", default=cfg.monochrome)
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
            else:
                gi = float(Prompt.ask("Glitch intensity 0..1", default=str(cfg.glitch_intensity)))
                cfg.glitch_intensity = clamp(gi, 0.0, 1.0)
            if Confirm.ask("Use a fixed random seed?", default=(cfg.seed is not None)):
                seed = IntPrompt.ask("Seed", default=cfg.seed if cfg.seed is not None else 1337)
                cfg.seed = int(seed)
            else:
                cfg.seed = None
        elif choice == "5":
            cfg.outline = Confirm.ask("Outline on?", default=cfg.outline)
            cfg.shadow  = Confirm.ask("Shadow on?",  default=cfg.shadow)
        elif choice == "6":
            cfg.auto_center   = Confirm.ask("Auto center to terminal?", default=cfg.auto_center)
            cfg.high_contrast = Confirm.ask("High-contrast (thicker outline/shadow)?", default=cfg.high_contrast)
            # If high contrast, tweak outline char/shadow density (implicit in render_frame_to_image / color only)
            # Monochrome handled under gradients menu
        elif choice == "7":
            path = Prompt.ask("Export path (.gif or .mp4), blank to disable", default=(cfg.export_path or ""))
            cfg.export_path = path.strip() or None
        elif choice == "8":
            cfg.clamp()
            run_animation(cfg)
        elif choice == "9":
            cfg.clamp()
            save_config(cfg)
            console.print(f"[green]Saved to {CFG_PATH}[/green]"); time.sleep(1)
        elif choice == "0":
            break

# -------------------------- Entrypoint --------------------------

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[dim]Bye.[/dim]")
