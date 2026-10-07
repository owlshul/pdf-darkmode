# 🌙 PDF Dark Mode & Night Reading Converter

A lightning-fast, high-fidelity CLI tool and macOS droplet to convert any PDF into a comfortable dark mode / night reading PDF right beside the original file, and automatically open it.

---

- **Zero File Size Bloat**: Digital PDFs remain identical in file size (e.g. 600 KB stays ~600 KB, not 10 MB!).
- **Infinite Vector Sharpness**: Uses a native vector engine so text, fonts, and diagrams remain razor-sharp even when zoomed to 1000%.
- **Instant Speed**: Converts standard documents in under 1 second (over 20–50 pages/sec).
- **100% Searchable & Selectable**: Cmd+F search, text selection, and copying work seamlessly.
- **Saves Right Beside the Original**: `document.pdf` becomes `document_sepia.pdf` or `document_dark.pdf` in the same folder.
- **Auto-Opens**: Automatically opens in your default PDF reader (macOS Preview, Skim, Acrobat, Zen, etc.) as soon as it's ready.
- **In-Place Image Tone-Mapping**: Embedded photos, logos, and figures are tone-mapped in place without re-rasterizing the page.
- **Scanned PDF Support**: Seamlessly falls back to an optimized multi-threaded raster engine for scanned handwritten notes or photocopies.
- **3 Carefully Tuned Reading Themes**:
  - `warm`: **Warm Sepia (Natural Book Paper)** — Subtle ivory paper (`#f7f2e7`) with dark espresso-charcoal ink (`#2b2623`). Glare-free daylight reading without harsh yellowing.
  - `dark` (Default): **Dark Charcoal (Standard Night Mode)** — Deep slate charcoal (`#161618`) with soft off-white text (`#e2e2e5`). Balanced, easy on the eyes.
  - `warm_dark`: **Warm Dark (Gentle Night Warmth)** — Subtle warm charcoal canvas (`#181716`) with cozy warm-cream text (`#ede4d6`). Soothing bedtime reading without turning text yellow.
- **Preserves Bookmarks & Outlines**: Retains Table of Contents, metadata, annotations, and page rotation.

---

## 🚀 3 Ways to Use It

### 1. Terminal Drag & Drop (Fastest)

Simply type `pdf-darkmode ` in your terminal, drag any PDF file from Finder directly into the terminal window, and press <kbd>Return</kbd>:

```bash
pdf-darkmode /path/to/my_document.pdf
```

Shortcut: You can also use `pdf-dark`:
```bash
pdf-dark /path/to/my_document.pdf
```

### 2. Interactive Terminal Prompt

If you just run `pdf-darkmode` with no arguments, it opens an interactive drag-and-drop prompt:

```bash
pdf-darkmode
```

Then simply drag and drop any PDF into the terminal prompt.

### 3. Desktop Droplet App (`PDF Dark Mode.app`)

A native macOS droplet app has been created on your Desktop:
📂 `~/Desktop/PDF Dark Mode.app`

- **Drag & Drop**: Drag ANY PDF file from Finder directly onto the `PDF Dark Mode.app` icon.
- **Click**: Double-click it to open a native file picker.

### 4. Finder Quick Action (Right-Click)

Right-click ANY PDF file in Finder → **Quick Actions** → **Convert to Dark Mode PDF**.

---

## 🛠️ CLI Options

```bash
pdf-darkmode [pdf ...] [options]

Options:
  -t, --theme {dark,sepia,warm,oled,invert}   Color theme (default: dark)
  -m, --mode {auto,vector,raster}             Engine mode (auto: vector for digital PDFs, raster for scans)
  -d, --dpi DPI                               Resolution for raster mode (default: 150)
  -q, --quality QUALITY                       JPEG/Image quality 1-100 (default: 75)
  -w, --workers WORKERS                       Number of parallel CPU worker threads (default: 4)
  -o, --output OUTPUT                         Custom output PDF path
  --no-open                                   Do not automatically open after conversion
```

### Examples:

```bash
# Convert with light sepia (warm parchment paper)
pdf-darkmode my_notes.pdf --theme sepia

# Convert with warm dark espresso & candlelight amber (bedtime reading)
pdf-darkmode my_notes.pdf --theme warm

# Convert with pure OLED black background
pdf-darkmode book.pdf --theme oled

# Ultra-crisp 200 DPI conversion
pdf-darkmode paper.pdf --dpi 200
```
