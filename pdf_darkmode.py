#!/usr/local/bin/python3
"""
PDF Dark Mode & Night Reading Converter
High-speed, compact PDF night mode converter with full native vector text preservation.
"""

import sys
import os
import io
import re
import time
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import pymupdf

# --- Color Themes & Configurations ---
THEMES = {
    "warm": {
        "name": "Warm Dark (Espresso & Amber - Night Default)",
        "desc": "Warm dark espresso (#1a1614) with soft candlelight amber text (#ebdcc6). Zero blue light.",
        "bg": (26, 22, 20),
        "text": (235, 220, 198),
        "card": (38, 32, 28),
        "mode": "dark",
        "gamma": 1.0,
    },
    "sepia": {
        "name": "Warm Sepia (Natural Book Paper - Light)",
        "desc": "Warm book paper (#f6eedc) with deep espresso ink (#2c221e) and full text color preservation.",
        "bg": (246, 238, 222),
        "text": (44, 34, 30),
        "card": (238, 228, 210),
        "mode": "light",
        "gamma": 1.0,
    },
}
# Default/fallback alias
THEMES["dark"] = THEMES["warm"]


def normalize_theme(theme_key: str) -> str:
    """Normalizes any user, CLI, or AppleScript input into a valid THEMES key."""
    if not theme_key:
        return "warm"
    t = str(theme_key).lower().strip().replace("-", "_").replace(" ", "_")
    if t in ("sepia", "warm_sepia", "light_sepia", "paper", "parchment", "light"):
        return "sepia"
    elif t in ("warm", "dark", "warm_dark", "night", "candlelight", "bedtime", "default"):
        return "warm"
    return "warm"


def build_theme_lut(theme_key: str):
    """Generates a 3-channel 256-value LUT for Pillow."""
    theme_key = normalize_theme(theme_key)
    cfg = THEMES.get(theme_key, THEMES["warm"])
    bg_r, bg_g, bg_b = cfg["bg"]
    tx_r, tx_g, tx_b = cfg["text"]
    gamma = cfg.get("gamma", 1.0)
    tmode = cfg.get("mode", "dark")

    def channel_lut(bg, text):
        lut = []
        for i in range(256):
            norm = (i / 255.0) ** gamma
            if tmode == "invert":
                val = 255 - i
            else:
                val = int(text - norm * (text - bg))
            lut.append(max(0, min(255, val)))
        return lut

    return channel_lut(bg_r, tx_r) + channel_lut(bg_g, tx_g) + channel_lut(bg_b, tx_b)


def clean_path(p: str) -> str:
    """Cleans up paths pasted or dragged into the terminal (quotes, backslashes)."""
    p = p.strip()
    if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
        p = p[1:-1]
    p = p.replace(r"\ ", " ")
    return os.path.abspath(os.path.expanduser(p))


def print_progress_bar(current: int, total: int, elapsed: float, prefix="Converting"):
    """Terminal progress bar."""
    bar_length = 26
    fraction = current / total if total > 0 else 1.0
    filled = int(fraction * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    percent = int(fraction * 100)
    pages_str = f"({current}/{total} pages)"
    time_str = f"{elapsed:.1f}s"
    sys.stdout.write(f"\r  {prefix}: [{bar}] {percent}% {pages_str} • {time_str}")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")


def format_size(bytes_val: int) -> str:
    """Formats file size into human-readable string."""
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val / (1024 * 1024):.2f} MB"


# --- Native Vector Engine (Zero Bloat, Razor Sharp) ---

def recolor_vector_stream(stream_bytes: bytes, theme_cfg: dict) -> bytes:
    """Recolors PDF vector content streams (RGB, Grayscale, CMYK)."""
    text_s = stream_bytes.decode("latin1", errors="ignore")
    tmode = theme_cfg["mode"]
    bg = tuple(c / 255.0 for c in theme_cfg["bg"])
    tx = tuple(c / 255.0 for c in theme_cfg["text"])
    card = tuple(c / 255.0 for c in theme_cfg.get("card", theme_cfg["bg"]))

    def map_color(r: float, g: float, b: float, is_fill: bool) -> str:
        op = "rg" if is_fill else "RG"
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        is_color = (max(r, g, b) - min(r, g, b)) > 0.08

        if tmode == "light":  # Warm Sepia (Natural Book Paper)
            if lum > 0.82 and not is_color:
                # White/near-white backgrounds -> warm parchment
                return f"{bg[0]:.4f} {bg[1]:.4f} {bg[2]:.4f} {op}"
            elif lum > 0.60 and not is_color:
                # Light neutral cards/borders
                return f"{card[0]:.4f} {card[1]:.4f} {card[2]:.4f} {op}"
            elif not is_color and lum < 0.45:
                # Neutral black/dark gray text -> deep espresso ink
                return f"{tx[0]:.4f} {tx[1]:.4f} {tx[2]:.4f} {op}"
            elif is_color:
                # PRESERVE ALL COLORED TEXT & HEADINGS (red, blue, green, gold, etc.)
                return f"{r:.4f} {g:.4f} {b:.4f} {op}"
            else:
                return f"{r:.4f} {g:.4f} {b:.4f} {op}"
        else:  # Warm Dark (Espresso & Amber - Night Default)
            if lum > 0.82 and not is_color:
                # Originally white backgrounds -> dark canvas
                return f"{bg[0]:.4f} {bg[1]:.4f} {bg[2]:.4f} {op}"
            elif lum > 0.60 and not is_color:
                # Light callout cards/borders -> dark card
                return f"{card[0]:.4f} {card[1]:.4f} {card[2]:.4f} {op}"
            elif not is_color and lum < 0.45:
                # Originally black/dark text -> soft candlelight amber text
                return f"{tx[0]:.4f} {tx[1]:.4f} {tx[2]:.4f} {op}"
            elif is_color:
                # Colored text/lines (red headings, blue links, etc.) -> boost luminance
                scale = max(1.0, 0.70 / max(0.01, lum))
                return f"{min(1.0, r * scale):.4f} {min(1.0, g * scale):.4f} {min(1.0, b * scale):.4f} {op}"
            else:
                scale = max(1.0, 0.70 / max(0.01, lum))
                return f"{min(1.0, r * scale):.4f} {min(1.0, g * scale):.4f} {min(1.0, b * scale):.4f} {op}"

    # RGB
    pattern_rgb = re.compile(
        r"(?:^|(?<=[\s\r\n]))([-+]?(?:\d*\.\d+|\d+))\s+([-+]?(?:\d*\.\d+|\d+))\s+([-+]?(?:\d*\.\d+|\d+))\s+(rg|RG)(?=[\s\r\n]|$)"
    )
    def repl_rgb(m):
        return map_color(float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4) == "rg")
    text_s = pattern_rgb.sub(repl_rgb, text_s)

    # Grayscale
    pattern_gray = re.compile(
        r"(?:^|(?<=[\s\r\n]))([-+]?(?:\d*\.\d+|\d+))\s+([gG])(?=[\s\r\n]|$)"
    )
    def repl_gray(m):
        g = float(m.group(1))
        return map_color(g, g, g, m.group(2) == "g")
    text_s = pattern_gray.sub(repl_gray, text_s)

    # CMYK
    pattern_cmyk = re.compile(
        r"(?:^|(?<=[\s\r\n]))([-+]?(?:\d*\.\d+|\d+))\s+([-+]?(?:\d*\.\d+|\d+))\s+([-+]?(?:\d*\.\d+|\d+))\s+([-+]?(?:\d*\.\d+|\d+))\s+([kK])(?=[\s\r\n]|$)"
    )
    def repl_cmyk(m):
        c, m_val, y, k = float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
        r = (1.0 - c) * (1.0 - k)
        g = (1.0 - m_val) * (1.0 - k)
        b = (1.0 - y) * (1.0 - k)
        return map_color(r, g, b, m.group(5) == "k")
    text_s = pattern_cmyk.sub(repl_cmyk, text_s)

    return text_s.encode("latin1")


def should_use_vector_engine(doc) -> bool:
    """Checks whether the PDF contains native vector text or vector drawings.
    Returns True for digital PDFs, False for pure scanned bitmaps.
    """
    sample_pages = doc[:min(5, len(doc))]
    for page in sample_pages:
        if len(page.get_text().strip()) > 20:
            return True
        if len(page.get_drawings()) > 0:
            return True
    return False


def convert_vector_pdf(doc, theme_key: str, theme_cfg: dict, quality: int = 80) -> bool:
    """Converts a PDF using native vector recoloring and in-place embedded image tone-mapping."""
    bg_pdf = tuple(c / 255.0 for c in theme_cfg["bg"])
    lut = build_theme_lut(theme_key)
    processed_xrefs = set()

    for page in doc:
        # 1. Recolor vector streams (text, lines, shapes)
        for xref in page.get_contents():
            c = doc.xref_stream(xref)
            if c:
                new_c = recolor_vector_stream(c, theme_cfg)
                doc.update_stream(xref, new_c)

        # 2. Add background color rectangle behind everything
        page.draw_rect(page.rect, color=None, fill=bg_pdf, overlay=False)

        # 3. Tone-map embedded images in-place (photos, diagrams, logos)
        for img_info in page.get_images():
            xref = img_info[0]
            if xref not in processed_xrefs:
                processed_xrefs.add(xref)
                try:
                    base_img = doc.extract_image(xref)
                    if base_img and "image" in base_img:
                        pil_im = Image.open(io.BytesIO(base_img["image"])).convert("RGB")
                        dark_im = pil_im.point(lut)
                        buf = io.BytesIO()
                        orig_ext = base_img.get("ext", "png").lower()
                        if orig_ext in ("png", "gif"):
                            dark_im.save(buf, format="PNG", optimize=True)
                        else:
                            dark_im.save(buf, format="JPEG", quality=quality, optimize=True)
                        page.replace_image(xref, stream=buf.getvalue())
                except Exception:
                    pass
    return True


# --- Multi-threaded Raster Engine (Fallback for Scans) ---

def convert_pdf_page(args_tuple):
    """Worker function to render, tone-map, and prepare TextWriter in parallel."""
    src_path, pno, dpi, lut, quality = args_tuple
    doc = pymupdf.open(src_path)
    page = doc[pno]

    # 1. Render to high-res pixmap
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # 2. Apply LUT transformation in C speed
    dark_img = img.point(lut)

    # 3. Compress to JPEG bytes (optimized quality)
    buf = io.BytesIO()
    dark_img.save(buf, format="JPEG", quality=quality, optimize=True)
    img_bytes = buf.getvalue()

    # 4. Batch text extraction via TextWriter
    tw = pymupdf.TextWriter(page.rect)
    try:
        font = pymupdf.Font("helv")
        d = page.get_text("dict")
        for b in d.get("blocks", []):
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    text = s.get("text", "").strip()
                    if text:
                        try:
                            tw.append(s["origin"], s["text"], fontsize=s["size"], font=font)
                        except Exception:
                            pass
    except Exception:
        pass

    return {
        "pno": pno,
        "width": page.rect.width,
        "height": page.rect.height,
        "rotation": page.rotation,
        "img_bytes": img_bytes,
        "tw": tw,
    }


def convert_raster_pdf(doc, input_path: str, output_path: str, theme: str, dpi: int, quality: int, workers: int, quiet: bool, t0: float):
    """Fallback raster conversion for scanned pages."""
    total_pages = len(doc)
    lut = build_theme_lut(theme)
    tasks = [(input_path, pno, dpi, lut, quality) for pno in range(total_pages)]

    page_results = [None] * total_pages
    completed_count = 0

    with ThreadPoolExecutor(max_workers=min(workers, total_pages or 1)) as executor:
        for res in executor.map(convert_pdf_page, tasks):
            page_results[res["pno"]] = res
            completed_count += 1
            if not quiet:
                print_progress_bar(completed_count, total_pages, time.time() - t0)

    out_doc = pymupdf.open()
    for pdata in page_results:
        out_page = out_doc.new_page(width=pdata["width"], height=pdata["height"])
        out_page.insert_image(out_page.rect, stream=pdata["img_bytes"])
        try:
            pdata["tw"].write_text(out_page, render_mode=3)
        except Exception:
            pass
        if pdata["rotation"]:
            out_page.set_rotation(pdata["rotation"])

    try:
        toc = doc.get_toc()
        if toc:
            out_doc.set_toc(toc)
    except Exception:
        pass

    out_doc.save(output_path, deflate=True)


# --- Main Conversion Orchestrator ---

def convert_pdf_file(
    input_path: str,
    output_path: str = None,
    theme: str = "dark",
    mode: str = "auto",
    dpi: int = 150,
    quality: int = 75,
    workers: int = 4,
    auto_open: bool = True,
    quiet: bool = False,
) -> str:
    """Converts a PDF to dark mode right beside the original file."""
    input_path = clean_path(input_path)
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"PDF file not found: {input_path}")

    theme = normalize_theme(theme)
    theme_cfg = THEMES[theme]

    # Output path right beside original if not provided
    if not output_path:
        dirname, filename = os.path.split(input_path)
        base, ext = os.path.splitext(filename)
        output_filename = f"{base}_{theme}{ext}"
        output_path = os.path.join(dirname, output_filename)
    else:
        output_path = clean_path(output_path)

    t0 = time.time()
    doc = pymupdf.open(input_path)
    total_pages = len(doc)
    theme_cfg = THEMES[theme]

    # Decide engine: vector (fast, zero bloat, crisp) vs raster (scanned fallback)
    use_vector = (mode == "vector") or (mode == "auto" and should_use_vector_engine(doc))

    if not quiet:
        engine_label = "Vector Engine (Compact & Razor-Sharp)" if use_vector else f"Raster Engine ({dpi} DPI)"
        print(f"\n🌙 Converting to Dark Mode ({theme_cfg['name']})")
        print(f"  📄 Source:  {input_path}")
        print(f"  💾 Output:  {output_path}")
        print(f"  ⚙️  Config:  {total_pages} pages • {engine_label}")

    if use_vector:
        try:
            convert_vector_pdf(doc, theme, theme_cfg, quality=quality)
            doc.save(output_path, deflate=True)
        except Exception as e:
            if not quiet:
                print(f"  ⚠️ Vector engine encountered issue ({e}); falling back to raster engine...")
            doc.close()
            doc = pymupdf.open(input_path)
            convert_raster_pdf(doc, input_path, output_path, theme, dpi, quality, workers, quiet, t0)
    else:
        convert_raster_pdf(doc, input_path, output_path, theme, dpi, quality, workers, quiet, t0)

    total_time = time.time() - t0
    orig_size_bytes = os.path.getsize(input_path)
    out_size_bytes = os.path.getsize(output_path)

    if not quiet:
        print(f"  ✅ Completed in {total_time:.2f}s ({total_time / total_pages:.2f}s/page)")
        print(f"  📊 Size: {format_size(orig_size_bytes)} -> {format_size(out_size_bytes)}")
        print(f"  📁 Saved: {output_path}")

    # Automatically open on macOS
    if auto_open and sys.platform == "darwin":
        if not quiet:
            print("  🚀 Opening in default viewer...")
        subprocess.run(["open", output_path], check=False)

    return output_path


def interactive_mode():
    """Interactive drag-and-drop loop when run without arguments."""
    print("=" * 60)
    print("🌙 PDF Dark Mode & Reading Themes Converter")
    print("=" * 60)
    print("Available Themes:")
    print("  1. warm  — Warm Dark (Espresso & Amber - Night Default)")
    print("  2. sepia — Warm Sepia (Natural Book Paper - Light, Preserves All Text Colors)")
    print("-" * 60)

    theme_choice = input("Select theme [1-2 or name, default: warm]: ").strip().lower()
    theme_map = {
        "1": "warm",
        "2": "sepia",
    }
    theme = normalize_theme(theme_map.get(theme_choice, theme_choice))

    while True:
        print("\n👉 Drag and drop your PDF file into this window (or 'q' to quit):")
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input or user_input.lower() in ["q", "quit", "exit"]:
            print("Goodbye!")
            break

        path = clean_path(user_input)
        if not os.path.exists(path):
            print(f"❌ File does not exist: {path}")
            continue

        if not path.lower().endswith(".pdf"):
            print(f"❌ File is not a PDF: {path}")
            continue

        try:
            convert_pdf_file(path, theme=theme, auto_open=True)
            print("\n✨ Done! Ready for another PDF.")
        except Exception as e:
            print(f"❌ Error during conversion: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert any PDF into a comfortable dark mode or warm reading PDF right beside the original.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdf-darkmode my_book.pdf                      # Warm Dark (espresso & amber night default)
  pdf-darkmode lecture.pdf --theme sepia        # Warm Sepia (natural book paper light)
  pdf-darkmode                                  # Interactive drag-and-drop mode
        """,
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="pdf-darkmode 1.4.0",
    )
    parser.add_argument("pdf", nargs="*", help="PDF file(s) to convert (or drag and drop into terminal)")
    parser.add_argument(
        "-t", "--theme",
        default="warm",
        help="Color theme: warm (night espresso & amber default), sepia (natural book paper light)",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["auto", "vector", "raster"],
        default="auto",
        help="Engine mode: auto (uses vector when available), vector (compact/sharp), raster (pixmap sandwich)",
    )
    parser.add_argument(
        "-d", "--dpi",
        type=int,
        default=150,
        help="Rendering resolution for raster mode (default: 150)",
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=75,
        help="Image quality 1-100 (default: 75)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of parallel worker threads for raster mode (default: 4)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Custom output PDF path (default: <name>_<theme>.pdf right beside original)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not automatically open the PDF after conversion",
    )

    args = parser.parse_args()

    # If no files provided, launch interactive drag & drop
    if not args.pdf:
        interactive_mode()
        return

    # Process all provided files
    for pdf_path in args.pdf:
        try:
            convert_pdf_file(
                input_path=pdf_path,
                output_path=args.output,
                theme=args.theme,
                mode=args.mode,
                dpi=args.dpi,
                quality=args.quality,
                workers=args.workers,
                auto_open=not args.no_open,
            )
        except Exception as e:
            print(f"❌ Error converting '{pdf_path}': {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
