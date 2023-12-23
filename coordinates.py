import json
import os

from shapely import Point
from tqdm import tqdm

from features import Features


class Coordinates:
    """
    Stores coordinates.
    """
    def __init__(self, coordinates=None):
        """
        Initializes a new instance of Coordinates.

        :param coordinates: The coordinates to store (default is None).
        """
        self.__coordinates = coordinates

    def __str__(self):
        return str(self.__coordinates)

    def __repr__(self):
        return self.__coordinates

    def __eq__(self, other):
        return self.__coordinates == other.__coordinates

    def __hash__(self):
        return hash(self.__coordinates)

    def get(self):
        """
        Gets the coordinates.

        :return: The list of coordinates.
        """
        return self.__coordinates

    def set(self, coordinates):
        """
        Sets the coordinates.

        :param coordinates: The coordinates to set.
        """
        self.__coordinates = coordinates

    def save(self, file_path):
        """
        Saves coordinates to a JSON file.

        :param file_path: The path to the JSON file.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            print(f'Saving coordinates to: {file_path}')
            file.write(json.dumps(self.__coordinates))

    @staticmethod
    def read(file_path):
        """
        Reads coordinates from a JSON file.

        :param file_path: The path to the JSON file.
        :return: New instance of Coordinates with read coordinates.
        """
        with open(file_path) as f:
            coordinates = json.load(f)

        return Coordinates(coordinates)

    def simplify(self, epsilon):
        """
        Simplifies the coordinates using the Douglas-Peucker algorithm.

        :param epsilon: The epsilon value for the Douglas-Peucker algorithm (default is 0.0001).
        :return: New instance of Coordinates with simplified coordinates
        """
        simplified_coordinates = []
        for item in self.__coordinates:
            if item["type"] == 'ways' or item["type"] == 'relations':
                simplified = self.__simplify_coordinates(item["coordinates"], epsilon)
                simplified_coordinates.append(
                    {"type": item["type"], "coordinates": simplified}
                )
            else:
                simplified_coordinates.append(item)

        return Coordinates(simplified_coordinates)

    def __simplify_coordinates(self, coordinates, epsilon):
        """
        Simplifies a list of coordinates using the Douglas-Peucker algorithm.

        :param coordinates: The list of coordinates to simplify.
        :return: The simplified list of coordinates.
        """
        simplified_coordinates = []

        for item in coordinates:
            if isinstance(item[0], tuple):
                simplified_item = self.__douglas_peucker(item, epsilon)
                simplified_coordinates.append(simplified_item)

        return simplified_coordinates

    def __douglas_peucker(self, points, epsilon):
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
        if dmax > epsilon:
            results1 = self.__douglas_peucker(points[:index + 1], epsilon)
            results2 = self.__douglas_peucker(points[index:], epsilon)

            # Convert results1 and results2 to lists before concatenating
            results1 = list(results1)
            results2 = list(results2)

            # Concatenate the results, excluding the last point of results1
            return results1[:-1] + results2

        # If the maximum distance is not greater than epsilon, return exactly 4 points
        return [points[0], points[index // 2], points[(index + end) // 2], points[end]]

    def to_features(self):
        """
        Converts coordinates to GeoJSON features with Polygon and Point geometries.

        :return: List of GeoJSON features.
        """
        geojson_features = []
        progress_bar = tqdm(total=len(self.__coordinates), desc=f"Converting to geojson features",
                            position=0, unit=' forms')

        for item in self.__coordinates:
            if item["type"] == 'ways' or item["type"] == 'relations':
                # Separate each way into individual features
                for way_coordinates in item["coordinates"]:
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [way_coordinates]
                        },
                    }
                    geojson_features.append(feature)
            elif item["type"] == 'nodes':
                # Convert to Point geometry
                for coordinates in item["coordinates"]:
                    point = Point(coordinates)
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": list(point.coords)
                        }
                    }
                    geojson_features.append(feature)
            else:
                # Preserve other types as-is
                geojson_features.append(item)
            progress_bar.update(1)

        progress_bar.close()

        return Features(geojson_features)
