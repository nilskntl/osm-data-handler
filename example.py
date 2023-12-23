from coordinates import Coordinates
from fetch import Fetch

if __name__ == "__main__":
    """
    Coordinates example.
    """

    # Fetch coordinates for a single key
    coordinates = Fetch.fetch_coordinates(key="building=house")
    # Fetch coordinates for a list of keys
    coordinates_batch = Fetch.fetch_coordinates_batch(
        keys=["building=house", "building=apartments"])
    # Fetch coordinates for a list of keys in a specific area
    coordinates_batch_and_area = Fetch.fetch_coordinates_batch(keys=["building=house", "building=apartments"],
                                                               area='["ISO3166-1"="DE"][admin_level=2]')
    # Simplify coordinates
    simplified_coordinates = coordinates_batch.simplify(epsilon=0.0001)
    # Save coordinates to a file
    coordinates.save("output/example.json")
    # Everything in one line
    Fetch.fetch_coordinates(key="building=house").simplify(epsilon=0.0001).save("output/example.json")

    """
    GeoJSON features example.
    """

    # Create GeoJSON features from coordinates
    features = coordinates.to_features()
    # Read GeoJSON features from a file of coordinates
    features_from_file = Coordinates.read("output/example.json").to_features()
    # Create buffer of 100m around GeoJSON features
    buffered_features = features.buffer(100)
    # Merge overlapping GeoJSON features
    merged_features = features.merge_features()
    # Save GeoJSON features to a file
    features.save("output/example.geojson")
    # Everything in one line
    Coordinates.read("output/example.json").to_features().buffer(100).merge_features().save("output/example.geojson")