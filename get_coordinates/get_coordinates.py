import os
import requests
from tqdm import tqdm
import json


class FetchCoordinates:
    def __init__(self, simplify_form=False, epsilon=0.0001):
        self.__overpass_url = "https://overpass-api.de/api/interpreter"
        self.__epsilon = epsilon
        self.__simplify_form = simplify_form
        self.__coordinates = []

    def getEpsilon(self):
        return self.__epsilon

    def setEpsilon(self, epsilon):
        self.__epsilon = epsilon

    def getSimplifyForm(self):
        return self.__simplify_form

    def setSimplifyForm(self, simplify_form):
        self.__simplify_form = simplify_form

    def __extract_coordinates(self, response):
        coordinates_node = []
        coordinates_way = []
        coordinates_relation = []

        if response.status_code == 200:
            data = response.json()

            # Für eindeutige Koordinaten
            unique_coordinates_way = set()
            unique_coordinates_relation = set()

            for element in data["elements"]:
                if element['type'] == 'node':
                    lat = element["lat"]
                    lon = element["lon"]
                    coordinates_node.append((lat, lon))

                elif element['type'] == 'way':
                    coordinate_one_way = []
                    for geometry_element in element["geometry"]:
                        lat = geometry_element["lat"]
                        lon = geometry_element["lon"]
                        coordinate_one_way.append((lat, lon))
                    # Füge nur eindeutige Koordinaten für Ways hinzu
                    unique_coordinates_way.add(tuple(coordinate_one_way))

                elif element['type'] == 'relation':
                    members = element.get('members', [])
                    relation_coordinates = []
                    for member in members:
                        if member['type'] == 'way':
                            way_coordinates = []
                            for geometry_element in member.get('geometry', []):
                                lat = geometry_element.get('lat')
                                lon = geometry_element.get('lon')
                                if lat and lon:
                                    way_coordinates.append((lat, lon))
                            if way_coordinates:
                                # Füge nur eindeutige Koordinaten für Relations hinzu
                                unique_coordinates_relation.add(tuple(way_coordinates))
                    relation_coordinates.extend(unique_coordinates_relation)

            coordinates_way = list(unique_coordinates_way)
            coordinates_relation = list(unique_coordinates_relation)
            if self.__simplify_form:
                coordinates_way = self.__simplify_coordinates(coordinates=coordinates_way)
                coordinates_relation = self.__simplify_coordinates(coordinates=coordinates_relation)

        else:
            print("Fehler bei der Abfrage der Daten. Statuscode:", response.status_code)

        return [{"type": "nodes", "coordinates": coordinates_node},
                {"type": "ways", "coordinates": coordinates_way},
                {"type": "relations", "coordinates": coordinates_relation}]

    def fetch_coordinates(self, key):
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

    @staticmethod
    def read_coordinates(file_path):

        with open(file_path) as f:
            coordinates = json.load(f)

        return coordinates

    def get_coordinates_batch(self, keys):
        progress_bar = tqdm(total=len(keys), position=0, unit='result')  # Create a single progress bar

        coordinates_batch = []

        for key in keys:
            progress_bar.set_description(f"Receiving coordinates for: {key}")
            coordinates_batch.append(self.fetch_coordinates(key))
            progress_bar.update(1)  # Update the progress bar

        coordinates = []
        for i in range(len(coordinates_batch)):
            for x in range(len(coordinates_batch[i])):
                coordinates.append(coordinates_batch[i][x])

        return coordinates

    def __douglas_peucker(self, points):

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
        simplified_coordinates = []

        for item in coordinates:
            if isinstance(item[0], tuple):  # Check if it's a list of coordinates (way)
                simplified_item = self.__douglas_peucker(item)
                simplified_coordinates.append(simplified_item)

        return simplified_coordinates

    @staticmethod
    def save_coordinates(file_path, coordinates):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            file.write(json.dumps(coordinates))
