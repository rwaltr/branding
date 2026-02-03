#!/usr/bin/env python3
"""
Add logo watermark to an image.
Usage: ./add-logo.py <input_image> [--opacity VALUE] [--output FILE]
  --opacity: 0-100, where 100 is fully opaque (default: 70)
  --output: output filename (default: <input>-branded.ext)
"""

import sys
import os
import subprocess
import tempfile
import argparse
from pathlib import Path

def check_dependencies():
    """Check if required tools are available."""
    # Check for ImageMagick (prefer magick, fall back to convert)
    has_magick = subprocess.run(['which', 'magick'], capture_output=True).returncode == 0
    has_convert = subprocess.run(['which', 'convert'], capture_output=True).returncode == 0
    
    if not has_magick and not has_convert:
        print("Missing dependencies: ImageMagick")
        print("\nTo install on Fedora/RHEL:")
        print("  sudo dnf install ImageMagick")
        return False
    
    # Return preferred command
    return 'magick' if has_magick else 'convert'

def get_image_dimensions(image_path, magick_cmd):
    """Get image dimensions using ImageMagick identify."""
    try:
        cmd = [magick_cmd, 'identify', '-format', '%w %h', image_path] if magick_cmd == 'magick' else ['identify', '-format', '%w %h', image_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        width, height = map(int, result.stdout.strip().split())
        return width, height
    except subprocess.CalledProcessError:
        print(f"Error: Could not read image dimensions from {image_path}")
        sys.exit(1)

def add_logo(input_image, output_image, logo_svg, magick_cmd, opacity=70):
    """Add logo to bottom left of image with 10% size and margin."""
    
    # Get image dimensions
    img_width, img_height = get_image_dimensions(input_image, magick_cmd)
    
    # Calculate logo size (10% of image width)
    logo_size = int(img_width * 0.10)
    
    # Calculate margin (2% of image width for nice spacing)
    margin = int(img_width * 0.02)
    
    # Convert opacity percentage to multiplier (0-100 -> 0.0-1.0)
    opacity_mult = opacity / 100.0
    
    print(f"Image dimensions: {img_width}x{img_height}")
    print(f"Logo size: {logo_size}x{logo_size}")
    print(f"Margin: {margin}px from bottom-left corner")
    print(f"Opacity: {opacity}%")
    print(f"Processing...")
    
    # Create temporary PNG with proper transparency
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_logo = tmp.name
    
    try:
        # Convert SVG to PNG with proper transparency
        # Use -density before SVG and -background none to ensure no white background
        # Apply opacity using -alpha set -channel A -evaluate multiply
        svg_cmd = f"{magick_cmd} -background none -density 300 {logo_svg} " \
                  f"-resize {logo_size}x{logo_size} " \
                  f"-alpha set -channel A -evaluate multiply {opacity_mult} +channel " \
                  f"{tmp_logo}"
        
        result = subprocess.run(svg_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error converting SVG: {result.stderr}")
            sys.exit(1)
        
        # Composite the transparent logo onto the image
        composite_cmd = f"{magick_cmd} {input_image} {tmp_logo} " \
                       f"-gravity southwest -geometry +{margin}+{margin} " \
                       f"-compose over -composite {output_image}"
        
        result = subprocess.run(composite_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error compositing: {result.stderr}")
            sys.exit(1)
        
        print(f"✓ Created: {output_image}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_logo):
            os.unlink(tmp_logo)

def main():
    parser = argparse.ArgumentParser(
        description='Add logo watermark to an image.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  ./add-logo.py ~/Downloads/wallpaper.png
  ./add-logo.py ~/Downloads/wallpaper.png --opacity 80
  ./add-logo.py ~/Downloads/wallpaper.png --output branded.png
  ./add-logo.py ~/Downloads/wallpaper.png --opacity 90 --output logo-90.png
        ''')
    
    parser.add_argument('input_image', help='Input image file')
    parser.add_argument('--opacity', type=int, default=70, 
                        help='Logo opacity 0-100, where 100 is fully opaque (default: 70)')
    parser.add_argument('--output', '-o', dest='output_image',
                        help='Output filename (default: <input>-branded.ext)')
    
    args = parser.parse_args()
    
    # Validate opacity
    if args.opacity < 0 or args.opacity > 100:
        parser.error("Opacity must be between 0 and 100")
    
    # Expand and validate input
    input_image = os.path.expanduser(args.input_image)
    if not os.path.exists(input_image):
        print(f"Error: Input file not found: {input_image}")
        sys.exit(1)
    
    # Determine output filename
    if args.output_image:
        output_image = args.output_image
    else:
        path = Path(input_image)
        output_image = str(path.parent / f"{path.stem}-branded{path.suffix}")
    
    opacity = args.opacity
    
    # Logo path relative to script
    script_dir = Path(__file__).parent
    logo_svg = script_dir / 'vector' / 'logoisolated.svg'
    
    if not logo_svg.exists():
        print(f"Error: Logo file not found: {logo_svg}")
        sys.exit(1)
    
    # Check dependencies
    magick_cmd = check_dependencies()
    if not magick_cmd:
        sys.exit(1)
    
    # Process image
    add_logo(input_image, output_image, str(logo_svg), magick_cmd, opacity)

if __name__ == '__main__':
    main()
