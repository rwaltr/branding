#!/usr/bin/env python3
"""
Add logo watermark to an image.
Usage: ./add-logo.py <input_image> [--logo NAME] [--opacity VALUE] [--output FILE]

  Running with no arguments shows this help message.

  --logo:    one of: logo, logooutlined, seal, sealoutlined (default: logo)
  --opacity: 0-100, where 100 is fully opaque (default: 70)
  --output:  output filename (default: <input>-branded.ext)
"""

import sys
import os
import subprocess
import tempfile
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

LOGOS = {
    'logo':          SCRIPT_DIR / 'vector' / 'logo.svg',
    'logooutlined':  SCRIPT_DIR / 'vector' / 'logooutlined.svg',
    'seal':          SCRIPT_DIR / 'vector' / 'seal.svg',
    'sealoutlined':  SCRIPT_DIR / 'vector' / 'sealoutlined.svg',
}

DEFAULT_LOGO = 'logo'


def check_dependencies():
    """Check if required tools are available."""
    has_magick = subprocess.run(['which', 'magick'], capture_output=True).returncode == 0
    has_convert = subprocess.run(['which', 'convert'], capture_output=True).returncode == 0

    if not has_magick and not has_convert:
        print("Missing dependencies: ImageMagick")
        print("\nTo install on Fedora/RHEL:")
        print("  sudo dnf install ImageMagick")
        return False

    return 'magick' if has_magick else 'convert'


def get_image_dimensions(image_path, magick_cmd):
    """Get image dimensions using ImageMagick identify."""
    try:
        if magick_cmd == 'magick':
            cmd = [magick_cmd, 'identify', '-format', '%w %h', image_path]
        else:
            cmd = ['identify', '-format', '%w %h', image_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        width, height = map(int, result.stdout.strip().split())
        return width, height
    except subprocess.CalledProcessError:
        print(f"Error: Could not read image dimensions from {image_path}")
        sys.exit(1)


def add_logo(input_image, output_image, logo_svg, magick_cmd, opacity=70):
    """Add logo to bottom left of image with 10% size and margin."""

    img_width, img_height = get_image_dimensions(input_image, magick_cmd)

    # 10% of image width
    logo_size = int(img_width * 0.10)

    # 2% margin from corner
    margin = int(img_width * 0.02)

    opacity_mult = opacity / 100.0

    print(f"Logo:             {Path(logo_svg).name}")
    print(f"Image dimensions: {img_width}x{img_height}")
    print(f"Logo size:        {logo_size}x{logo_size}")
    print(f"Margin:           {margin}px from bottom-left corner")
    print(f"Opacity:          {opacity}%")
    print(f"Processing...")

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_logo = tmp.name

    try:
        svg_cmd = (
            f"{magick_cmd} -background none -density 300 {logo_svg} "
            f"-resize {logo_size}x{logo_size} "
            f"-alpha set -channel A -evaluate multiply {opacity_mult} +channel "
            f"{tmp_logo}"
        )

        result = subprocess.run(svg_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error converting SVG: {result.stderr}")
            sys.exit(1)

        composite_cmd = (
            f"{magick_cmd} {input_image} {tmp_logo} "
            f"-gravity southwest -geometry +{margin}+{margin} "
            f"-compose over -composite {output_image}"
        )

        result = subprocess.run(composite_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error compositing: {result.stderr}")
            sys.exit(1)

        print(f"✓ Created: {output_image}")
    finally:
        if os.path.exists(tmp_logo):
            os.unlink(tmp_logo)


def main():
    logo_choices_str = ', '.join(LOGOS.keys())

    parser = argparse.ArgumentParser(
        description='Add logo watermark to an image. Run with no arguments to see this help.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
available logos:
  {logo_choices_str}

examples:
  ./add-logo.py photo.png
  ./add-logo.py photo.png --logo seal
  ./add-logo.py photo.png --logo logooutlined --opacity 80
  ./add-logo.py photo.png --output branded.png
  ./add-logo.py photo.png --logo sealoutlined --opacity 90 --output out.png
        ''')

    parser.add_argument('input_image', help='Input image file')
    parser.add_argument('--logo', '-l', default=DEFAULT_LOGO,
                        choices=LOGOS.keys(),
                        metavar='LOGO',
                        help=f'Logo to use (default: {DEFAULT_LOGO}). '
                             f'Available: {logo_choices_str}')
    parser.add_argument('--opacity', type=int, default=70,
                        help='Logo opacity 0-100, where 100 is fully opaque (default: 70)')
    parser.add_argument('--output', '-o', dest='output_image',
                        help='Output filename (default: <input>-branded.ext)')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Validate opacity
    if args.opacity < 0 or args.opacity > 100:
        parser.error("Opacity must be between 0 and 100")

    # Expand and validate input
    input_image = os.path.expanduser(args.input_image)
    if not os.path.exists(input_image):
        print(f"Error: Input file not found: {input_image}")
        sys.exit(1)

    # Resolve logo SVG path
    logo_svg = LOGOS[args.logo]
    if not logo_svg.exists():
        print(f"Error: Logo file not found: {logo_svg}")
        sys.exit(1)

    # Determine output filename
    if args.output_image:
        output_image = args.output_image
    else:
        path = Path(input_image)
        output_image = str(path.parent / f"{path.stem}-branded{path.suffix}")

    # Check dependencies
    magick_cmd = check_dependencies()
    if not magick_cmd:
        sys.exit(1)

    add_logo(input_image, output_image, str(logo_svg), magick_cmd, args.opacity)


if __name__ == '__main__':
    main()
