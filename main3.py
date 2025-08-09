#!/usr/bin/env python3
# ascii_cycle_scrambler.py
# Windows-friendly, ANSI color, multi-line input, menu with explanations.
# Animates your text as ASCII ART: each character flips randomly until it matches, left-to-right.

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
HIDE  = "\x1b[?25l"; SHOW = "\x1b[?25h"; CLEAR = "\x1b[2J"; HOME = "\x1b[H"
def rgb(r,g,b): return f"\x1b[38;2;{r};{g};{b}m"

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

# ---------- Character pools for the RANDOM picks (we always include target chars) ----------
POOLS = {
    "letters":        string.ascii_uppercase + " ",
    "letters+digits": string.ascii_uppercase + string.digits + " ",
    "alnum+punct":    string.ascii_uppercase + string.digits + " .,:!?-",
    "printable":      string.ascii_uppercase + string.digits + " .,:!?-",
}
SPEEDS = { "slow":30.0, "normal":60.0, "fast":90.0, "ludicrous":120.0 }

# ---------- Tiny 5x6 ASCII font (uppercase A–Z, 0–9, space and .,:!?-) ----------
# Each glyph is 6 rows of 5 chars (use '█' blocks + spaces). Keep ASCII by using '#'.
FH, FW = 6, 5
def G(*rows): return [r for r in rows]  # helper

FONT = {
    "A": G(" ### ",
           "#   #",
           "#   #",
           "#####",
           "#   #",
           "#   #"),
    "B": G("#### ",
           "#   #",
           "#### ",
           "#   #",
           "#   #",
           "#### "),
    "C": G(" ### ",
           "#   #",
           "#    ",
           "#    ",
           "#   #",
           " ### "),
    "D": G("#### ",
           "#   #",
           "#   #",
           "#   #",
           "#   #",
           "#### "),
    "E": G("#####",
           "#    ",
           "#### ",
           "#    ",
           "#    ",
           "#####"),
    "F": G("#####",
           "#    ",
           "#### ",
           "#    ",
           "#    ",
           "#    "),
    "G": G(" ### ",
           "#   #",
           "#    ",
           "#  ##",
           "#   #",
           " ####"),
    "H": G("#   #",
           "#   #",
           "#####",
           "#   #",
           "#   #",
           "#   #"),
    "I": G(" ### ",
           "  #  ",
           "  #  ",
           "  #  ",
           "  #  ",
           " ### "),
    "J": G("  ###",
           "   # ",
           "   # ",
           "   # ",
           "#  # ",
           " ##  "),
    "K": G("#  ##",
           "# #  ",
           "##   ",
           "# #  ",
           "#  # ",
           "#   #"),
    "L": G("#    ",
           "#    ",
           "#    ",
           "#    ",
           "#    ",
           "#####"),
    "M": G("#   #",
           "## ##",
           "# # #",
           "#   #",
           "#   #",
           "#   #"),
    "N": G("#   #",
           "##  #",
           "# # #",
           "#  ##",
           "#   #",
           "#   #"),
    "O": G(" ### ",
           "#   #",
           "#   #",
           "#   #",
           "#   #",
           " ### "),
    "P": G("#### ",
           "#   #",
           "#### ",
           "#    ",
           "#    ",
           "#    "),
    "Q": G(" ### ",
           "#   #",
           "#   #",
           "# # #",
           "#  # ",
           " ## #"),
    "R": G("#### ",
           "#   #",
           "#### ",
           "# #  ",
           "#  # ",
           "#   #"),
    "S": G(" ####",
           "#    ",
           " ### ",
           "    #",
           "#   #",
           " ### "),
    "T": G("#####",
           "  #  ",
           "  #  ",
           "  #  ",
           "  #  ",
           "  #  "),
    "U": G("#   #",
           "#   #",
           "#   #",
           "#   #",
           "#   #",
           " ### "),
    "V": G("#   #",
           "#   #",
           "#   #",
           " # # ",
           " # # ",
           "  #  "),
    "W": G("#   #",
           "#   #",
           "# # #",
           "# # #",
           "## ##",
           "#   #"),
    "X": G("#   #",
           " # # ",
           "  #  ",
           "  #  ",
           " # # ",
           "#   #"),
    "Y": G("#   #",
           " # # ",
           "  #  ",
           "  #  ",
           "  #  ",
           "  #  "),
    "Z": G("#####",
           "   # ",
           "  #  ",
           " #   ",
           "#    ",
           "#####"),
    "0": G(" ### ",
           "#  ##",
           "# # #",
           "##  #",
           "#   #",
           " ### "),
    "1": G("  #  ",
           " ##  ",
           "  #  ",
           "  #  ",
           "  #  ",
           " ### "),
    "2": G(" ### ",
           "#   #",
           "   # ",
           "  #  ",
           " #   ",
           "#####"),
    "3": G("#### ",
           "    #",
           " ### ",
           "    #",
           "#   #",
           " ### "),
    "4": G("#   #",
           "#   #",
           "#####",
           "    #",
           "    #",
           "    #"),
    "5": G("#####",
           "#    ",
           "#### ",
           "    #",
           "#   #",
           " ### "),
    "6": G(" ### ",
           "#    ",
           "#### ",
           "#   #",
           "#   #",
           " ### "),
    "7": G("#####",
           "    #",
           "   # ",
           "  #  ",
           "  #  ",
           "  #  "),
    "8": G(" ### ",
           "#   #",
           " ### ",
           "#   #",
           "#   #",
           " ### "),
    "9": G(" ### ",
           "#   #",
           "#   #",
           " ####",
           "    #",
           " ### "),
    " ": G("     ","     ","     ","     ","     ","     "),
    ".": G("     ","     ","     ","     ","  ## ","  ## "),
    ",": G("     ","     ","     ","     ","  ## ","  #  "),
    ":": G("     ","  ## ","  ## ","     ","  ## ","  ## "),
    "!": G("  #  ","  #  ","  #  ","  #  ","     ","  #  "),
    "?": G(" ### ","#   #","   # ","  #  ","     ","  #  "),
    "-": G("     ","     "," ### ","     ","     ","     "),
}

def glyph(ch):
    ch = ch.upper()
    return FONT.get(ch, FONT["?"] if "?" in FONT else FONT["#"] if "#" in FONT else FONT["-"])

# ---------- Render a string (single line) into ASCII art rows, with optional color per character ----------
def render_line_ascii(line, color_seq=None):
    # color_seq: list of ANSI color prefixes per character (length == len(line)) or None for no per-char color
    rows = [""] * FH
    for idx, ch in enumerate(line):
        g = glyph(ch)
        color = color_seq[idx] if (color_seq and idx < len(color_seq)) else ""
        reset = RESET if color else ""
        for r in range(FH):
            # Replace '#' with block char; keep spaces as spaces
            rows[r] += color + g[r].replace("#", "█") + reset + " "
    return rows

def strip_ansi(s): return re.sub(r"\x1b\[[0-9;]*m", "", s)

# ---------- Build the random alphabet pool for flipping ----------
def build_alphabet(target, pool_key):
    base = POOLS.get(pool_key, POOLS["alnum+punct"])
    # include all unique chars from target to guarantee matchability
    extra = "".join(sorted(set(target.upper().replace("\n",""))))
    return "".join(sorted(set(base + extra)))

# ---------- Animation: Scramble → Lock (ASCII art) ----------
def animate_scramble_ascii(text, pal, pool_key, fps, stagger, rainbow_active):
    alphabet = build_alphabet(text, pool_key)
    # Work per line (multi-line)
    lines = text.split("\n")
    fps = max(1.0, fps)
    frame_time = 1.0 / fps
    hue = 0

    # For each line, we maintain display chars and lock states
    line_states = []
    for ln in lines:
        tgt = list(ln.upper())
        disp = [random.choice(alphabet) if c != "" else "" for c in tgt]
        locked = [False for _ in tgt]
        line_states.append([tgt, disp, locked])

    sys.stdout.write(HIDE)
    try:
        start = time.perf_counter()
        while True:
            all_done = True
            # Update logic (left-to-right per line)
            for li, (tgt, disp, locked) in enumerate(line_states):
                # apply stagger per line
                if time.perf_counter() < start + li*stagger:
                    continue
                # find next unlocked index
                try:
                    i = locked.index(False)
                except ValueError:
                    continue
                all_done = False
                pick = random.choice(alphabet) if tgt[i] != " " else " "
                disp[i] = pick
                if pick == tgt[i]:
                    locked[i] = True
            # Draw frame
            sys.stdout.write(CLEAR + HOME)
            out_rows = [""] * FH
            for li, (tgt, disp, locked) in enumerate(line_states):
                # Build per-char colors
                colors = []
                # active index (first False) if any
                try:
                    active_i = locked.index(False)
                except ValueError:
                    active_i = -1
                for j, ch in enumerate(disp):
                    if j == active_i and active_i != -1:
                        c = (RAINBOW[hue % len(RAINBOW)] if rainbow_active else pal["active"])
                    elif locked[j]:
                        c = pal["locked"]
                    else:
                        c = pal["scramble"]
                    colors.append(c)
                art_rows = render_line_ascii("".join(disp), colors)
                out_rows = [out_rows[r] + art_rows[r] for r in range(FH)]
                # blank row between ASCII lines
                out_rows.append("")
            # Print rows
            for r in out_rows:
                if r == "": print()
                else: print(r)
            sys.stdout.flush()
            if all_done:
                break
            time.sleep(frame_time)
            hue += 1
        print()
    finally:
        sys.stdout.write(SHOW + RESET)
        sys.stdout.flush()

# ---------- Animation: Typewriter (ASCII art) ----------
def animate_typewriter_ascii(text, pal, fps, border=False, delay_scale=1.0):
    # prints characters one-by-one as ASCII art; simpler coloring (locked color)
    lines = text.split("\n")
    shown = ["" for _ in lines]
    r, c = 0, 0
    fps = max(1.0, fps); frame_time = 1.0 / fps
    sys.stdout.write(HIDE)
    try:
        while r < len(lines):
            line_up = lines[r].upper()
            if c <= len(line_up):
                shown[r] = line_up[:c]
                c += 1
            else:
                r += 1; c = 0; continue
            # draw
            sys.stdout.write(CLEAR + HOME)
            out_rows = [""] * FH
            for ln in shown:
                art_rows = render_line_ascii(ln, [pal["locked"]] * len(ln))
                out_rows = [out_rows[i] + art_rows[i] for i in range(FH)]
                out_rows.append("")
            for rr in out_rows:
                print(rr)
            time.sleep(frame_time * delay_scale)
        print()
    finally:
        sys.stdout.write(SHOW + RESET)
        sys.stdout.flush()

# ---------- Input helpers ----------
def read_multiline():
    print("\nType/paste your text (multi-line OK).")
    print(f"When finished, enter a single line with {BOLD}.end{RESET} and press Enter.\n")
    buf = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".end":
            break
        buf.append(line)
    return "\n".join(buf)

def explain_menu():
    print(CLEAR + HOME + BOLD + "Menu: what each option does" + RESET + "\n")
    print(BOLD + "1) Edit text" + RESET + " – Paste or type multi-line text. End with '.end'.")
    print(BOLD + "2) Palette" + RESET + " – Choose the color theme for scramble/active/locked/static states.")
    print(BOLD + "3) Pool" + RESET + " – Random characters used while scrambling (always includes your target chars).")
    print("   Options: letters, letters+digits, alnum+punct, printable.")
    print(BOLD + "4) Speed" + RESET + " – Frames per second. Higher is smoother/faster animation.")
    print(BOLD + "5) Stagger" + RESET + " – Seconds to delay each subsequent line (0 = all lines start together).")
    print(BOLD + "6) Mode" + RESET + " – 'scramble' (random until match) or 'typewriter' (one-by-one).")
    print(BOLD + "7) Rainbow active" + RESET + " – Toggle a rainbow shimmer on the currently active character.")
    input("\nPress Enter to return…")

# ---------- Menu ----------
def main():
    text = "ZERODAY LABS\nASCII CYCLE\nMULTI-LINE OK"
    theme = "cyberpunk"
    pool = "alnum+punct"
    speed = "normal"
    stagger = 0.12
    mode = "scramble"   # or "typewriter"
    rainbow = True

    while True:
        print(CLEAR + HOME + BOLD + "ASCII Art Text Animator" + RESET)
        print(DIM + "No banner. Your text is rendered as big ASCII letters and animated." + RESET + "\n")
        print(f"{BOLD}1){RESET} Edit text ({len(text)} chars, {text.count('\\n')+1} line(s))")
        print(f"{BOLD}2){RESET} Palette: {theme}  " + DIM + "(colors)" + RESET)
        print(f"{BOLD}3){RESET} Pool: {pool}     " + DIM + "(random flip characters)" + RESET)
        print(f"{BOLD}4){RESET} Speed: {speed} ({SPEEDS[speed]} FPS)")
        print(f"{BOLD}5){RESET} Line stagger: {stagger:.2f} s")
        print(f"{BOLD}6){RESET} Mode: {mode}     " + DIM + "[scramble | typewriter]" + RESET)
        print(f"{BOLD}7){RESET} Rainbow active: {'on' if rainbow else 'off'}")
        print(f"{BOLD}8){RESET} Help (explain these)")
        print(f"{BOLD}9){RESET} Run")
        print(f"{BOLD}0){RESET} Exit\n")
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
            try:
                stagger = max(0.0, float(input("Seconds between line starts (e.g., 0.15): ").strip()))
            except ValueError:
                pass
        elif sel == "6":
            s = input("Mode [scramble | typewriter]: ").strip().lower() or mode
            if s in ("scramble","typewriter"): mode = s
        elif sel == "7":
            rainbow = not rainbow
        elif sel == "8":
            explain_menu()
        elif sel == "9":
            pal = PALETTES.get(theme, PALETTES["cyberpunk"])
            try:
                if mode == "scramble":
                    animate_scramble_ascii(text, pal, pool, SPEEDS[speed], stagger, rainbow)
                else:
                    animate_typewriter_ascii(text, pal, SPEEDS[speed], delay_scale=0.9 if speed=="fast" else (0.7 if speed=="ludicrous" else 1.0))
            except KeyboardInterrupt:
                pass
            input("\nDone. Press Enter to return to menu…")
        elif sel == "0":
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
