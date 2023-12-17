import os

import requests

import os
import requests
from tqdm import tqdm


class OverpassAPI:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"

    def receive_coordinates(self, key):
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
        return requests.post(self.overpass_url, data=overpass_query)

    @staticmethod
    def extract_coordinates(response):
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
        else:
            print("Fehler bei der Abfrage der Daten. Statuscode:", response.status_code)

        return coordinates_node, coordinates_way, coordinates_relation


class CoordinatesProcessor:
    @staticmethod
    def douglas_peucker(points, epsilon):
        if len(points) <= 4:
            return points

        # Find the point with the maximum distance
        dmax = 0
        index = 0
        end = len(points) - 1
        for i in range(1, end):
            d = CoordinatesProcessor.perpendicular_distance(points[i], points[0], points[end])
            if d > dmax:
                index = i
                dmax = d

        # If the maximum distance is greater than epsilon, recursively simplify
        # If the maximum distance is greater than epsilon, recursively simplify
        if dmax > epsilon:
            results1 = CoordinatesProcessor.douglas_peucker(points[:index + 1], epsilon)
            results2 = CoordinatesProcessor.douglas_peucker(points[index:], epsilon)

            # Convert results1 and results2 to lists before concatenating
            results1 = list(results1)
            results2 = list(results2)

            # Concatenate the results, excluding the last point of results1
            return results1[:-1] + results2

        # If the maximum distance is not greater than epsilon, return exactly 4 points
        return [points[0], points[index // 2], points[(index + end) // 2], points[end]]

    @staticmethod
    def perpendicular_distance(point, line_start, line_end):
        x, y = point
        x1, y1 = line_start
        x2, y2 = line_end

        # Calculate the perpendicular distance
        denominator = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
        if denominator == 0:
            return 0  # Avoid division by zero
        return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / denominator

    @staticmethod
    def simplify_way(way, epsilon):
        simplified_way = CoordinatesProcessor.douglas_peucker(way, epsilon)
        return simplified_way

    @staticmethod
    def simplify_coordinates(coordinates, epsilon):
        simplified_coordinates = []

        for item in coordinates:
            if isinstance(item[0], tuple):  # Check if it's a list of coordinates (way)
                simplified_item = CoordinatesProcessor.simplify_way(item, epsilon)
                simplified_coordinates.append(simplified_item)
            elif isinstance(item[0], list):  # Check if it's a list of lists (relation)
                simplified_relation = []
                for way in item:
                    simplified_way = CoordinatesProcessor.simplify_way(way, epsilon)
                    simplified_relation.append(simplified_way)
                simplified_coordinates.append(simplified_relation)

        return simplified_coordinates

    @staticmethod
    def write_coordinates_to_file(file_path, coordinates_list):
        # Check if the directory of the file_path exists, if not, create it
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, 'w') as file:
            for item in coordinates_list:
                if isinstance(item[0], tuple):  # Check if it's a list of coordinates
                    for coord in item:
                        file.write(f"{coord[0]}, {coord[1]}\n")
                    file.write("\n")
                else:
                    file.write(f"{item[0]}, {item[1]}\n")

    def __init__(self, detailed_polygons, epsilon, output_directory):
        self.detailed_polygons = detailed_polygons
        self.epsilon = epsilon
        self.output_directory = output_directory

    def get_coordinates(self, keys, types):
        overpass_api = OverpassAPI()

        progress_bar = tqdm(total=len(keys), position=0, unit='result')  # Create a single progress bar

        for key in keys:
            progress_bar.set_description(f"Receiving coordinates for: {key}")
            index = keys.index(key)
            max_index = len(keys)
            response = overpass_api.receive_coordinates(key)
            coordinates = overpass_api.extract_coordinates(response)

            if self.detailed_polygons:
                for type_ in types:
                    coordinates_type = coordinates[types.index(type_)]
                    file_path = f"{self.output_directory}/coordinates/coordinates_{key}_{type_}.txt"
                    CoordinatesProcessor.write_coordinates_to_file(file_path, coordinates_type)

            for type_coordinates in types:
                file_path = f"{self.output_directory}/simplified_coordinates/simplified_coordinates_{key}_{type_coordinates}.txt"
                if 'nodes' in type_coordinates:
                    CoordinatesProcessor.write_coordinates_to_file(file_path,
                                                                   coordinates[types.index(type_coordinates)])
                else:
                    simplified_coordinates = CoordinatesProcessor.simplify_coordinates(
                        coordinates[types.index(type_coordinates)], self.epsilon)
                    CoordinatesProcessor.write_coordinates_to_file(file_path, simplified_coordinates)

            progress_bar.update(1)  # Update the progress bar

if __name__ == "__main__":
    processor = CoordinatesProcessor(False, 0.0001, "../output")

    keys = [
        '"amenity"="school"',
        '"building"="school"',
        '"amenity"="kindergarten"',
        '"building"="kindergarten"',
        '"leisure"="playground"',
        '"playground:theme"="playground"',
        '"highway"="pedestrian"',
    ]

    types = [
        'nodes',
        'ways',
        'relations'
    ]

    processor.get_coordinates(keys, types)
