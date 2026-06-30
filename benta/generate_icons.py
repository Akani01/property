# generate_icons.py
from PIL import Image
import os

def generate_icons():
    """Generate all PWA icons from a source image"""
    source_image = 'logo.png'  # Your source image
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    if not os.path.exists(source_image):
        print(f"Source image '{source_image}' not found!")
        return
    
    img = Image.open(source_image)
    img = img.convert('RGBA')
    
    # Create icons directory
    icons_dir = 'hiring/static/hiring/icons'
    os.makedirs(icons_dir, exist_ok=True)
    
    for size in sizes:
        # Resize image
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save
        output_path = os.path.join(icons_dir, f'icon-{size}x{size}.png')
        resized.save(output_path, 'PNG', optimize=True)
        print(f"Generated {output_path}")

if __name__ == '__main__':
    generate_icons()