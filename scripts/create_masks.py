import os
import glob
import cv2
import argparse
import numpy as np
from PIL import Image

def create_svg_mask(image_path, output_path, max_edges=16):
    """
    Generates a simplified SVG mask from the non-transparent areas of a PNG image.

    Args:
        image_path (str): Path to the input PNG image.
        output_path (str): Path to save the output SVG file.
        max_edges (int): The maximum number of edges for the simplified polygon.
    """
    try:
        # Open the image and ensure it has an alpha channel
        img = Image.open(image_path).convert("RGBA")
        img_np = np.array(img)
    except FileNotFoundError:
        print(f"Error: Input file not found at {image_path}")
        return

    # Get the alpha channel and create a binary mask
    alpha_channel = img_np[:, :, 3]
    _, binary_mask = cv2.threshold(alpha_channel, 0, 255, cv2.THRESH_BINARY)

    # Find the external contour of the non-transparent area
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print(f"No contours found in {image_path}. Skipping.")
        return

    # Use the largest contour
    largest_contour = max(contours, key=cv2.contourArea)

    # Find the convex hull of the contour, which guarantees all pixels are included.
    hull = cv2.convexHull(largest_contour)

    # Simplify the convex hull until it has at most max_edges
    epsilon = 0.01 * cv2.arcLength(hull, True)
    simplified_contour = cv2.approxPolyDP(hull, epsilon, True)

    # Iteratively increase epsilon to reduce edges if necessary
    while len(simplified_contour) > max_edges:
        epsilon *= 1.1
        simplified_contour = cv2.approxPolyDP(hull, epsilon, True)
        if epsilon > cv2.arcLength(hull, True): # Safety break
            break

    # Get image dimensions for the SVG viewbox
    height, width = img.height, img.width

    # Build the SVG path data string
    if len(simplified_contour) > 0:
        points = " ".join([f"{pt[0][0]},{pt[0][1]}" for pt in simplified_contour])
        svg_content = f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">\n'
        svg_content += f'  <polygon points="{points}" />\n'
        svg_content += '</svg>'

        # Write the SVG file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(svg_content)
        print(f"Generated mask: {output_path}")
    else:
        print(f"Could not generate a simplified path for {image_path}.")

def main():
    """
    Finds all PNG images matching the provided glob patterns and generates SVG masks for them.
    """
    parser = argparse.ArgumentParser(
        description="Generate simplified SVG masks from the non-transparent areas of PNG images."
    )
    parser.add_argument(
        'patterns',
        nargs='+',
        help="One or more glob patterns to find PNG images (e.g., 'content/post/**/*.png')."
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help="Overwrite existing SVG mask files."
    )
    args = parser.parse_args()

    image_paths = []
    for pattern in args.patterns:
        # Use recursive=True to support '**' in patterns
        image_paths.extend(glob.glob(pattern, recursive=True))

    if not image_paths:
        print("No PNG images found matching the provided patterns.")
        return

    for image_path in image_paths:
        # Define the output path for the SVG file
        output_filename = os.path.splitext(os.path.basename(image_path))[0] + '.svg'
        output_path = os.path.join(os.path.dirname(image_path), output_filename)

        if os.path.exists(output_path) and not args.force:
            print(f"Warning: Mask file already exists, skipping. Use --force to overwrite. {output_path}")
            continue

        create_svg_mask(image_path, output_path)

if __name__ == '__main__':
    main()
