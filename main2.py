#!/usr/bin/env python3
# windows_color_scrambler.py
# Colorful, Windows-friendly, menu-driven "scramble until match" multi-line animator.

import os, sys, time, random, string, ctypes

# --- Enable ANSI/VT on Windows for colors and cursor control ---
if os.name == "nt":
    kernel32 = ctypes.windll.kernel32
    h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
        kernel32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

# --- ANSI helpers ---
RESET = "\x1b[0m"
BOLD  = "\x1b[1m"
DIM   = "\x1b[2m"
HIDE  = "\x1b[?25l"
SHOW  = "\x1b[?25h"
HOME  = "\x1b[H"
CLEAR = "\x1b[2J"

# --- Palettes (foreground colors) ---
PALETTES = {
    "matrix":   {"scramble":"\x1b[32m","active":"\x1b[93m","locked":"\x1b[92m","static":"\x1b[90m"},
    "neon":     {"scramble":"\x1b[95m","active":"\x1b[96m","locked":"\x1b[97m","static":"\x1b[90m"},
    "ice":      {"scramble":"\x1b[36m","active":"\x1b[94m","locked":"\x1b[97m","static":"\x1b[90m"},
    "sunset":   {"scramble":"\x1b[91m","active":"\x1b[93m","locked":"\x1b[97m","static":"\x1b[90m"},
    "mono":     {"scramble":"","active":"","locked":"","static":""},
}

# Optional rainbow tick for the active character
RAINBOW = ["\x1b[91m","\x1b[93m","\x1b[92m","\x1b[96m","\x1b[94m","\x1b[95m"]

# --- Character pools and speeds ---
POOLS = {
    "letters":         string.ascii_letters + " ",
    "letters+digits":  string.ascii_letters + string.digits + " ",
    "alnum+punct":     string.ascii_letters + string.digits + string.punctuation + " ",
    "printable":       "".join(ch for ch in string.printable if ch not in "\t\r\x0b\x0c"),
}

SPEEDS = {
    "slow":      30.0,
    "normal":    60.0,
    "fast":      90.0,
    "ludicrous": 120.0,
}

def colorize(ch: str, state: str, pal: dict, hue_idx: int, rainbow_active: bool) -> str:
    if state == "locked":
        return f"{pal['locked']}{ch}{RESET}"
    if state == "active":
        c = (RAINBOW[hue_idx % len(RAINBOW)] if rainbow_active and pal['active'] else pal['active'])
        return f"{c}{ch}{RESET}"
    if state == "scramble":
        return f"{pal['scramble']}{ch}{RESET}"
    return f"{pal['static']}{ch}{RESET}"

def build_alphabet(target: str, pool_key: str) -> str:
    base = POOLS.get(pool_key, POOLS["alnum+punct"])
    # include every unique character from the target (excluding newlines) to guarantee matchability
    extra = target.replace("\n", "")
    return "".join(sorted(set(base + extra)))

def animate_lockstep(target: str, palette_name: str, pool_key: str, fps: float,
                     per_line_stagger: float, rainbow_active: bool):
    pal = PALETTES.get(palette_name, PALETTES["matrix"])
    alphabet = build_alphabet(target, pool_key)

    chars   = list(target)
    locked  = [ch == "\n" for ch in chars]  # newlines are instantly locked
    display = [("\n" if ch == "\n" else random.choice(alphabet)) for ch in chars]
    indices = [i for i, ch in enumerate(chars) if ch != "\n"]
    if not indices:
        print(target)
        return

    # Per-line stagger (delay when each line is allowed to start resolving)
    lines = target.split("\n")
    line_starts = []
    pos = 0
    for ln in lines:
        line_starts.append(pos)
        pos += len(ln) + 1  # +1 for newline (even for last; our target usually ends with \n)

    next_allowed_time = {start: 0.0 for start in line_starts}
    t0 = time.perf_counter()
    for n, start in enumerate(line_starts):
        next_allowed_time[start] = t0 + n * per_line_stagger

    i_ptr = 0
    frame_time = 1.0 / max(1.0, fps)
    hue = 0

    sys.stdout.write(CLEAR + HOME + HIDE)
    try:
        while not all(locked):
            if not indices:
                break

            i_ptr %= len(indices)
            i = indices[i_ptr]

            # If this character's line hasn't been "released" yet, just draw a frame
            if line_starts:
                line_start = max(s for s in line_starts if s <= i)
                if time.perf_counter() < next_allowed_time.get(line_start, 0.0):
                    sys.stdout.write(HOME + "".join(
                        colorize(display[j], "scramble" if not locked[j] else "locked", pal, hue, rainbow_active)
                        if display[j] != "\n" else "\n" for j in range(len(display))
                    ))
                    sys.stdout.flush()
                    time.sleep(frame_time)
                    hue += 1
                    continue

            if not locked[i]:
                pick = random.choice(alphabet)
                display[i] = pick
                if pick == chars[i]:
                    locked[i] = True
                    indices.pop(i_ptr)
                else:
                    i_ptr += 1

            # Draw frame with state-based colors
            sys.stdout.write(HOME)
            active_idx = indices[i_ptr % len(indices)] if indices else -1
            out = []
            for j, ch in enumerate(display):
                if chars[j] == "\n":
                    out.append("\n")
                else:
                    if locked[j]:
                        out.append(colorize(ch, "locked", pal, hue, rainbow_active))
                    elif j == active_idx:
                        out.append(colorize(ch, "active", pal, hue, rainbow_active))
                    else:
                        out.append(colorize(ch, "scramble", pal, hue, rainbow_active))
            sys.stdout.write("".join(out))
            sys.stdout.flush()

            time.sleep(frame_time)
            hue += 1

        sys.stdout.write("\n")
    finally:
        sys.stdout.write(SHOW + RESET)
        sys.stdout.flush()

# --- Input helpers ---
def read_multiline() -> str:
    print("\nType/paste your text (multi-line OK).")
    print("When finished, enter a single line with " + BOLD + ".end" + RESET + " and press Enter.\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".end":
            break
        lines.append(line)
    return "\n".join(lines)

def press_enter():
    try:
        input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        pass

def show_help():
    print(CLEAR + HOME + BOLD + "Help: What the menu options do" + RESET + "\n")
    print(BOLD + "1) Edit text" + RESET + " – Paste or type any multi-line text you want to animate. End with '.end'.")
    print(BOLD + "2) Theme" + RESET + " – Choose color palette for the animation (scramble/active/locked/static).")
    print(BOLD + "3) Character pool" + RESET + " – The set of random characters used while scrambling.")
    print("   'letters' (A–Z,a–z), 'letters+digits' (adds 0–9), 'alnum+punct' (adds punctuation), 'printable' (most ASCII).")
    print(BOLD + "4) Speed" + RESET + " – Frames per second. Higher values look smoother and finish faster.")
    print(BOLD + "5) Per-line stagger" + RESET + " – Delay (seconds) between when each new line is allowed to start resolving.")
    print("   For example 0.15 makes line 2 start ~0.15s after line 1, line 3 ~0.30s after line 1, etc.")
    print(BOLD + "6) Rainbow active" + RESET + " – Toggle a rainbow shimmer on the currently active character.")
    print(BOLD + "7) Run" + RESET + " – Start the animation with the current settings.")
    press_enter()

def main():
    # Defaults
    text = "Flip clock vibes\nMultiple lines work too!"
    theme = "matrix"
    pool_key = "alnum+punct"
    speed_key = "normal"
    per_line_stagger = 0.00
    rainbow_active = True

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(BOLD + "=== Windows Color Scrambler ===" + RESET)
        print(DIM + "Random until match → lock → move on. Multi-line supported." + RESET + "\n")
        print(f"{BOLD}1){RESET} Edit text ({len(text)} chars, {text.count('\\n')+1} line(s))")
        print(f"{BOLD}2){RESET} Theme: {theme}  " + DIM + "(scramble/active/locked/static colors)" + RESET)
        print(f"{BOLD}3){RESET} Character pool: {pool_key}")
        print(f"{BOLD}4){RESET} Speed: {speed_key} ({SPEEDS[speed_key]} FPS)")
        print(f"{BOLD}5){RESET} Per-line stagger: {per_line_stagger:.2f} sec")
        print(f"{BOLD}6){RESET} Rainbow active: {'on' if rainbow_active else 'off'}")
        print(f"{BOLD}7){RESET} Run")
        print(f"{BOLD}8){RESET} Help (explain these options)")
        print(f"{BOLD}0){RESET} Exit\n")
        choice = input("Select: ").strip()

        if choice == "1":
            t = read_multiline()
            if t.strip():
                text = t
        elif choice == "2":
            print("\nThemes: " + ", ".join(PALETTES.keys()))
            sel = input(f"Choose theme [{theme}]: ").strip().lower() or theme
            if sel in PALETTES: theme = sel
        elif choice == "3":
            print("\nPools: " + ", ".join(POOLS.keys()))
            sel = input(f"Choose pool [{pool_key}]: ").strip().lower() or pool_key
            if sel in POOLS: pool_key = sel
        elif choice == "4":
            print("\nSpeeds: " + ", ".join(SPEEDS.keys()))
            sel = input(f"Choose speed [{speed_key}]: ").strip().lower() or speed_key
            if sel in SPEEDS: speed_key = sel
        elif choice == "5":
            try:
                per_line_stagger = max(0.0, float(input("Seconds between line starts (e.g., 0.15): ").strip()))
            except ValueError:
                pass
        elif choice == "6":
            rainbow_active = not rainbow_active
        elif choice == "7":
            # Ensure we end with a newline so the last line locks cleanly
            run_text = text if text.endswith("\n") else text + "\n"
            print("\nAnimating... (Ctrl+C to stop)\n")
            try:
                animate_lockstep(
                    target=run_text,
                    palette_name=theme,
                    pool_key=pool_key,
                    fps=SPEEDS[speed_key],
                    per_line_stagger=per_line_stagger,
                    rainbow_active=rainbow_active,
                )
            except KeyboardInterrupt:
                pass
            press_enter()
        elif choice == "8":
            show_help()
        elif choice == "0":
            break
        else:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
