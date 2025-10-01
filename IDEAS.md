## Ideas for Features / Capabilities
- Build DB function that collects "https://fantasy.premierleague.com/api/element-summary/***{element_id}***/" endpoint and stores as parameter table. It is then init as a Pd DataFrame when running main.py
- View xPoints via calculation on expected stats
    - If no expected_defcon, decide on some aggregation of total defensive contributions -> points that seems fair
    - Maybe use data to fit this trend... scale factor mapping defensive contributions to defcon points awarded