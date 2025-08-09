#!/usr/bin/env python3
# flip_lock_color.py
import sys, time, random, string

# --- Color helpers (ANSI) ---
RESET = "\x1b[0m"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
HOME = "\x1b[H"
CLEAR = "\x1b[2J"

# Basic palettes (foreground colors)
PALETTES = {
    "matrix": {
        "scramble": "\x1b[32m",   # green
        "active":   "\x1b[93m",   # bright yellow
        "locked":   "\x1b[92m",   # bright green
        "static":   "\x1b[90m",   # dim
    },
    "neon": {
        "scramble": "\x1b[95m",   # magenta
        "active":   "\x1b[96m",   # cyan
        "locked":   "\x1b[97m",   # bright white
        "static":   "\x1b[90m",
    },
    "ice": {
        "scramble": "\x1b[36m",   # cyan
        "active":   "\x1b[94m",   # blue
        "locked":   "\x1b[97m",   # bright white
        "static":   "\x1b[90m",
    },
    "mono": {
        "scramble": "",
        "active":   "",
        "locked":   "",
        "static":   "",
    },
}

# A lightweight rainbow for "active" cycling
RAINBOW = ["\x1b[91m","\x1b[93m","\x1b[92m","\x1b[96m","\x1b[94m","\x1b[95m"]

BASE_POOL = string.ascii_letters + string.digits + string.punctuation + " "

def ask_multiline(prompt: str) -> str:
    print(prompt)
    print("(Ctrl-D to finish on Linux/macOS, or Ctrl-Z then Enter on Windows)\n")
    chunks = []
    try:
        for line in sys.stdin:
            chunks.append(line)
    except KeyboardInterrupt:
        pass
    text = "".join(chunks).rstrip("\n")
    if not text:
        text = "Flip clock vibes\nMultiple lines work too!"
    return text

def ask_choice(prompt: str, choices: list, default: str) -> str:
    choice_str = "/".join(choices)
    ans = input(f"{prompt} [{choice_str}] (default: {default}): ").strip().lower()
    return ans if ans in choices else default

def ask_speed() -> tuple[float, float]:
    # Returns (FPS, frame_skip) where higher FPS = smoother, frame_skip controls how often we advance pointer
    speed = ask_choice("Speed", ["slow","normal","fast","ludicrous"], "normal")
    if speed == "slow":      return (30.0, 0)   # ~30 FPS
    if speed == "fast":      return (75.0, 0)
    if speed == "ludicrous": return (120.0, 0)
    return (60.0, 0)  # normal

def colorize(ch: str, state: str, pal: dict, active_hue: int) -> str:
    if state == "locked":
        return f"{pal['locked']}{ch}{RESET}"
    if state == "active":
        # fun rainbow accent for active if palette isn't mono
        hue = "" if pal is PALETTES["mono"] else RAINBOW[active_hue % len(RAINBOW)]
        return f"{hue or pal['active']}{ch}{RESET}"
    if state == "scramble":
        return f"{pal['scramble']}{ch}{RESET}"
    return f"{pal['static']}{ch}{RESET}"

def animate_lockstep(target: str, palette_name: str = "matrix", fps: float = 60.0):
    pal = PALETTES.get(palette_name, PALETTES["matrix"])

    # Build alphabet: include all unique chars from target so every char is reachable
    alphabet = "".join(sorted(set(BASE_POOL + target.replace("\n",""))))

    chars = list(target)
    locked = [ch == "\n" for ch in chars]  # newlines lock instantly
    display = [("\n" if ch == "\n" else random.choice(alphabet)) for ch in chars]
    indices = [i for i, ch in enumerate(chars) if ch != "\n"]

    if not indices:
        print(target)
        return

    i_ptr = 0
    frame_time = 1.0 / max(1.0, fps)
    active_hue = 0

    sys.stdout.write(CLEAR + HIDE)
    try:
        while not all(locked):
            if not indices:
                break

            # Update one character per frame: pick random; if matches, lock and remove
            i_ptr %= len(indices)
            i = indices[i_ptr]
            if not locked[i]:
                pick = random.choice(alphabet)
                display[i] = pick
                if pick == chars[i]:
                    locked[i] = True
                    indices.pop(i_ptr)
                    # i_ptr now points at next index automatically
                else:
                    i_ptr += 1  # keep scanning forward next frame

            # Redraw entire block with colors
            sys.stdout.write(HOME)
            active_index = indices[i_ptr % len(indices)] if indices else -1
            out = []
            for j, ch in enumerate(display):
                if chars[j] == "\n":
                    out.append("\n")
                else:
                    if locked[j]:
                        out.append(colorize(ch, "locked", pal, active_hue))
                    elif j == active_index:
                        out.append(colorize(ch, "active", pal, active_hue))
                    else:
                        out.append(colorize(ch, "scramble", pal, active_hue))
            sys.stdout.write("".join(out))
            sys.stdout.flush()

            active_hue += 1
            # timing
            time.sleep(frame_time)
        # final line break
        sys.stdout.write("\n")
    finally:
        sys.stdout.write(SHOW + RESET)
        sys.stdout.flush()

if __name__ == "__main__":
    print(CLEAR + HOME)
    print("=== Flip-Lock Scrambler ===")
    text = ask_multiline("Paste your text (multi-line OK):")
    theme = ask_choice("Theme", list(PALETTES.keys()), "matrix")
    fps, _ = ask_speed()
    print("\nAnimating… (Ctrl-C to quit)\n")
    animate_lockstep(text + "\n", palette_name=theme, fps=fps)
