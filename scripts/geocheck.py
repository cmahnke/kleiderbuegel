import os
import frontmatter
import argparse
import sys
from geopy.geocoders import Nominatim

precisions = {"exact": 6, "street": 5, "city": 4}

def count_decimal_places(number):
    s = str(number)
    if '.' in s:
        return len(s.split('.')[-1])
    return 0

def nominatim(address):
    try:
        geolocator = Nominatim(user_agent="hugo_geo_checker_script")
        location = geolocator.geocode(address)
        if location:
            return (location.longitude, location.latitude)
    except Exception as e:
        print(f"  - Geocoding error for address '{address}': {e}", file=sys.stderr)
    return None

def gmaps(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

def process_files(content_dir):

    # TODO: MAybe add a check if the order is correct

    print(f"Scanning for content files in: {content_dir}\n")

    for root, _, files in os.walk(content_dir):
        for filename in files:
            # TODO: compare multiple language versions
            if filename.endswith(".md"):
                file_path = os.path.join(root, filename)


                post = frontmatter.load(file_path)
                print(f"--- Checking: {file_path} ---")

                if 'geojson' in post.metadata and 'coordinates' in post['geojson']:
                    coords = post['geojson']['coordinates']
                    if 'precision' in post['geojson']:
                        precision = post['geojson']['precision']
                    else:
                        raise
                    if isinstance(coords, list) and len(coords) == 2:
                        lon, lat = coords[0], coords[1]
                        print(f"  EPSG:4326 (Lon, Lat): ({lon}, {lat})")
                        print(f"  Google Maps Link: {gmaps(lat, lon)}")

                        lon_decimals = count_decimal_places(lon)
                        lat_decimals = count_decimal_places(lat)

                        if lon_decimals > precisions[precision] or lat_decimals > precisions[precision]:
                            print(f"  Warning: High decimal precision detected (Lon: {lon_decimals}, Lat: {lat_decimals}). Proposal:")
                            print("```yaml")
                            print("geojson:")
                            print(f"  coordinates:")
                            try:
                                print(f"  - {round(lon, precisions[precision])}")
                                print(f"  - {round(lat, precisions[precision])}")
                                print(f"  precision: {precision}")
                                print("```")
                            except e:
                                print(f"Faild to round coordinates for {file_path}")
                                raise e
                
                if 'address' in post.metadata and 'geojson' not in post.metadata:
                    print("Address given, but no coordintes!")
                    address = post['address']
                    print(f"  Address found: '{address}'.")
                    print(f"  Attempting to fetch coordinates from Nominatim...")
                    coords = nominatim(address)
                    if coords:
                        lon, lat = coords
                        print(f"  > Coordinates found: (Lon: {lon}, Lat: {lat})")
                        print(f"  > Google Maps Link: {gmaps(lat, lon)}")
                        print(f"  > Proposal to add to front matter:")
                        print("```yaml")
                        print("geojson:")
                        print(f"  coordinates:")
                        print(f"  - {round(lon, 6)}")
                        print(f"  - {round(lat, 6)}")
                        print("```")
                    else:
                        print(f"  > Could not find coordinates for the address.")
                elif 'address' not in post.metadata and 'geojson' in post.metadata:
                    raise Exception(f"Missing adress for {file_path}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="QA for GeoJSON coordinates in posts"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="content",
        help="Hugo content directory (default 'content')."
    )
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found at '{args.directory}'", file=sys.stderr)
        sys.exit(1)

    process_files(args.directory)
