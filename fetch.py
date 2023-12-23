import requests
from tqdm import tqdm

from coordinates import Coordinates


class Fetch:
    """
    Fetches data from the Overpass API.
    """

    @staticmethod
    def fetch_coordinates(key, area=None):
        """
        Fetches coordinates for a given key.

        :param key: The key to fetch coordinates for.
        :param area: The area in which you are searching (default is Worldwide (None)).
        :return: A list of dictionaries containing coordinates for nodes, ways, and relations.
        """
        print(f'Receiving coordinates for: {key}')

        coordinates = Fetch.__fetch_coordinates(key, area)
        return Coordinates(coordinates)

    @staticmethod
    def fetch_coordinates_batch(keys, area=None):
        """
        Fetches coordinates for a batch of keys.

        :param keys: A list of keys to fetch coordinates for.
        :param area: The area in which you are searching (default is Worldwide (None)).
        :return: A list of dictionaries containing coordinates for nodes, ways, and relations.
        """
        progress_bar = tqdm(total=len(keys), position=0, unit='result')

        coordinates_batch = []

        for key in keys:
            progress_bar.set_description(f"Receiving coordinates for: {key}")
            coordinates_batch.append(Fetch.__fetch_coordinates(key, area))
            progress_bar.update(1)

        coordinates = []
        for i in range(len(coordinates_batch)):
            for x in range(len(coordinates_batch[i])):
                coordinates.append(coordinates_batch[i][x])

        return Coordinates(coordinates)

    @staticmethod
    def __fetch_coordinates(key, area):
        """
        Fetches coordinates from the Overpass API for a given key.

        :param key: The key to fetch coordinates for.
        :return: A list of dictionaries containing coordinates for nodes, ways, and relations.
        """
        if area is None:
            overpass_query = f"""
                [out:json];
                (
                  node[{key}];
                  way[{key}];
                  relation[{key}];
                );
                out geom;
            """
        else:
            overpass_query = f"""
                [out:json];
                area{area}->.searchArea;
                (
                  node[{key}](area.searchArea);
                  way[{key}](area.searchArea);
                  relation[{key}](area.searchArea);
                );
                out geom;
            """
        response = requests.post('https://overpass-api.de/api/interpreter', data=overpass_query)
        return Fetch.__extract_coordinates(response)

    @staticmethod
    def __extract_coordinates(response):
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

        else:
            print("Error when requesting the data. Status code:", response.status_code)

        return [
            {"type": "nodes", "coordinates": coordinates_node},
            {"type": "ways", "coordinates": coordinates_way},
            {"type": "relations", "coordinates": coordinates_relation}
        ]