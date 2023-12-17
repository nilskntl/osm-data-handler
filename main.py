from create_geojson.create_geojson import GeoJSONProcessor
from get_coordinates.get_coordinates import CoordinatesProcessor

if __name__ == "__main__":
    epsilon = 0.0001
    detailed_polygons = False
    simplify_factor = 4.0
    polygon_range = 100
    output_directory = "output"

    foo = [
        '"amenity"="school"',
        '"building"="school"',
        '"amenity"="kindergarten"',
        '"building"="kindergarten"',
        '"leisure"="playground"',
        '"playground:theme"="playground"',
        '"highway"="pedestrian"',
        '"community_centre"="youth_centre"',
        '"social_facility:for"="youth"',
        '"club"="youth"',
    ]

    bar = [
        'nodes',
        'ways',
        'relations'
    ]

    coordinates_processor = CoordinatesProcessor(detailed_polygons=detailed_polygons, epsilon=epsilon, output_directory=output_directory)
    coordinates_processor.get_coordinates(keys=foo, types=bar)

    geojson_processor = GeoJSONProcessor(detailed_polygons=detailed_polygons, simplify_factor=simplify_factor,
                                         polygon_range=polygon_range, output_directory=output_directory)
    geojson_processor.create_geojson_batch(items=foo, types=bar)
