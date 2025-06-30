#!/usr/bin/env python3
"""
QR Code Generation Utility for CMMS Equipment

This script generates QR codes for all equipment in the system.
Each QR code links to the failure reporting page for that specific equipment.

Usage:
    python generate_qr_codes.py [--output-dir OUTPUT_DIR] [--format FORMAT]

Options:
    --output-dir: Directory to save QR codes (default: qr_codes/)
    --format: Output format - png, svg, or pdf (default: png)
"""

import os
import sys
import argparse
import qrcode
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Equipment

def generate_qr_code(equipment, base_url, output_dir, format='png'):
    """Generate QR code for a single equipment item"""
    
    # Create QR code URL
    qr_url = f"{base_url}/qr-report/{equipment.id}"
    
    # Create filename
    safe_name = "".join(c for c in equipment.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_name = safe_name.replace(' ', '_')
    filename = f"QR_{equipment.equipment_id}_{safe_name}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    # Create output path
    output_path = Path(output_dir) / f"{filename}.{format}"
    
    # Save QR code
    if format == 'png':
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(str(output_path))
    elif format == 'svg':
        # For SVG, we'll use a different approach
        try:
            import qrcode.image.svg
            factory = qrcode.image.svg.SvgImage
            img = qr.make_image(image_factory=factory)
            with open(output_path, 'w') as f:
                f.write(img.to_string())
        except ImportError:
            print("SVG support requires qrcode[svg] package. Falling back to PNG.")
            img = qr.make_image(fill_color="black", back_color="white")
            output_path = Path(output_dir) / f"{filename}.png"
            img.save(str(output_path))
    else:
        print(f"Unsupported format: {format}")
        return None
    
    return output_path

def generate_qr_codes_for_all_equipment(base_url, output_dir='qr_codes', format='png'):
    """Generate QR codes for all equipment in the system"""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Get all equipment
    with app.app_context():
        equipment_list = Equipment.query.all()
        
        if not equipment_list:
            print("No equipment found in the database.")
            return
        
        print(f"Generating QR codes for {len(equipment_list)} equipment items...")
        print(f"Output directory: {output_path.absolute()}")
        print(f"Format: {format}")
        print(f"Base URL: {base_url}")
        print("-" * 50)
        
        generated_files = []
        
        for equipment in equipment_list:
            try:
                output_file = generate_qr_code(equipment, base_url, output_path, format)
                if output_file:
                    generated_files.append(output_file)
                    print(f"✓ Generated: {equipment.name} ({equipment.equipment_id}) -> {output_file.name}")
                else:
                    print(f"✗ Failed: {equipment.name} ({equipment.equipment_id})")
            except Exception as e:
                print(f"✗ Error generating QR code for {equipment.name}: {e}")
        
        # Generate summary report
        summary_file = output_path / f"qr_codes_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w') as f:
            f.write("QR Code Generation Summary\n")
            f.write("=" * 30 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Base URL: {base_url}\n")
            f.write(f"Format: {format}\n")
            f.write(f"Total Equipment: {len(equipment_list)}\n")
            f.write(f"Successfully Generated: {len(generated_files)}\n")
            f.write("\nGenerated Files:\n")
            f.write("-" * 20 + "\n")
            for file_path in generated_files:
                f.write(f"{file_path.name}\n")
        
        print("-" * 50)
        print(f"✓ Generated {len(generated_files)} QR codes successfully")
        print(f"✓ Summary saved to: {summary_file}")
        print(f"✓ Files saved to: {output_path.absolute()}")

def main():
    parser = argparse.ArgumentParser(description='Generate QR codes for CMMS equipment')
    parser.add_argument('--output-dir', default='qr_codes', 
                       help='Directory to save QR codes (default: qr_codes/)')
    parser.add_argument('--format', default='png', choices=['png', 'svg'],
                       help='Output format (default: png)')
    parser.add_argument('--base-url', default='http://localhost:5000',
                       help='Base URL for the CMMS system (default: http://localhost:5000)')
    
    args = parser.parse_args()
    
    print("CMMS QR Code Generator")
    print("=" * 30)
    
    try:
        generate_qr_codes_for_all_equipment(
            base_url=args.base_url,
            output_dir=args.output_dir,
            format=args.format
        )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 