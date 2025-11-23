import json
import re
import argparse

def clean_geojson_popups(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found, run hugo first")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode '{input_file}'. Make sure it is a valid JSON file.")
        return

    # TODO: check if we should use beautiful soup here to be able to exclude by css selector
    link_div_pattern = re.compile(r'<div class="link">.*?</div>\s*', re.DOTALL)

    for feature in data.get('features', []):
        properties = feature.get('properties', {})
        if 'popupContent' in properties:
            original_popup = properties['popupContent']
            cleaned_popup = link_div_pattern.sub('', original_popup)
            properties['popupContent'] = cleaned_popup

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Successfully cleaned GeoJSON file and saved it to '{output_file}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Clean the link from the popupContent in a GeoJSON file.'
    )
    parser.add_argument('--input', '-i', default='./docs/list/map.geojson',
        help='Path to the input GeoJSON file.'
    )
    parser.add_argument('--output', '-o',
        help='Path for the output cleaned GeoJSON file. Defaults to adding ".cleaned" before the extension.'
    )
    args = parser.parse_args()

    if args.output:
        output_file_path = args.output
    else:
        output_file_path = f"./kleiderbuegel-map.json"

    clean_geojson_popups(args.input, output_file_path)
