import pyproj
from geojson import Feature, FeatureCollection, dumps
from shapely.geometry import Point, LineString, shape

from shapely.ops import transform, unary_union
import os
from tqdm import tqdm


class GeoJSONProcessor:
    def __init__(self, detailed_polygons, simplify_factor, polygon_range, output_directory):
        self.output_directory = output_directory
        self.detailed_polygons = detailed_polygons
        self.simplify_factor = simplify_factor
        self.polygon_range = polygon_range
        self.common_features = []

    def read_coordinates(self, file_path, type):
        args = []
        if type == 'nodes':
            args = self.read_coordinates_nodes(file_path)
        elif type == 'ways':
            args = self.read_coordinates_ways(file_path)
        elif type == 'relations':
            args = self.read_coordinates_relations(file_path)
        return args

    def create_geojson(self, args, type, item):
        if type == 'nodes':
            return self.create_geojson_nodes(args, item)
        elif type == 'ways':
            return self.create_geojson_ways(args, item)
        elif type == 'relations':
            return self.create_geojson_relations(args, item)

    def read_coordinates_nodes(self, file_path):
        coordinates = []
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip():
                    lat, lon = map(float, line.strip().split(','))
                    coordinates.append((lon, lat))
        return coordinates

    def read_coordinates_ways(self, file_path):
        ways = []
        with open(file_path, 'r') as file:
            current_way = []
            for line in file:
                if line.strip():
                    lat, lon = map(float, line.strip().split(','))
                    current_way.append((lon, lat))
                else:
                    if current_way:
                        ways.append(current_way)
                        current_way = []
            if current_way:
                ways.append(current_way)
        return ways

    def read_coordinates_relations(self, file_path):
        return self.read_coordinates_ways(file_path)

    def create_geojson_nodes(self, coordinates, item):
        features = []
        total_nodes = len(coordinates)
        progress_bar = tqdm(total=total_nodes, desc=f"Creating geojson for {item} (nodes)", position=0,
                            leave=True, unit='nodes')  # Create a single progress bar

        for lon, lat in coordinates:
            utm_point = self.lonlat_to_utm(lon, lat)
            circle = utm_point.buffer(self.polygon_range)

            if not self.detailed_polygons:
                simplified_circle = circle.simplify(self.simplify_factor)
                simplified_circle = transform(
                    pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                    simplified_circle)
                feature = Feature(geometry=simplified_circle, properties={'marker-color': '#ff0000'})
            else:
                circle = transform(pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                                   circle)
                feature = Feature(geometry=circle, properties={'marker-color': '#ff0000'})

            features.append(feature)
            self.common_features.append(feature)
            progress_bar.update(1)  # Update the progress bar

        progress_bar.close()  # Close the progress bar
        feature_collection = FeatureCollection(features)
        return feature_collection

    def create_geojson_ways(self, ways, item):
        features = []
        total_ways = len(ways)
        progress_bar = tqdm(total=total_ways, desc=f"Creating geojson for {item} (ways)",
                            position=0, unit='way')  # Create a single progress bar

        for way in ways:
            line = LineString([self.lonlat_to_utm(lon, lat) for lon, lat in way])
            buffer = line.buffer(self.polygon_range)

            if not self.detailed_polygons:
                simplified_buffer = buffer.simplify(self.simplify_factor)
                simplified_buffer = transform(
                    pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                    simplified_buffer)

                feature = Feature(geometry=simplified_buffer, properties={'marker-color': '#00ff00'})
            else:
                buffer = transform(pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                                   buffer)
                feature = Feature(geometry=buffer, properties={'marker-color': '#00ff00'})

            features.append(feature)
            self.common_features.append(feature)
            progress_bar.update(1)  # Update the progress bar

        progress_bar.close()  # Close the progress bar

        feature_collection = FeatureCollection(features)
        return feature_collection

    def create_geojson_relations(self, relations, item):
        features = []
        total_ways = len(relations)
        progress_bar = tqdm(total=total_ways, desc=f"Creating geojson for {item} (relations)",
                            position=0, unit='relations')  # Create a single progress bar

        for way in relations:
            line = LineString([self.lonlat_to_utm(lon, lat) for lon, lat in way])
            buffer = line.buffer(self.polygon_range)

            if not self.detailed_polygons:
                simplified_buffer = buffer.simplify(self.simplify_factor)
                simplified_buffer = transform(
                    pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                    simplified_buffer)

                feature = Feature(geometry=simplified_buffer, properties={'marker-color': '#00ff00'})
            else:
                buffer = transform(pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True).transform,
                                   buffer)
                feature = Feature(geometry=buffer, properties={'marker-color': '#00ff00'})

            features.append(feature)
            self.common_features.append(feature)
            progress_bar.update(1)  # Update the progress bar

        progress_bar.close()  # Close the progress bar

        feature_collection = FeatureCollection(features)
        return feature_collection

    def lonlat_to_utm(self, lon, lat):
        utm_proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32633", always_xy=True).transform
        return transform(utm_proj, Point(lon, lat))

    def merge_overlapping_features(self, feature_collection, item, type):
        geometries = [shape(feature['geometry']) for feature in feature_collection['features']]

        merged = unary_union(geometries)

        total = len(merged.geoms)
        progress_bar = tqdm(total=total, desc=f"Saving overlapping features {item} ({type})",
                            position=0, unit=type)  # Create a single progress bar

        merged_features = []
        for geom in merged.geoms:
            feature = Feature(geometry=geom, properties={'marker-color': '#ff0000'})
            merged_features.append(feature)
            progress_bar.update(1)  # Update the progress bar

        progress_bar.close()  # Close the progress bar

        return FeatureCollection(merged_features)

    def save_geojson(self, geojson, file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            file.write(geojson)

    def process_item(self, item, type, output_directory):
        if self.detailed_polygons:
            input_path = f"{output_directory}/coordinates/coordinates_{item}_{type}.txt"
            output_path = f"{output_directory}/geojson_feature_collection/geojson_feature_collection_{item}_{type}.geojson"
            coordinates = self.read_coordinates(input_path, type)
            feature_collection = self.create_geojson(coordinates, type, item)
            self.save_geojson(dumps(feature_collection), output_path)
            merged_feature_collection = self.merge_overlapping_features(feature_collection, item, type)
            output_path = f"{self.output_directory}/merged_geojson_feature_collection/merged_geojson_feature_collection_{item}.geojson"
            self.save_geojson(dumps(merged_feature_collection), output_path)

        input_path = f"{output_directory}/simplified_coordinates/simplified_coordinates_{item}_{type}.txt"
        output_path = f"{output_directory}/simplified_geojson_feature_collection/simplified_geojson_feature_collection_{item}_{type}.geojson"
        coordinates = self.read_coordinates(input_path, type)
        feature_collection = self.create_geojson(coordinates, type, item)
        self.save_geojson(dumps(feature_collection), output_path)
        merged_feature_collection = self.merge_overlapping_features(feature_collection, item, type)
        output_path = (f"{self.output_directory}/merged_simplified_geojson_feature_collection"
                       f"/merged_simplified_geojson_feature_collection_{item}.geojson")
        self.save_geojson(dumps(merged_feature_collection), output_path)

    def create_geojson_batch(self, items, types):
        for item in items:
            for type in types:
                self.process_item(item, type, self.output_directory)

        # Safe common features
        print('Saving common features, this may take a while...')
        print(f'Number of common features: {len(self.common_features)}')
        feature_collection = FeatureCollection(self.common_features)
        output_path = f"{self.output_directory}/feature_collection.geojson"
        self.save_geojson(dumps(feature_collection), output_path)
        # Safe merged common features
        print('Saving merged common features, this may take a while...')
        merged_feature_collection = self.merge_overlapping_features(feature_collection, '', 'ALL')
        output_path = f"{self.output_directory}/merged_feature_collection.geojson"
        self.save_geojson(dumps(merged_feature_collection), output_path)


if __name__ == "__main__":
    processor = GeoJSONProcessor(detailed_polygons=False, simplify_factor=4.0, polygon_range=100,
                                 output_directory='../output')

    tags = [
        '"amenity"="school"',
    ]

    types = [
        'nodes',
        'ways',
        'relations'
    ]

    processor.create_geojson_batch(tags, types)
