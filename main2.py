# windows_ascii_scrambler.py
import os, sys, time, random, string, ctypes

# --- Enable ANSI/VT on Windows (for smooth cursor moves, no colors used) ---
if os.name == "nt":
    kernel32 = ctypes.windll.kernel32
    h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
        kernel32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

# --- VT codes (ASCII only) ---
RESET = "\x1b[0m"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
HOME = "\x1b[H"
CLEAR = "\x1b[2J"

# --- Character pools ---
POOLS = {
    "letters": string.ascii_letters + " ",
    "letters+digits": string.ascii_letters + string.digits + " ",
    "alnum+punct": string.ascii_letters + string.digits + string.punctuation + " ",
    "printable": "".join(ch for ch in string.printable if ch not in "\t\r\x0b\x0c"),
}

SPEEDS = {
    "slow": 30.0,
    "normal": 60.0,
    "fast": 90.0,
    "ludicrous": 120.0,
}

def build_alphabet(target: str, pool_key: str) -> str:
    base = POOLS.get(pool_key, POOLS["alnum+punct"])
    extra = target.replace("\n", "")
    return "".join(sorted(set(base + extra)))

def animate_lockstep(target: str, alphabet: str, fps: float = 60.0, per_line_stagger: float = 0.0):
    chars = list(target)
    locked = [ch == "\n" for ch in chars]  # newlines lock instantly
    display = [("\n" if ch == "\n" else random.choice(alphabet)) for ch in chars]
    # Build per-line ranges for stagger
    lines = target.split("\n")
    line_starts = []
    idx = 0
    for line in lines:
        line_starts.append(idx)
        idx += len(line) + 1  # +1 for newline, even last line (we'll add one at run time)

    indices = [i for i, ch in enumerate(chars) if ch != "\n"]
    if not indices:
        print(target)
        return

    # Optional: delay start index of each line for staggered reveal
    next_allowed_time = {start: 0.0 for start in line_starts}
    now0 = time.perf_counter()
    for n, start in enumerate(line_starts):
        next_allowed_time[start] = now0 + n * per_line_stagger

    i_ptr = 0
    frame_time = 1.0 / max(1.0, fps)

    sys.stdout.write(CLEAR + HOME + HIDE)
    try:
        while not all(locked):
            if not indices:
                break

            i_ptr %= len(indices)
            i = indices[i_ptr]

            # If this index is at a new line start and we haven't reached its start time, just draw a frame
            line_start = max([s for s in line_starts if s <= i]) if line_starts else 0
            if time.perf_counter() < next_allowed_time.get(line_start, 0.0):
                sys.stdout.write(HOME + "".join(display))
                sys.stdout.flush()
                time.sleep(frame_time)
                continue

            if not locked[i]:
                pick = random.choice(alphabet)
                display[i] = pick
                if pick == chars[i]:
                    locked[i] = True
                    indices.pop(i_ptr)
                else:
                    i_ptr += 1

            sys.stdout.write(HOME + "".join(display))
            sys.stdout.flush()
            time.sleep(frame_time)
        sys.stdout.write("\n")
    finally:
        sys.stdout.write(SHOW + RESET)
        sys.stdout.flush()

def read_multiline() -> str:
    print("\nEnter text (multi-line). Type a single line with `.end` to finish.\n")
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

def main():
    text = "Flip clock vibes\nMultiple lines work too!"
    pool_key = "alnum+punct"
    fps_key = "normal"
    per_line_stagger = 0.0

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=== Windows ASCII Scrambler ===\n")
        print(f"1) Edit text ({len(text)} chars, {text.count('\\n')+1} line(s))")
        print(f"2) Character pool: {pool_key}")
        print(f"3) Speed: {fps_key} ({SPEEDS[fps_key]} FPS)")
        print(f"4) Per-line stagger: {per_line_stagger:.2f} sec")
        print("5) Run")
        print("0) Exit\n")
        choice = input("Select: ").strip()

        if choice == "1":
            text = read_multiline() or text
        elif choice == "2":
            print("\nPools:", ", ".join(POOLS.keys()))
            sel = input(f"Choose pool [{pool_key}]: ").strip().lower() or pool_key
            if sel in POOLS: pool_key = sel
        elif choice == "3":
            print("\nSpeeds:", ", ".join(SPEEDS.keys()))
            sel = input(f"Choose speed [{fps_key}]: ").strip().lower() or fps_key
            if sel in SPEEDS: fps_key = sel
        elif choice == "4":
            try:
                per_line_stagger = max(0.0, float(input("Seconds between line starts (e.g., 0.15): ").strip()))
            except ValueError:
                pass
        elif choice == "5":
            alphabet = build_alphabet(text + "\n", pool_key)
            print("\nAnimating... (Ctrl+C to stop)\n")
            animate_lockstep(text + "\n", alphabet, fps=SPEEDS[fps_key], per_line_stagger=per_line_stagger)
            input("\nDone. Press Enter to return to menu...")
        elif choice == "0":
            break
        else:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
