import os
from PIL import Image

def generate_icons():
    # Master logo
    source = "hiring/static/hiring/images/logo.png"

    # Output folder
    output_dir = "hiring/static/hiring/icons"
    os.makedirs(output_dir, exist_ok=True)

    # Make sure the logo exists
    if not os.path.exists(source):
        print(f"❌ Logo not found: {source}")
        return

    # Load the logo
    logo = Image.open(source).convert("RGBA")

    print(f"✅ Using logo: {os.path.abspath(source)}")
    print(f"📏 Original size: {logo.size}")

    # Icon filenames and sizes
    icons = {
        "icon-72.png": 72,
        "icon-72x72.png": 72,
        "icon-96.png": 96,
        "icon-128.png": 128,
        "icon-144.png": 144,
        "icon-152.png": 152,
        "icon-192.png": 192,
        "icon-384.png": 384,
        "icon-512.png": 512,
    }

    # Generate icons
    for filename, size in icons.items():
        resized = logo.resize((size, size), Image.Resampling.LANCZOS)
        output_path = os.path.join(output_dir, filename)
        resized.save(output_path, "PNG")
        print(f"✅ Generated: {output_path}")

    # Also update the images folder
    images_dir = "hiring/static/hiring/images"

    logo.resize((192, 192), Image.Resampling.LANCZOS).save(
        os.path.join(images_dir, "icon-192x192.png"),
        "PNG"
    )

    logo.resize((512, 512), Image.Resampling.LANCZOS).save(
        os.path.join(images_dir, "icon-512x512.png"),
        "PNG"
    )

    print("\n🎉 All icons generated successfully!")

if __name__ == "__main__":
    generate_icons()