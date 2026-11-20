# Knowledge Engineering: Autonomous Trailer Knowledge-Based Agent

The self-driving trailer from Practical Exercise 3 (Nairobi to Kisumu), rebuilt as a **knowledge-based agent**.
It keeps a knowledge base of facts and rules about the road network, live weather, traffic law and its own load.
It infers new facts by forward chaining, plans routes with UCS/A\*, and explains every decision.

| File | Purpose |
|---|---|
| `Autonomous_Trailer.ipynb` | The agent, following the 10 knowledge-engineering steps |
| `build_kb.py` | Assembles the static knowledge from public APIs |
| `kb_data.json` | Output of `build_kb.py`, loaded by the notebook |

## Knowledge sources

| Knowledge | Source |
|---|---|
| Towns, roads, class distances | Practical Exercise 3 road graph |
| Town coordinates, county | OpenStreetMap Nominatim |
| Real driving distance and time per road | OSRM demo server |
| Town elevation | Open-Meteo Elevation API |
| Town descriptions | Wikipedia REST API |
| Live weather (fetched when the notebook runs) | Open-Meteo Forecast API |
| Speed limits, maximum vehicle mass | Traffic Act (Cap. 403); EAC Vehicle Load Control Act, 2016 |

All APIs are free, need no key and are used within their usage policies (Nominatim: max 1 request/second).

## Running

```bash
pip install requests pandas matplotlib
python build_kb.py              # optional: refresh kb_data.json (needs internet)
jupyter notebook Autonomous_Trailer.ipynb
```

In Colab the notebook downloads `kb_data.json` from this repository automatically.
Use the chat cell in Step 8 to talk to the agent (type `help`), for example:

```
route Nairobi to Kisumu safest
close Nakuru to Kericho
report fog at Gilgil
why Kericho to Ahero
signal amber
load 61000
```
