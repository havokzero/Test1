# 🎨 ASCII Banner Scrambler Ultra

All-in-one terminal app for gorgeous FIGlet/toilet-style ASCII banners with gradients, outlines, shadow, multiple animation modes, ASCII-image rendering, and GIF/MP4 export — all from an intuitive menu with hotkeys.

<p align="center">
  <img alt="demo" src="docs/demo.gif" width="720">
</p>

---

## ✨ Features

- **Beautiful text banners** via `pyfiglet` (hundreds of fonts)
- **Color gradients** (rainbow, ocean, fire, neon, retro phosphor/amber) + **directions** (L→R, R→L, T→B, B→T, diagonals)
- **Effects**: crisp **outline**, soft **shadow** (toilet vibes), **monochrome** fallback
- **Animation modes**:
  - `scramble` (easing + wave reveal)
  - `typewriter`
  - `glitch`
  - `matrix` (rain/rise)
- **ASCII image mode**: render any image/logo to ASCII and animate
- **Export**: save **GIF** or **MP4** (NVENC if available, otherwise libx264)
- **Fast**: frame-diff printing (only changed runs), precomputed styles
- **UX**: menu loop, live preview, hotkeys, profiles/themes, terminal auto-centering & resize-friendly
- **Config**: saved to `~/.banner_scrambler.json`

---

## 📦 Installation

```bash
git clone https://github.com/havokzero/banner-scrambler-ultra.git
cd banner-scrambler-ultra
pip install -r requirements.txt
# or install deps directly:
pip install pyfiglet rich pillow imageio rapidfuzz
```

**Python**: 3.8+

---

## 🚀 Quick Start

```bash
python banner_scrambler_ultra.py
```

- Use the **menu** and **hotkeys** (below) to tweak fonts, colors, modes, etc.
- Press **P** to play the animation, **X** to export a GIF/MP4.

---

## ⌨️ Hotkeys (in Preview)

- **F**: cycle font
- **G**: cycle gradient
- **D**: cycle gradient direction
- **M**: cycle mode (`scramble`/`typewriter`/`glitch`/`matrix`)
- **O**: toggle outline
- **S**: toggle shadow
- **C**: toggle auto-center
- **P**: play animation
- **X**: export (prompt for path, e.g., `out.gif` or `out.mp4`)
- **T**: apply theme (`phosphor`, `neon_grid`, `sunset`, `mono_bold`)
- **Q**: back to menu

---

## 🧭 Menu Map

1. **Text/Image** — switch to ASCII image mode or set message text  
2. **Font/Width/Align** — pick/search font, set wrap width & alignment  
3. **Gradients/Colors** — gradient preset, direction, monochrome  
4. **Mode/Timings** — mode, FPS, duration, wave/typewriter/glitch params  
5. **Effects** — outline & shadow toggles  
6. **Layout/Mono** — auto-center, monochrome, random seed  
7. **Export** — set output path (`.gif`/`.mp4`)  
8. **Run** — play animation  
9. **Save Profile** — persist to `~/.banner_scrambler.json`

---

## 🖼️ Examples

**Classic slanted neon:**
```bash
python banner_scrambler_ultra.py
# Menu → Text: "HELLO WORLD"  | Font: slant | Gradient: neon/d1 | Mode: scramble
# Press P to play, X to export (e.g., out.mp4)
```

**ASCII-image logo, fire gradient, typewriter, export GIF:**
```bash
python banner_scrambler_ultra.py
# 1) Text/Image → Use image mode → pick logo.png → width 120
# 3) Gradient → fire / tb
# 4) Mode → typewriter, FPS 50, Duration 4s, CPS ~180
# 7) Export → out.gif  → Press X to render
```

**Matrix vibe (monochrome + shadow):**
```bash
# In preview: M (until matrix), S (shadow on), G (gradient none) → P
```

---

## ⚙️ Config & Themes

A profile is saved at:

```json
{
  "message": "ZDL",
  "use_image": false,
  "image_path": null,
  "image_width": 120,
  "font": "standard",
  "width": 120,
  "align": "left",
  "mode": "scramble",
  "fps": 60,
  "duration": 3.0,
  "charset_key": "ascii",
  "gradient": "rainbow",
  "gradient_dir": "lr",
  "seed": 1337,
  "wave_ms": 450.0,
  "typewriter_cps": 150,
  "glitch_intensity": 0.3,
  "outline": true,
  "shadow": true,
  "auto_center": true,
  "monochrome": false,
  "export_path": null
}
```

Built-in themes: `phosphor`, `neon_grid`, `sunset`, `mono_bold`.  
Apply via **T** (in preview).

---

## 🛠️ Troubleshooting

- **Colors look dull**: your terminal may not support 24-bit color. App will fall back to monochrome; try a truecolor-capable terminal (`$COLORTERM=truecolor`).
- **No fonts listed**: ensure `pyfiglet` is installed; try `pip install --force-reinstall pyfiglet`.
- **MP4 export fails**: the app tries **NVENC** first, then falls back to `libx264`. Install system codecs or just export `out.gif`.
- **Image looks squished**: tweak *ASCII image width*; terminals use tall cells—renderer compensates but you may want smaller width.

---

## 📁 Project Layout

```
repo/
├─ banner_scrambler_ultra.py   # main app (menu + engine)
├─ requirements.txt            # pyfiglet, rich, pillow, imageio, rapidfuzz
└─ docs/
   ├─ demo.gif                 # optional demo animation
   └─ screenshots/             # optional stills
```

---

## 🤝 Contributing

1. Fork & create a feature branch  
2. Keep PRs focused (effects, mode, export, UI)  
3. Run `ruff/black` if you use them; keep changes readable  
4. Add a short demo GIF if your feature is visual

Ideas welcome: **new gradients, modes, ASCII image filters, export tweaks**.

---

## 📜 License

MIT © 2025
