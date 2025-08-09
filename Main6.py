#!/usr/bin/env python3
# ascii_cycle_scrambler_noflicker_turtle.py
# No-flicker ASCII-art scrambler + optional Turtle "scary face" endcard.
# Windows-friendly (ANSI enabled), multi-line input (.end), menu explains options.

import os, sys, time, random, string, ctypes, re

# ---------- Windows ANSI enable ----------
if os.name == "nt":
    kernel32 = ctypes.windll.kernel32
    h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
        kernel32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

# ---------- ANSI helpers ----------
RESET = "\x1b[0m"; BOLD = "\x1b[1m"; DIM = "\x1b[2m"
HIDE  = "\x1b[?25l"; SHOW = "\x1b[?25h"
ALT_ON  = "\x1b[?1049h"; ALT_OFF = "\x1b[?1049l"
def goto(r, c=1): return f"\x1b[{r};{c}H"
def rgb(r,g,b): return f"\x1b[38;2;{r};{g};{b}m"
def strip_ansi(s): return re.sub(r"\x1b\[[0-9;]*m", "", s)

# ---------- Palettes / Pools / Speeds ----------
PALETTES = {
    "matrix":   {"scramble":rgb(0,180,0),"active":rgb(255,220,0),"locked":rgb(0,255,120),"static":"\x1b[90m"},
    "neon":     {"scramble":rgb(255,0,200),"active":rgb(0,220,255),"locked":rgb(255,255,255),"static":"\x1b[90m"},
    "ice":      {"scramble":rgb(0,200,255),"active":rgb(80,130,255),"locked":rgb(230,240,255),"static":"\x1b[90m"},
    "sunset":   {"scramble":rgb(255,90,90),"active":rgb(255,190,60),"locked":rgb(255,240,220),"static":"\x1b[90m"},
    "cyberpunk":{"scramble":rgb(255,0,180),"active":rgb(0,255,255),"locked":rgb(255,255,255),"static":"\x1b[90m"},
    "aqua":     {"scramble":rgb(0,220,180),"active":rgb(0,180,255),"locked":rgb(220,255,255),"static":"\x1b[90m"},
    "mono":     {"scramble":"","active":"","locked":"","static":""},
}
RAINBOW = [rgb(255,80,80), rgb(255,180,60), rgb(120,220,80), rgb(60,200,220), rgb(80,120,255), rgb(200,100,255)]

POOLS = {
    "letters":        string.ascii_uppercase + " ",
    "letters+digits": string.ascii_uppercase + string.digits + " ",
    "alnum+punct":    string.ascii_uppercase + string.digits + " .,:!?-",
    "printable":      string.ascii_uppercase + string.digits + " .,:!?-",
}
SPEEDS = { "slow":30.0, "normal":60.0, "fast":90.0, "ludicrous":120.0 }

# Quick scene presets (theme, pool, speed, stagger, rainbow)
PRESETS = {
    "Matrix":     ("matrix", "letters+digits", "fast", 0.08, False),
    "NeonSign":   ("neon",   "alnum+punct",    "normal", 0.12, True),
    "IceClean":   ("ice",    "letters",        "normal", 0.10, False),
    "CyberBurst": ("cyberpunk","alnum+punct",  "ludicrous", 0.06, True),
    "MonoQuiet":  ("mono",   "letters",        "slow", 0.12, False),
}

# ---------- 5x6 ASCII font ----------
FH, FW = 6, 5
def G(*rows): return [r for r in rows]
FONT = {
    "A": G(" ### ","#   #","#   #","#####","#   #","#   #"),
    "B": G("#### ","#   #","#### ","#   #","#   #","#### "),
    "C": G(" ### ","#   #","#    ","#    ","#   #"," ### "),
    "D": G("#### ","#   #","#   #","#   #","#   #","#### "),
    "E": G("#####","#    ","#### ","#    ","#    ","#####"),
    "F": G("#####","#    ","#### ","#    ","#    ","#    "),
    "G": G(" ### ","#   #","#    ","#  ##","#   #"," ####"),
    "H": G("#   #","#   #","#####","#   #","#   #","#   #"),
    "I": G(" ### ","  #  ","  #  ","  #  ","  #  "," ### "),
    "J": G("  ###","   # ","   # ","   # ","#  # "," ##  "),
    "K": G("#  ##","# #  ","##   ","# #  ","#  # ","#   #"),
    "L": G("#    ","#    ","#    ","#    ","#    ","#####"),
    "M": G("#   #","## ##","# # #","#   #","#   #","#   #"),
    "N": G("#   #","##  #","# # #","#  ##","#   #","#   #"),
    "O": G(" ### ","#   #","#   #","#   #","#   #"," ### "),
    "P": G("#### ","#   #","#### ","#    ","#    ","#    "),
    "Q": G(" ### ","#   #","#   #","# # #","#  # "," ## #"),
    "R": G("#### ","#   #","#### ","# #  ","#  # ","#   #"),
    "S": G(" ####","#    "," ### ","    #","#   #"," ### "),
    "T": G("#####","  #  ","  #  ","  #  ","  #  ","  #  "),
    "U": G("#   #","#   #","#   #","#   #","#   #"," ### "),
    "V": G("#   #","#   #","#   #"," # # "," # # ","  #  "),
    "W": G("#   #","#   #","# # #","# # #","## ##","#   #"),
    "X": G("#   #"," # # ","  #  ","  #  "," # # ","#   #"),
    "Y": G("#   #"," # # ","  #  ","  #  ","  #  ","  #  "),
    "Z": G("#####","   # ","  #  "," #   ","#    ","#####"),
    "0": G(" ### ","#  ##","# # #","##  #","#   #"," ### "),
    "1": G("  #  "," ##  ","  #  ","  #  ","  #  "," ### "),
    "2": G(" ### ","#   #","   # ","  #  "," #   ","#####"),
    "3": G("#### ","    #"," ### ","    #","#   #"," ### "),
    "4": G("#   #","#   #","#####","    #","    #","    #"),
    "5": G("#####","#    ","#### ","    #","#   #"," ### "),
    "6": G(" ### ","#    ","#### ","#   #","#   #"," ### "),
    "7": G("#####","    #","   # ","  #  ","  #  ","  #  "),
    "8": G(" ### ","#   #"," ### ","#   #","#   #"," ### "),
    "9": G(" ### ","#   #","#   #"," ####","    #"," ### "),
    " ": G("     ","     ","     ","     ","     ","     "),
    ".": G("     ","     ","     ","     ","  ## ","  ## "),
    ",": G("     ","     ","     ","     ","  ## ","  #  "),
    ":": G("     ","  ## ","  ## ","     ","  ## ","  ## "),
    "!": G("  #  ","  #  ","  #  ","  #  ","     ","  #  "),
    "?": G(" ### ","#   #","   # ","  #  ","     ","  #  "),
    "-": G("     ","     "," ### ","     ","     ","     "),
}
def glyph(ch): return FONT.get(ch.upper(), FONT["-"])

# ---- Glyph cache (faster) ----
GLYPH_CACHE = {}
def glyph_plain(ch):
    ch = ch.upper()
    g = GLYPH_CACHE.get(ch)
    if g is None:
        base = glyph(ch)
        g = [row.replace("#","█") for row in base]
        GLYPH_CACHE[ch] = g
    return g

# ---------- Rendering ----------
def render_line_ascii(line, color_seq=None):
    rows = [""] * FH
    for idx, ch in enumerate(line):
        g = glyph_plain(ch)
        color = (color_seq[idx] if (color_seq and idx < len(color_seq)) else "")
        reset = RESET if color else ""
        for r in range(FH):
            rows[r] += color + g[r] + reset + " "
    return rows

def build_alphabet(target, pool_key):
    base = POOLS.get(pool_key, POOLS["alnum+punct"])
    extra = "".join(sorted(set(target.upper().replace("\n",""))))
    return "".join(sorted(set(base + extra)))

# ---- Flicker-free renderer (delta updates) ----
class Renderer:
    def __init__(self, use_alt_screen=True):
        self.prev = []
        self.use_alt = use_alt_screen
        self.height = 0

    def begin(self):
        if self.use_alt:
            sys.stdout.write(ALT_ON)
        sys.stdout.write(HIDE + goto(1,1))
        sys.stdout.flush()

    def draw(self, lines):
        # Bail if identical to previous frame
        if lines == self.prev:
            return
        widths = [len(strip_ansi(l)) for l in lines]
        width = max(widths) if widths else 0
        padded = [l + " " * (width - len(strip_ansi(l))) for l in lines]

        max_rows = max(len(self.prev), len(padded))
        for row in range(1, max_rows + 1):
            new_line = padded[row-1] if row-1 < len(padded) else ""
            old_line = self.prev[row-1] if row-1 < len(self.prev) else None
            if new_line != old_line:
                sys.stdout.write(goto(row, 1) + new_line + RESET)

        if len(padded) < len(self.prev):
            for row in range(len(padded)+1, len(self.prev)+1):
                sys.stdout.write(goto(row, 1) + " " * len(strip_ansi(self.prev[row-1])))

        self.prev = padded
        self.height = max_rows
        sys.stdout.flush()

    def end(self):
        sys.stdout.write(goto(self.height + 1, 1) + SHOW)
        if self.use_alt:
            sys.stdout.write(ALT_OFF)
        sys.stdout.flush()

# ---------- Animations ----------
def animate_scramble_ascii(text, pal, pool_key, fps, stagger, rainbow_active, renderer):
    alphabet = build_alphabet(text, pool_key)
    lines = text.split("\n")

    states = []
    tries = []
    for ln in lines:
        tgt = list(ln.upper())
        disp = [random.choice(alphabet) if c != "" else "" for c in tgt]
        locked = [False for _ in tgt]
        tries.append([0]*len(tgt))
        states.append([tgt, disp, locked])

    fps = max(1.0, fps)
    target_dt = 1.0 / fps
    hue = 0
    start = time.perf_counter()

    renderer.begin()
    try:
        while True:
            frame_start = time.perf_counter()
            all_done = True
            for li, (tgt, disp, locked) in enumerate(states):
                if time.perf_counter() < start + li*stagger:
                    all_done = all_done and all(locked); continue
                try:
                    i = locked.index(False)
                except ValueError:
                    continue
                all_done = False
                # Bias toward target over time (smooth progress)
                tries[li][i] += 1
                bias = min(0.85, 0.15 + tries[li][i]*0.02)
                if random.random() < bias:
                    pick = tgt[i]
                else:
                    pick = " " if tgt[i] == " " else random.choice(alphabet)
                disp[i] = pick
                if pick == tgt[i]:
                    locked[i] = True

            # Build frame (use SELECTED palette!)
            ascii_rows = []
            for (tgt, disp, locked) in states:
                try: active_i = locked.index(False)
                except ValueError: active_i = -1
                colors = []
                for j, ch in enumerate(disp):
                    if j == active_i and active_i != -1:
                        c = (RAINBOW[hue % len(RAINBOW)] if rainbow_active else pal["active"])
                    elif locked[j]:
                        c = pal["locked"]
                    else:
                        c = pal["scramble"]
                    colors.append(c)
                for r in render_line_ascii("".join(disp), colors):
                    ascii_rows.append(r)
                ascii_rows.append("")  # spacer

            renderer.draw(ascii_rows)
            if all_done: break
            hue += 1

            # Adaptive sleep to hit target FPS
            elapsed = time.perf_counter() - frame_start
            to_sleep = target_dt - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
        renderer.draw(ascii_rows)
    finally:
        renderer.end()

def animate_typewriter_ascii(text, pal, fps, renderer, delay_scale=1.0):
    lines = text.split("\n")
    shown = ["" for _ in lines]
    r, c = 0, 0
    fps = max(1.0, fps)
    target_dt = 1.0 / fps
    renderer.begin()
    try:
        while r < len(lines):
            frame_start = time.perf_counter()
            line_up = lines[r].upper()
            if c <= len(line_up):
                shown[r] = line_up[:c]; c += 1
            else:
                r += 1; c = 0; continue
            ascii_rows = []
            for ln in shown:
                art_rows = render_line_ascii(ln, [pal["locked"]] * len(ln))
                ascii_rows.extend(art_rows); ascii_rows.append("")
            renderer.draw(ascii_rows)

            elapsed = time.perf_counter() - frame_start
            to_sleep = (target_dt * delay_scale) - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
        renderer.draw(ascii_rows)
    finally:
        renderer.end()

# ---------- Turtle endcard (fullscreen, waits for Esc/click) ----------
def endcard_turtle_skull(fullscreen=True, bg=(5,5,8), glow_secs=3.0):
    try:
        import turtle
    except Exception as e:
        print(f"(Turtle unavailable: {e})"); return

    scr = turtle.Screen()
    turtle.colormode(255)
    scr.bgcolor(bg)
    if fullscreen:
        try:
            root = scr._root
            root.attributes("-fullscreen", True)
        except Exception:
            scr.setup(width=1.0, height=1.0)
    else:
        scr.setup(width=960, height=720)

    t = turtle.Turtle(visible=False); t.speed(0)
    turtle.tracer(False)

    def fill_circle(x, y, r, color):
        t.up(); t.goto(x, y - r); t.setheading(0)
        t.color(color); t.fillcolor(color)
        t.down(); t.begin_fill(); t.circle(r); t.end_fill(); t.up()

    def fill_poly(points, color):
        t.up(); t.goto(points[0]); t.color(color); t.fillcolor(color)
        t.down(); t.begin_fill()
        for p in points[1:]: t.goto(p)
        t.goto(points[0]); t.end_fill(); t.up()

    # Scale to window
    try: w, h = scr.window_width(), scr.window_height()
    except Exception: w, h = 1280, 720
    S = max(min(h, w) / 5.0, 120)

    skull = (240,240,240); jaw=(225,225,225); hole=(25,25,25)

    fill_circle(0, 0, int(1.1*S), skull)
    fill_poly([(-1.0*S, -0.3*S), (-0.5*S, -0.95*S), (0.5*S, -0.95*S), (1.0*S, -0.3*S)], jaw)

    eye_outer_r = int(0.28*S); eye_inner_r = int(0.16*S)
    eye_y = int(0.35*S); eye_dx = int(0.55*S)
    fill_circle(-eye_dx, eye_y, eye_outer_r, hole)
    fill_circle( eye_dx, eye_y, eye_outer_r, hole)

    fill_poly([(-0.15*S, 0.0), (0.15*S, 0.0), (0.0, -0.25*S)], hole)

    t.color(210,210,210); t.width(int(max(2, S/30)))
    t.goto(-0.8*S, -0.55*S); t.setheading(0); t.down(); t.forward(1.6*S); t.up()
    t.setheading(90)
    for k in range(-6, 7, 2):
        x = (k/8.0) * 0.8 * S
        t.goto(x, -0.55*S); t.setheading(-90); t.down(); t.forward(0.25*S); t.up()

    turtle.update()

    # Glow pulse
    glow = turtle.Turtle(visible=False); glow.speed(0)
    left_eye  = (-eye_dx, eye_y + int(0.08*S))
    right_eye = ( eye_dx, eye_y + int(0.08*S))
    start = time.time()
    while time.time() - start < glow_secs:
        strength = int(120 + 120 * abs((time.time()*5) % 2 - 1))
        glow.clear()
        for (x, y) in (left_eye, right_eye):
            fill_circle(x, y, eye_inner_r, (0, strength, 220))
        turtle.update()
        time.sleep(0.05)

    def _exit(*_):
        try:
            root = scr._root
            root.attributes("-fullscreen", False)
        except Exception:
            pass
        try:
            scr.bye()
        except Exception:
            pass

    scr.listen()
    scr.onkey(_exit, "Escape")
    scr.onclick(lambda *_: _exit())
    turtle.mainloop()

# ---------- Input / Menu ----------
def read_multiline():
    print("\nType/paste your text (multi-line OK).")
    print(f"When finished, enter a single line with {BOLD}.end{RESET} and press Enter.\n")
    buf = []
    while True:
        try: line = input()
        except EOFError: break
        if line.strip() == ".end": break
        buf.append(line)
    return "\n".join(buf)

def explain_menu():
    print("\n" + BOLD + "Menu: what each option does" + RESET)
    print(BOLD + "1) Edit text" + RESET + " – Paste or type multi-line text. End with '.end'.")
    print(BOLD + "2) Palette" + RESET + " – Color theme for scramble/active/locked/static.")
    print(BOLD + "3) Pool" + RESET + " – Random characters used while scrambling (targets always included).")
    print("   Options: letters, letters+digits, alnum+punct, printable.")
    print(BOLD + "4) Speed" + RESET + " – Frames per second (higher = smoother/faster).")
    print(BOLD + "5) Stagger" + RESET + " – Seconds to delay each subsequent line.")
    print(BOLD + "6) Mode" + RESET + " – 'scramble' (random until match) or 'typewriter' (one-by-one).")
    print(BOLD + "7) Rainbow active" + RESET + " – Toggle rainbow shimmer on the active character.")
    print(BOLD + "8) Alt screen" + RESET + " – Toggle alternate screen buffer (reduces flicker).")
    print(BOLD + "9) Endcard" + RESET + " – Off or Turtle skull after animation completes.")
    print(BOLD + "P) Presets" + RESET + " – Quick scene selection (theme, pool, speed, stagger, rainbow).")
    input("\nPress Enter to return…")

def apply_preset(name, cur):
    theme, pool, speed, stagger, rainbow = PRESETS[name]
    return theme, pool, speed, stagger, rainbow

def main():
    text = "ZERODAY LABS\nASCII CYCLE\nMULTI-LINE OK"
    theme = "cyberpunk"
    pool = "alnum+punct"
    speed = "normal"
    stagger = 0.12
    mode = "scramble"
    rainbow = True
    use_alt = True
    endcard = "off"  # off | turtle-skull

    while True:
        sys.stdout.write("\x1b[2J" + goto(1,1))
        print(BOLD + "ASCII Art Text Animator (no-flicker) + Turtle Endcard" + RESET)
        print(DIM + "Delta redraw; adaptive FPS; bias-to-target; multi-line; Windows-friendly." + RESET + "\n")
        print(f"{BOLD}1){RESET} Edit text ({len(text)} chars, {text.count('\\n')+1} line(s))")
        print(f"{BOLD}2){RESET} Palette: {theme}")
        print(f"{BOLD}3){RESET} Pool: {pool}")
        print(f"{BOLD}4){RESET} Speed: {speed} ({SPEEDS[speed]} FPS)")
        print(f"{BOLD}5){RESET} Line stagger: {stagger:.2f} s")
        print(f"{BOLD}6){RESET} Mode: {mode}  [scramble | typewriter]")
        print(f"{BOLD}7){RESET} Rainbow active: {'on' if rainbow else 'off'}")
        print(f"{BOLD}8){RESET} Alt screen: {'on' if use_alt else 'off'}")
        print(f"{BOLD}9){RESET} Endcard: {endcard}  [off | turtle-skull]")
        print(f"{BOLD}P){RESET} Presets")
        print(f"{BOLD}H){RESET} Help")
        print(f"{BOLD}R){RESET} Run")
        print(f"{BOLD}Q){RESET} Quit\n")
        sel = input("Select: ").strip().lower()

        if sel == "1":
            t = read_multiline()
            if t.strip(): text = t
        elif sel == "2":
            print("\nPalettes:", ", ".join(PALETTES.keys()))
            s = input(f"Choose palette [{theme}]: ").strip().lower() or theme
            if s in PALETTES: theme = s
        elif sel == "3":
            print("\nPools:", ", ".join(POOLS.keys()))
            s = input(f"Choose pool [{pool}]: ").strip().lower() or pool
            if s in POOLS: pool = s
        elif sel == "4":
            print("\nSpeeds:", ", ".join(SPEEDS.keys()))
            s = input(f"Choose speed [{speed}]: ").strip().lower() or speed
            if s in SPEEDS: speed = s
        elif sel == "5":
            try: stagger = max(0.0, float(input("Seconds between line starts (e.g., 0.10): ").strip()))
            except ValueError: pass
        elif sel == "6":
            s = input("Mode [scramble | typewriter]: ").strip().lower() or mode
            if s in ("scramble","typewriter"): mode = s
        elif sel == "7":
            rainbow = not rainbow
        elif sel == "8":
            use_alt = not use_alt
        elif sel == "9":
            s = input("Endcard [off | turtle-skull]: ").strip().lower() or endcard
            if s in ("off","turtle-skull"): endcard = s
        elif sel == "p":
            print("\nPresets:", ", ".join(PRESETS.keys()))
            name = input("Choose preset: ").strip()
            if name in PRESETS:
                theme, pool, speed, stagger, rainbow = apply_preset(name, (theme, pool, speed, stagger, rainbow))
        elif sel == "h":
            explain_menu()
        elif sel == "r":
            pal = PALETTES.get(theme, PALETTES["cyberpunk"])
            renderer = Renderer(use_alt_screen=use_alt)
            try:
                if mode == "scramble":
                    animate_scramble_ascii(text, pal, pool, SPEEDS[speed], stagger, rainbow, renderer)
                else:
                    delay_scale = 0.9 if speed=="fast" else (0.7 if speed=="ludicrous" else 1.0)
                    animate_typewriter_ascii(text, pal, SPEEDS[speed], renderer, delay_scale=delay_scale)
            except KeyboardInterrupt:
                renderer.end()

            # Endcard
            if endcard == "turtle-skull":
                print("\nLaunching skull… (Esc or click to exit)")
                try:
                    endcard_turtle_skull(fullscreen=True, glow_secs=3.0)
                except Exception as e:
                    print(f"(Turtle endcard failed: {e})")
            input("\nDone. Press Enter to return…")
        elif sel == "q":
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
