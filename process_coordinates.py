import json
import os

import pyproj
from geojson import Feature, FeatureCollection, dumps
from shapely.geometry import Point, LineString, shape
from shapely.ops import transform, unary_union
from tqdm import tqdm


class GeoJSONProcessor:
    def __init__(self, simplify_polygons=True, simplify_factor=2.0, polygon_range=100, properties=None):
        self.__properties = properties
        self.__simplify_polygons = simplify_polygons
        self.__simplify_factor = simplify_factor
        self.__polygon_range = polygon_range

    def set_simplify_factor(self, simplify_factor):
        self.__simplify_factor = simplify_factor

    def get_simplify_factor(self):
        return self.__simplify_factor

    def set_polygon_range(self, polygon_range):
        self.__polygon_range = polygon_range

    def get_polygon_range(self):
        return self.__polygon_range

    def set_detailed_polygons(self, detailed_polygons):
        self.__simplify_polygons = detailed_polygons

    def get_detailed_polygons(self):
        return self.__simplify_polygons

    def create_features_batch(self, coordinates_batch):

        features_batch = []

        for coordinates in coordinates_batch:
            features = self.create_features(coordinates)
            for feature in features:
                features_batch.append(feature)

        return features_batch

    @staticmethod
    def read_coordinates(file_path):

        with open(file_path) as f:
            coordinates = json.load(f)

        return coordinates

    @staticmethod
    def save(features, file_path):

        feature_collection = FeatureCollection(features)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            file.write(dumps(feature_collection))

    def create_features(self, coordinates):
        features = []
        number_features = 0
        # Calculate number of features
        for geometry_type in coordinates:
            number_features = number_features + len(geometry_type['coordinates'])

        progress_bar = tqdm(total=number_features, desc=f"Creating geojson",
                            position=0, unit=' forms')  # Create a single progress bar

        def add_feature(geometry):
            if self.__polygon_range > 0:
                if self.__simplify_polygons:
                    geometry = geometry.simplify(self.__simplify_factor)

                geometry = transform(
                    pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                    geometry)

            feature = Feature(geometry=geometry, properties=self.__properties)
            features.append(feature)
            progress_bar.update(1)

        def lonlat_to_utm(longitude, latitude):
            utm_proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32633", always_xy=True).transform
            return transform(utm_proj, Point(longitude, latitude))

        for geometry_type in coordinates:
            if geometry_type["type"] == 'nodes':
                for lon, lat in geometry_type["coordinates"]:
                    if self.__polygon_range > 0:
                        utm_point = lonlat_to_utm(lon, lat)
                        circle_buffer = utm_point.buffer(self.__polygon_range)
                        add_feature(circle_buffer)
                    else:
                        point = Point(lonlat_to_utm(lon, lat))
                        add_feature(point)

            else:
                for way in geometry_type["coordinates"]:
                    if self.__polygon_range > 0:
                        line = LineString([lonlat_to_utm(lon, lat) for lon, lat in way])
                        line_buffer = line.buffer(self.__polygon_range)
                        add_feature(line_buffer)
                    else:
                        line = LineString([lonlat_to_utm(lon, lat) for lon, lat in way])
                        line = transform(
                            pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                            line)
                        add_feature(line)

        progress_bar.close()  # Close the progress bar
        return features

    def merge_features(self, features):
        geometries = [shape(feature['geometry']) for feature in features]

        merged = unary_union(geometries)

        total = len(merged.geoms)
        progress_bar = tqdm(total=total, desc=f"Saving overlapping features",
                            position=0, unit='features')  # Create a single progress bar

        merged_features = []
        for geom in merged.geoms:
            feature = Feature(geometry=geom, properties=self.__properties)
            merged_features.append(feature)
            progress_bar.update(1)  # Update the progress bar

        progress_bar.close()  # Close the progress bar

        return merged_features
