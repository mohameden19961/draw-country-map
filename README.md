# Draw Country Map

Draw an accurate map of any country with its flag, using Python.

## Usage

```bash
python3 draw_map.py <country_name>
```

Example:
```bash
python3 draw_map.py France
python3 draw_map.py Egypt
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 draw_map.py "South Korea"
```

The map is saved as `{country}_map.png`. Flags are cached in `.flag_cache/`.
