import os

import pyproj
from geojson import Feature, FeatureCollection, dumps
from shapely.geometry import Point, LineString, shape
from shapely.ops import transform, unary_union
from tqdm import tqdm


class Features:
    """
    Stores GeoJSON features.
    """

    def __init__(self, features=None):
        """
        Initializes a new instance of Features.

        :param features: The features to store. Nodes get stored as points, ways and relations as polygons (default
        is None).
        """
        self.__features = features

    def __str__(self):
        return str(self.__features)

    def __repr__(self):
        return self.__features

    def __eq__(self, other):
        return self.__features == other.__features

    def __hash__(self):
        return hash(self.__features)

    def get(self):
        """
        Gets the features.

        :return: The list of features.
        """
        return self.__features

    def set(self, features):
        """
        Sets the features.

        :param features: The coordinates to set.
        """
        self.__features = features

    def save(self, file_path):
        """
        Saves GeoJSON FeatureCollection to a file.

        :param file_path: Path to save the GeoJSON file.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            print(f'Saving geojson to: {file_path}')
            file.write(dumps(FeatureCollection(self.__features)))

    def merge_features(self):
        """
        Merges overlapping GeoJSON features.

        :return: List of merged GeoJSON features.
        """
        geometries = []
        merged_features = []

        for feature in self.__features:
            # Check if the geometry coordinates have at least four points
            if len(feature['geometry']['coordinates'][0]) < 3:
                # Include geometries with less than four coordinates as is
                merged_features.append(Feature(geometry=feature['geometry']))
                continue
            geometry = shape(feature['geometry'])
            geometries.append(geometry)

        buffered_geometries = [geom.buffer(0) for geom in geometries]  # Create minimal buffer (error handling)

        merged = unary_union(buffered_geometries)

        total = len(merged.geoms)
        progress_bar = tqdm(total=total, desc=f"Saving overlapping features",
                            position=0, unit='features')

        for geom in merged.geoms:
            feature = Feature(geometry=geom)
            merged_features.append(feature)
            progress_bar.update(1)

        progress_bar.close()

        return Features(merged_features)

    def buffer(self, buffer_distance_meters=100):
        """
        Applies a buffer of a specified distance to the GeoJSON features.

        :param buffer_distance_meters: Buffer distance in meters (default is 100).
        :return: List of GeoJSON features with buffers applied.
        """
        buffered_features = []

        progress_bar = tqdm(total=len(self.__features), desc=f"Creating Buffer",
                            position=0, unit=' forms')

        unsupported_geometry_types = []

        # Define a projection system (UTM is commonly used for accurate distance measurements)
        utm_projection = pyproj.Transformer.from_crs('epsg:4326', 'epsg:32633', always_xy=True).transform

        def lonlat_to_utm(longitude, latitude):
            return transform(utm_projection, Point(longitude, latitude))

        def add_feature(buffered_geometry):

            buffered_geometry = transform(
                pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                buffered_geometry)

            buffed_feature = Feature(geometry=buffered_geometry)
            buffered_features.append(buffed_feature)

        for feature in self.__features:
            if feature['geometry']['type'] == "Polygon":
                # Convert the geometry to a Shapely object
                geometry = feature["geometry"]
                try:
                    if len(geometry['coordinates'][0]) <= 2:
                        # Handle LineString (two coordinates) by creating a buffer around the line
                        line = LineString(geometry['coordinates'][0])
                        buffered_line = transform(utm_projection, line).buffer(buffer_distance_meters)
                        add_feature(buffered_line)
                    else:
                        shapely_geometry = shape(geometry)
                        # Check if the geometry has enough coordinates
                        if shapely_geometry.is_empty or len(shapely_geometry.exterior.coords) < 4:
                            continue
                        add_feature(transform(utm_projection, shapely_geometry).buffer(buffer_distance_meters))
                except Exception as e:
                    print(e)
                    pass
            elif feature['geometry']['type'] == "Point":
                try:
                    # Apply buffer to Points
                    add_feature(lonlat_to_utm(feature['geometry']['coordinates'][0][0],
                                              feature['geometry']['coordinates'][0][1]).buffer(buffer_distance_meters))
                except Exception as e:
                    print(e)
            else:
                if feature['geometry']['type'] not in unsupported_geometry_types:
                    print(f"Unsupported geometry type: {feature['geometry']['type']}")
                    unsupported_geometry_types.append(feature['geometry']['type'])
            progress_bar.update(1)

        progress_bar.close()

        return Features(buffered_features)
