import os
from PIL import Image, ImageDraw, ImageFont

def generate_icons():
    """Generate PWA icons with Tolleya branding"""
    
    icon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    output_dir = 'hiring/static/hiring/icons'
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a base image with Tolleya branding
    for size in icon_sizes:
        img = Image.new('RGB', (size, size), color='#c62828')
        draw = ImageDraw.Draw(img)
        
        # Draw a white border
        border_width = size // 20
        draw.rectangle(
            [(border_width, border_width), (size - border_width, size - border_width)],
            outline='white',
            width=border_width
        )
        
        # Add "T" text
        try:
            font_size = size // 2
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
        except:
            font = ImageFont.load_default()
        
        # Get text size
        text = 'T'
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Center text
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        # Save
        output_path = os.path.join(output_dir, f'icon-{size}.png')
        img.save(output_path, 'PNG')
        print(f'✅ Generated: {output_path}')

if __name__ == '__main__':
    generate_icons()
    print('🎉 All icons generated!')