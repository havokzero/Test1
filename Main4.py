#!/usr/bin/env python3
# ascii_cycle_scrambler_noflicker.py
# Windows-friendly, color ASCII art animator with NO FLICKER:
# - Delta renderer: only redraw changed rows
# - Fixed-width padding per frame to avoid wrap/jitter
# - Optional alternate screen buffer
#
# Modes: "scramble" (random until match) and "typewriter".
# Multi-line input supported (.end). Menu explains options.

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

# ---------- Palettes ----------
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

# ---------- Pools / Speeds ----------
POOLS = {
    "letters":        string.ascii_uppercase + " ",
    "letters+digits": string.ascii_uppercase + string.digits + " ",
    "alnum+punct":    string.ascii_uppercase + string.digits + " .,:!?-",
    "printable":      string.ascii_uppercase + string.digits + " .,:!?-",
}
SPEEDS = { "slow":30.0, "normal":60.0, "fast":90.0, "ludicrous":120.0 }

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

# ---------- Rendering ----------
def render_line_ascii(line, color_seq=None):
    rows = [""] * FH
    for idx, ch in enumerate(line):
        g = glyph(ch)
        color = (color_seq[idx] if (color_seq and idx < len(color_seq)) else "")
        reset = RESET if color else ""
        for r in range(FH):
            rows[r] += color + g[r].replace("#", "█") + reset + " "
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
        """lines: list[str] already fully padded to fixed width for this frame"""
        # Pad to equal width to prevent wrap
        widths = [len(strip_ansi(l)) for l in lines]
        width = max(widths) if widths else 0
        padded = [l + " " * (width - len(strip_ansi(l))) for l in lines]

        # Erase extra previous rows if new frame has fewer lines
        max_rows = max(len(self.prev), len(padded))
        for row in range(1, max_rows + 1):
            new_line = padded[row-1] if row-1 < len(padded) else ""
            old_line = self.prev[row-1] if row-1 < len(self.prev) else None
            if new_line != old_line:
                sys.stdout.write(goto(row, 1) + new_line + RESET)

        # If new frame has fewer lines, blank the leftover old rows
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

# ---------- Animations (using Renderer) ----------
def animate_scramble_ascii(text, pal, pool_key, fps, stagger, rainbow_active, renderer):
    alphabet = build_alphabet(text, pool_key)
    lines = text.split("\n")
    # states per line
    states = []
    for ln in lines:
        tgt = list(ln.upper())
        disp = [random.choice(alphabet) if c != "" else "" for c in tgt]
        locked = [False for _ in tgt]
        states.append([tgt, disp, locked])

    fps = max(1.0, fps); frame_time = 1.0 / fps
    hue = 0
    start = time.perf_counter()

    renderer.begin()
    try:
        while True:
            all_done = True
            # update
            for li, (tgt, disp, locked) in enumerate(states):
                if time.perf_counter() < start + li*stagger:
                    all_done = all_done and all(locked)
                    continue
                try:
                    i = locked.index(False)
                except ValueError:
                    continue
                all_done = False
                pick = " " if tgt[i] == " " else random.choice(alphabet)
                disp[i] = pick
                if pick == tgt[i]:
                    locked[i] = True

            # render frame (delta)
            ascii_rows = []
            for (tgt, disp, locked) in states:
                # per-char colors
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
                ascii_rows.append("")  # spacer row

            renderer.draw(ascii_rows)
            if all_done:
                break
            hue += 1
            time.sleep(frame_time)
        # leave cursor after the block
        renderer.draw(ascii_rows)
    finally:
        renderer.end()

def animate_typewriter_ascii(text, pal, fps, renderer, delay_scale=1.0):
    lines = text.split("\n")
    shown = ["" for _ in lines]
    r, c = 0, 0
    fps = max(1.0, fps); frame_time = 1.0 / fps
    renderer.begin()
    try:
        while r < len(lines):
            line_up = lines[r].upper()
            if c <= len(line_up):
                shown[r] = line_up[:c]
                c += 1
            else:
                r += 1; c = 0; continue

            ascii_rows = []
            for ln in shown:
                art_rows = render_line_ascii(ln, [pal["locked"]] * len(ln))
                ascii_rows.extend(art_rows)
                ascii_rows.append("")
            renderer.draw(ascii_rows)
            time.sleep(frame_time * delay_scale)
        renderer.draw(ascii_rows)
    finally:
        renderer.end()

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
    print(BOLD + "8) Alt screen" + RESET + " – Toggle alternate screen buffer (can reduce flicker further).")
    input("\nPress Enter to return…")

def main():
    text = "ZERODAY LABS\nASCII CYCLE\nMULTI-LINE OK"
    theme = "cyberpunk"
    pool = "alnum+punct"
    speed = "normal"
    stagger = 0.12
    mode = "scramble"
    rainbow = True
    use_alt = True  # alternate screen buffer

    while True:
        sys.stdout.write("\x1b[2J" + goto(1,1))
        print(BOLD + "ASCII Art Text Animator (no-flicker)" + RESET)
        print(DIM + "Delta redraw + fixed width padding; multi-line; colors; Windows-friendly." + RESET + "\n")
        print(f"{BOLD}1){RESET} Edit text ({len(text)} chars, {text.count('\\n')+1} line(s))")
        print(f"{BOLD}2){RESET} Palette: {theme}")
        print(f"{BOLD}3){RESET} Pool: {pool}")
        print(f"{BOLD}4){RESET} Speed: {speed} ({SPEEDS[speed]} FPS)")
        print(f"{BOLD}5){RESET} Line stagger: {stagger:.2f} s")
        print(f"{BOLD}6){RESET} Mode: {mode}  [scramble | typewriter]")
        print(f"{BOLD}7){RESET} Rainbow active: {'on' if rainbow else 'off'}")
        print(f"{BOLD}8){RESET} Alt screen: {'on' if use_alt else 'off'}")
        print(f"{BOLD}9){RESET} Help")
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
            input("\nDone. Press Enter to return…")
        elif sel == "q":
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
