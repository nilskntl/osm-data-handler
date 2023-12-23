# OSM Data Handler

This repository contains Python scripts for fetching and processing geographical data from the Overpass API. The primary purpose is to obtain coordinates for specific keys (e.g., amenities, buildings, etc.) within a defined area. The fetched data can then be saved, simplified, and converted to adjustable GeoJSON features.

## Contents
1. [Installation](#installation)
2. [Usage](#usage)
   - [Fetching Coordinates](#fetching-coordinates)
   - [Fetching Coordinates in Batch](#fetching-coordinates-in-batch)
   - [Saving Coordinates](#saving-coordinates)
   - [Simplifying Coordinates](#simplifying-coordinates)
   - [Converting to GeoJSON Features](#converting-to-geojson-features)
3. [File Descriptions](#file-descriptions)
   - [fetch.py](#fetchpy)
   - [coordinates.py](#coordinatespy)
   - [features.py](#featurespy)

## Installation

To use these scripts, you need to have Python installed. Additionally, install the required libraries using:

```bash
pip install requests tqdm shapely pyproj geojson
```

## Usage

### Fetching Coordinates

To fetch coordinates for a specific key (e.g., "amenity"), use the `fetch_coordinates` method:

```python
from fetch import Fetch

# Example: Fetch coordinates for amenity=restaurant worldwide
coordinates = Fetch.fetch_coordinates("amenity=restaurant")
```

### Fetching Coordinates in Batch

To fetch coordinates for a batch of keys, use the `fetch_coordinates_batch` method:

```python
from fetch import Fetch

# Example: Fetch coordinates for multiple amenities worldwide
keys = ["amenity=restaurant", "amenity=bar", "amenity=cafe"]
coordinates_batch = Fetch.fetch_coordinates_batch(keys)
```

### Saving Coordinates

To save coordinates to a JSON file, use the `save` method of the `Coordinates` class:

```python
from coordinates import Coordinates

# Example: Save coordinates to a file
coordinates.save("output/coordinates.json")
```

### Simplifying Coordinates

To simplify coordinates using the Douglas-Peucker algorithm, use the `simplify` method:

```python
from coordinates import Coordinates

# Example: Simplify coordinates with epsilon value 0.0001
simplified_coordinates = coordinates.simplify(0.0001)
```

### Converting to GeoJSON Features

To convert coordinates to GeoJSON features, use the `to_features` method of the `Coordinates` class:

```python
from coordinates import Coordinates

# Example: Convert coordinates to GeoJSON features
geojson_features = coordinates.to_features()
```

## File Descriptions

### fetch.py

This script contains a class `Fetch` that provides methods to fetch coordinates from the Overpass API. It includes functions for fetching coordinates, fetching coordinates in batch, and internal methods for making API requests and extracting coordinates.

### coordinates.py

The `Coordinates` class in this script stores and manipulates geographical coordinates. It includes methods for saving and reading coordinates from a JSON file, simplifying coordinates using the Douglas-Peucker algorithm, and converting coordinates to GeoJSON features.

### features.py

The `Features` class stores GeoJSON features and provides methods for saving, merging overlapping features, and applying a buffer to the features. It includes functions for handling different geometry types (at the time: points and polygons)
