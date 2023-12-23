
from fetch import Fetch

if __name__ == "__main__":


    """
    Fetch coordinates 
    """

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
        #'"highway"="pedestrian"',
        #'"area:highway"="pedestrian"',
        '"community_centre"="youth_centre"',
        '"social_facility:for"="youth"',
        '"club"="youth"',
        '"social_facility:for"="child"',
        '"community_centre:for"="child;juvenile"',
        '"healthcare:speciality"="child_psychiatry"',
        '"community_centre:for"="child"',
        '"social_facility:for"="child;juvenile"',
        '"retreat:for"="child"',
        '"community_centre:for"="juvenile;child"',
    ]

    bar = [
        '"highway"="pedestrian"',
        '"area:highway"="pedestrian"'
    ]

    coordinates = Fetch.fetch_coordinates_batch(bar, '["ISO3166-1"="DE"][admin_level=2]')
    coordinates.save("output/testfile/test1.json")
    coordinates.to_geojson_features().buffer(10).buffer(10).save("output/testfile/test2.json")

    #print(coordinates.to_geojson_features())

"""
geojson_processor = GeoJSONProcessor(detailed_polygons=detailed_polygons, simplify_factor=simplify_factor,
                                         polygon_range=polygon_range, output_directory=output_directory)
    geojson_processor.create_geojson_batch(items=foo, geometry_types=bar)
"""
