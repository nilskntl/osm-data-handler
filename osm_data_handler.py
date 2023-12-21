import json
import os

import pyproj
import requests
from geojson import Feature, FeatureCollection, dumps
from shapely.geometry import Point, LineString, shape
from shapely.ops import transform, unary_union
from tqdm import tqdm


class Coordinates:
    def __init__(self, simplify_form=False, epsilon=0.0001):
        """
        Initializes a new instance of FetchCoordinates.

        :param simplify_form: If True, simplifies the coordinates using Douglas-Peucker algorithm.
        :param epsilon: The epsilon value for the Douglas-Peucker algorithm.
        """
        self.__overpass_url = "https://overpass-api.de/api/interpreter"
        self.__epsilon = epsilon
        self.__simplify_form = simplify_form
        self.__cached_coordinates = {}

    def setEpsilon(self, epsilon):
        """
        Sets the epsilon value for the Douglas-Peucker algorithm.

        :param epsilon: The epsilon value.
        """
        self.__epsilon = epsilon

    def getEpsilon(self):
        """
        Gets the current epsilon value for the Douglas-Peucker algorithm.

        :return: The epsilon value.
        """
        return self.__epsilon

    def setSimplifyForm(self, simplify_form):
        """
        Sets the flag for simplifying coordinates.

        :param simplify_form: If True, coordinates will be simplified using Douglas-Peucker.
        """
        self.__simplify_form = simplify_form

    def getSimplifyForm(self):
        """
        Gets the current status of the coordinate simplification flag.

        :return: True if coordinates are simplified, False otherwise.
        """
        return self.__simplify_form

    def fetch_coordinates(self, key):
        """
        Fetches coordinates for a given key.

        :param key: The key to fetch coordinates for.
        :return: A list of dictionaries containing coordinates for nodes, ways, and relations.
        """
        print(f'Receiving coordinates for: {key}')
        if key in self.__cached_coordinates:
            coordinates = self.__cached_coordinates[key]
        else:
            coordinates = self.__fetch_coordinates(key)
            self.__cached_coordinates[key] = coordinates

        print(f'All coordinates received')
        return coordinates

    @staticmethod
    def read_coordinates(file_path):
        """
        Reads coordinates from a JSON file.

        :param file_path: The path to the JSON file.
        :return: The coordinates read from the file.
        """
        with open(file_path) as f:
            coordinates = json.load(f)

        return coordinates

    def fetch_coordinates_batch(self, keys):
        """
        Fetches coordinates for a batch of keys.

        :param keys: A list of keys to fetch coordinates for.
        :return: A list of dictionaries containing coordinates for nodes, ways, and relations.
        """
        progress_bar = tqdm(total=len(keys), position=0, unit='result')

        coordinates_batch = []

        for key in keys:
            progress_bar.set_description(f"Receiving coordinates for: {key}")
            coordinates_batch.append(self.__fetch_coordinates(key))
            progress_bar.update(1)

        coordinates = []
        for i in range(len(coordinates_batch)):
            for x in range(len(coordinates_batch[i])):
                coordinates.append(coordinates_batch[i][x])

        print(f'All coordinates received')

        return coordinates

    @staticmethod
    def save(coordinates, file_path):
        """
        Saves coordinates to a JSON file.

        :param coordinates: The coordinates to save.
        :param file_path: The path to the JSON file.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            file.write(json.dumps(coordinates))

    def __fetch_coordinates(self, key):
        """
        Fetches coordinates from the Overpass API for a given key.

        :param key: The key to fetch coordinates for.
        :return: A list of dictionaries containing coordinates for nodes, ways, and relations.
        """
        overpass_query = f"""
            [out:json];
            area["ISO3166-1"="DE"][admin_level=2]->.searchArea;
            (
              node[{key}](area.searchArea);
              way[{key}](area.searchArea);
              relation[{key}](area.searchArea);
            );
            out geom;
        """
        response = requests.post(self.__overpass_url, data=overpass_query)
        return self.__extract_coordinates(response)

    def __extract_coordinates(self, response):
        """
        Extracts coordinates from the Overpass API response.

        :param response: The response from the Overpass API.
        :return: A list of dictionaries containing coordinates for nodes, ways, and relations.
        """
        coordinates_node = []
        coordinates_way = []
        coordinates_relation = []

        if response.status_code == 200:
            data = response.json()

            for element in data["elements"]:
                if element['type'] == 'node':
                    lat = element["lat"]
                    lon = element["lon"]
                    coordinates_node.append((lon, lat))

                elif element['type'] == 'way':
                    way_coordinates = [(node["lon"], node["lat"]) for node in element["geometry"]]
                    coordinates_way.append(way_coordinates)

                elif element['type'] == 'relation':
                    relation_coordinates = []
                    for member in element.get('members', []):
                        if member['type'] == 'way':
                            way_coordinates = [(node["lon"], node["lat"]) for node in member.get('geometry', [])]
                            relation_coordinates.extend(way_coordinates)

                    coordinates_relation.append(relation_coordinates)

            if self.__simplify_form:
                coordinates_way = [self.__simplify_coordinates(coordinates=way) for way in coordinates_way]
                coordinates_relation = [self.__simplify_coordinates(coordinates=relation) for relation in
                                        coordinates_relation]

        else:
            print("Error when requesting the data. Status code:", response.status_code)

        return [
            {"type": "nodes", "coordinates": coordinates_node},
            {"type": "ways", "coordinates": coordinates_way},
            {"type": "relations", "coordinates": coordinates_relation}
        ]

    def __douglas_peucker(self, points):
        """
        Applies the Douglas-Peucker algorithm to simplify a list of points.
        https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm
        Generated with GPT 3.5

        :param points: The list of points to simplify.
        :return: The simplified list of points.
        """

        def perpendicular_distance(point, line_start, line_end):
            x, y = point
            x1, y1 = line_start
            x2, y2 = line_end

            # Calculate the perpendicular distance
            denominator = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
            if denominator == 0:
                return 0  # Avoid division by zero
            return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / denominator

        if len(points) <= 4:
            return points

        # Find the point with the maximum distance
        dmax = 0
        index = 0
        end = len(points) - 1
        for i in range(1, end):
            d = perpendicular_distance(points[i], points[0], points[end])
            if d > dmax:
                index = i
                dmax = d

        # If the maximum distance is greater than epsilon, recursively simplify
        if dmax > self.__epsilon:
            results1 = self.__douglas_peucker(points[:index + 1])
            results2 = self.__douglas_peucker(points[index:])

            # Convert results1 and results2 to lists before concatenating
            results1 = list(results1)
            results2 = list(results2)

            # Concatenate the results, excluding the last point of results1
            return results1[:-1] + results2

        # If the maximum distance is not greater than epsilon, return exactly 4 points
        return [points[0], points[index // 2], points[(index + end) // 2], points[end]]

    def __simplify_coordinates(self, coordinates):
        """
        Simplifies a list of coordinates using the Douglas-Peucker algorithm.

        :param coordinates: The list of coordinates to simplify.
        :return: The simplified list of coordinates.
        """
        simplified_coordinates = []

        for item in coordinates:
            if isinstance(item[0], tuple):
                simplified_item = self.__douglas_peucker(item)
                simplified_coordinates.append(simplified_item)

        return simplified_coordinates


class GeoJSON:
    def __init__(self, simplify_polygons=True, simplify_factor=2.0, polygon_range=0, properties=None):
        """
        Initializes the GeoJSONProcessor object.

        :param simplify_polygons: Whether to simplify polygons (default is True).
        :param simplify_factor: The factor by which to simplify polygons (default is 2.0).
        :param polygon_range: The range for creating buffer polygons (default is 0).
        :param properties: Additional properties for GeoJSON features (default is None).
        """
        self.__properties = properties
        self.__simplify_polygons = simplify_polygons
        self.__simplify_factor = simplify_factor
        self.__polygon_range = polygon_range

    def set_simplify_factor(self, simplify_factor):
        """
        Set the simplify factor for polygons.

        :param simplify_factor: The factor by which to simplify polygons.
        """
        self.__simplify_factor = simplify_factor

    def get_simplify_factor(self):
        """
        Get the current simplify factor.

        :return: The current simplify factor.
        """
        return self.__simplify_factor

    def set_polygon_range(self, polygon_range):
        """
        Set the polygon range for buffer creation.

        :param polygon_range: The range for creating buffer polygons.
        """
        self.__polygon_range = polygon_range

    def get_polygon_range(self):
        """
        Get the current polygon range.

        :return: The current polygon range.
        """
        return self.__polygon_range

    def set_detailed_polygons(self, detailed_polygons):
        """
        Set whether to use detailed polygons.

        :param detailed_polygons: Boolean indicating whether to use detailed polygons.
        """
        self.__simplify_polygons = detailed_polygons

    def get_detailed_polygons(self):
        """
        Check if detailed polygons are enabled.

        :return: True if detailed polygons are enabled, False otherwise.
        """
        return self.__simplify_polygons

    def create_features_batch(self, coordinates_batch):
        """
        Creates a batch of GeoJSON features from a batch of coordinates.

        :param coordinates_batch: List of coordinate sets.
        :return: List of GeoJSON features.
        """
        features_batch = []

        for coordinates in coordinates_batch:
            features = self.create_features(coordinates)
            for feature in features:
                features_batch.append(feature)

        return features_batch

    @staticmethod
    def read_coordinates(file_path):
        """
        Reads coordinates from a file.

        :param file_path: Path to the file containing coordinates.
        :return: Parsed coordinates.
        """
        with open(file_path) as f:
            coordinates = json.load(f)

        return coordinates

    @staticmethod
    def read_geojson(file_path):
        """
        Reads GeoJSON FeatureCollection from a file.

        :param file_path: Path to the GeoJSON file.
        :return: List of GeoJSON features.
        """
        with open(file_path) as f:
            geojson_data = json.load(f)

        features = []
        for feature in geojson_data.get('features', []):
            geometry = feature.get('geometry')
            properties = feature.get('properties')
            if geometry:
                feature_obj = Feature(geometry=geometry, properties=properties)
                features.append(feature_obj)

        return features

    @staticmethod
    def save(features, file_path):
        """
        Saves GeoJSON FeatureCollection to a file.

        :param features: List of GeoJSON features.
        :param file_path: Path to save the GeoJSON file.
        """
        feature_collection = FeatureCollection(features)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            file.write(dumps(feature_collection))

    def create_features(self, coordinates):
        """
        Creates GeoJSON features from coordinates.

        :param coordinates: List of coordinate sets.
        :return: List of GeoJSON features.
        """
        features = []
        number_features = 0
        for geometry_type in coordinates:
            number_features = number_features + len(geometry_type['coordinates'])

        progress_bar = tqdm(total=number_features, desc=f"Creating GeoJSON",
                            position=0, unit=' forms')

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

        progress_bar.close()
        return features

    def merge_features(self, features):
        """
        Merges overlapping GeoJSON features.

        :param features: List of GeoJSON features.
        :return: List of merged GeoJSON features.
        """
        geometries = []

        for feature in features:
            geometry = shape(feature['geometry'])
            geometries.append(geometry)

        buffered_geometries = [geom.buffer(0) for geom in geometries]  # Create minimal buffer (error handling)

        merged = unary_union(buffered_geometries)

        total = len(merged.geoms)
        progress_bar = tqdm(total=total, desc=f"Saving overlapping features",
                            position=0, unit='features')

        merged_features = []
        for geom in merged.geoms:
            feature = Feature(geometry=geom, properties=self.__properties)
            merged_features.append(feature)
            progress_bar.update(1)

        progress_bar.close()

        return merged_features
