"""
Demo 3 - Catalog Creator background removal (no API key needed for this step)
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.vision_service.rembg_processor import process_product_image


def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_scripts/demo_03_catalog_image.py <path_to_image.jpg>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = os.path.join(os.path.dirname(__file__), "demo_output_catalog.png")

    with open(input_path, "rb") as f:
        raw_bytes = f.read()

    processed_bytes, error = process_product_image(raw_bytes)

    if error:
        print("Quality check failed:", error)
        sys.exit(1)

    with open(output_path, "wb") as f:
        f.write(processed_bytes)

    print("Input:", input_path)
    print("Output:", output_path)


if __name__ == "__main__":
    main()
