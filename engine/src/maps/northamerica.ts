// by John and Cici
import { GameMap } from './../maps';

export enum Regions {
    Pink = 'pink', // NW: Pacific Northwest / Western Canada
    Brown = 'brown', // West: California / Pacific SW / Mountain West
    Orange = 'orange', // SW / Mexico
    Green = 'green', // South: Texas / Deep South / Florida
    Blue = 'blue', // Midwest / Plains / Mid-South
    Yellow = 'yellow', // Great Lakes / Mid-Atlantic
    Red = 'red', // Northeast / Eastern Canada
}

export enum Cities {
    // Pink — Pacific Northwest / Western Canada
    Edmonton = 'Edmonton',
    Calgary = 'Calgary',
    Vancouver = 'Vancouver',
    Seattle = 'Seattle',
    Regina = 'Regina',
    Winnipeg = 'Winnipeg',
    Minneapolis = 'Minneapolis',

    // Brown — California / Pacific SW / Mountain West
    Portland = 'Portland',
    SanFrancisco = 'San Francisco',
    LosAngeles = 'Los Angeles',
    SanDiego = 'San Diego',
    SaltLakeCity = 'Salt Lake City',
    LasVegas = 'Las Vegas',
    Denver = 'Denver',

    // Orange — SW / Mexico (includes Mexico City N + Mexico City S metropolis pair)
    Albuquerque = 'Albuquerque',
    Juarez = 'Juarez',
    Chihuahua = 'Chihuahua',
    Monterrey = 'Monterrey',
    Guadalajara = 'Guadalajara',
    MexicoCityN = 'Mexico City N',
    MexicoCityS = 'Mexico City S',

    // Green — Texas / Deep South / Florida
    SanAntonio = 'San Antonio',
    DallasFortWorth = 'Dallas-Fort Worth',
    Houston = 'Houston',
    NewOrleans = 'New Orleans',
    Atlanta = 'Atlanta',
    Jacksonville = 'Jacksonville',
    Miami = 'Miami',

    // Blue — Midwest / Plains / Mid-South
    Milwaukee = 'Milwaukee',
    Chicago = 'Chicago',
    KansasCity = 'Kansas City',
    StLouis = 'St. Louis',
    Indianapolis = 'Indianapolis',
    OklahomaCity = 'Oklahoma City',
    Memphis = 'Memphis',

    // Yellow — Great Lakes / Mid-Atlantic
    Toronto = 'Toronto',
    Detroit = 'Detroit',
    Pittsburgh = 'Pittsburgh',
    Columbus = 'Columbus',
    Nashville = 'Nashville',
    Washington = 'Washington',
    Charlotte = 'Charlotte',

    // Red — Northeast / Eastern Canada (includes New York N + New York S metropolis pair)
    Quebec = 'Quebec',
    Ottawa = 'Ottawa',
    Montreal = 'Montreal',
    NewYorkN = 'New York N',
    NewYorkS = 'New York S',
    Boston = 'Boston',
    Philadelphia = 'Philadelphia',
}

export const map: GameMap = {
    name: 'North America',
    // Coords authored against the displayed photo (~2000x1716). First-pass
    // estimates from the printed board — verify against the actual map and tune
    // `adjustRatio` / `mapPosition` once we render in the viewer.
    cities: [
        // Pink — Pacific Northwest / Western Canada
        { name: Cities.Edmonton, region: Regions.Pink, x: 230, y: 30 },
        { name: Cities.Calgary, region: Regions.Pink, x: 250, y: 190 },
        { name: Cities.Vancouver, region: Regions.Pink, x: 120, y: 330 },
        { name: Cities.Seattle, region: Regions.Pink, x: 120, y: 430 },
        { name: Cities.Regina, region: Regions.Pink, x: 420, y: 255 },
        { name: Cities.Winnipeg, region: Regions.Pink, x: 600, y: 255 },
        { name: Cities.Minneapolis, region: Regions.Pink, x: 730, y: 425 },

        // Brown — California / Pacific SW / Mountain West
        { name: Cities.Portland, region: Regions.Brown, x: 205, y: 510 },
        { name: Cities.SanFrancisco, region: Regions.Brown, x: 135, y: 660 },
        { name: Cities.LosAngeles, region: Regions.Brown, x: 210, y: 815 },
        { name: Cities.SanDiego, region: Regions.Brown, x: 300, y: 880 },
        { name: Cities.SaltLakeCity, region: Regions.Brown, x: 380, y: 555 },
        { name: Cities.LasVegas, region: Regions.Brown, x: 300, y: 695 },
        { name: Cities.Denver, region: Regions.Brown, x: 560, y: 615 },

        // Orange — SW / Mexico
        { name: Cities.Albuquerque, region: Regions.Orange, x: 515, y: 820 },
        { name: Cities.Juarez, region: Regions.Orange, x: 475, y: 925 },
        { name: Cities.Chihuahua, region: Regions.Orange, x: 505, y: 1050 },
        { name: Cities.Monterrey, region: Regions.Orange, x: 665, y: 1230 },
        { name: Cities.Guadalajara, region: Regions.Orange, x: 560, y: 1415 },
        { name: Cities.MexicoCityN, region: Regions.Orange, x: 650, y: 1515 },
        { name: Cities.MexicoCityS, region: Regions.Orange, x: 650, y: 1605 },

        // Green — Texas / Deep South / Florida
        { name: Cities.SanAntonio, region: Regions.Green, x: 730, y: 1130 },
        { name: Cities.DallasFortWorth, region: Regions.Green, x: 850, y: 1020 },
        { name: Cities.Houston, region: Regions.Green, x: 885, y: 1140 },
        { name: Cities.NewOrleans, region: Regions.Green, x: 1105, y: 1145 },
        { name: Cities.Atlanta, region: Regions.Green, x: 1310, y: 1065 },
        { name: Cities.Jacksonville, region: Regions.Green, x: 1395, y: 1170 },
        { name: Cities.Miami, region: Regions.Green, x: 1495, y: 1350 },

        // Blue — Midwest / Plains / Mid-South
        { name: Cities.Milwaukee, region: Regions.Blue, x: 975, y: 390 },
        { name: Cities.Chicago, region: Regions.Blue, x: 1030, y: 490 },
        { name: Cities.KansasCity, region: Regions.Blue, x: 825, y: 720 },
        { name: Cities.StLouis, region: Regions.Blue, x: 965, y: 720 },
        { name: Cities.Indianapolis, region: Regions.Blue, x: 1095, y: 680 },
        { name: Cities.OklahomaCity, region: Regions.Blue, x: 800, y: 870 },
        { name: Cities.Memphis, region: Regions.Blue, x: 1050, y: 905 },

        // Yellow — Great Lakes / Mid-Atlantic
        { name: Cities.Toronto, region: Regions.Yellow, x: 1290, y: 495 },
        { name: Cities.Detroit, region: Regions.Yellow, x: 1245, y: 585 },
        { name: Cities.Pittsburgh, region: Regions.Yellow, x: 1395, y: 685 },
        { name: Cities.Columbus, region: Regions.Yellow, x: 1265, y: 730 },
        { name: Cities.Nashville, region: Regions.Yellow, x: 1150, y: 845 },
        { name: Cities.Washington, region: Regions.Yellow, x: 1445, y: 845 },
        { name: Cities.Charlotte, region: Regions.Yellow, x: 1480, y: 965 },

        // Red — Northeast / Eastern Canada
        { name: Cities.Quebec, region: Regions.Red, x: 1810, y: 405 },
        { name: Cities.Ottawa, region: Regions.Red, x: 1620, y: 490 },
        { name: Cities.Montreal, region: Regions.Red, x: 1780, y: 510 },
        { name: Cities.NewYorkN, region: Regions.Red, x: 1635, y: 655 },
        { name: Cities.NewYorkS, region: Regions.Red, x: 1635, y: 720 },
        { name: Cities.Boston, region: Regions.Red, x: 1810, y: 615 },
        { name: Cities.Philadelphia, region: Regions.Red, x: 1620, y: 830 },
    ],
    connections: [
        // Pink — internal
        { nodes: [Cities.Edmonton, Cities.Calgary], cost: 5 },
        { nodes: [Cities.Calgary, Cities.Vancouver], cost: 16 },
        { nodes: [Cities.Vancouver, Cities.Seattle], cost: 4 },
        { nodes: [Cities.Edmonton, Cities.Regina], cost: 15 },
        { nodes: [Cities.Calgary, Cities.Regina], cost: 14 },
        { nodes: [Cities.Vancouver, Cities.Regina], cost: 28 },
        { nodes: [Cities.Regina, Cities.Winnipeg], cost: 11 },
        { nodes: [Cities.Winnipeg, Cities.Minneapolis], cost: 13 },

        // Pink ↔ Brown
        { nodes: [Cities.Seattle, Cities.Portland], cost: 5 },
        { nodes: [Cities.Regina, Cities.SaltLakeCity], cost: 29 },
        { nodes: [Cities.Regina, Cities.Denver], cost: 24 },
        { nodes: [Cities.Winnipeg, Cities.Denver], cost: 26 },
        { nodes: [Cities.Minneapolis, Cities.Denver], cost: 23 },

        // Brown — internal
        { nodes: [Cities.Portland, Cities.SanFrancisco], cost: 20 },
        { nodes: [Cities.SanFrancisco, Cities.LosAngeles], cost: 12 },
        { nodes: [Cities.LosAngeles, Cities.SanDiego], cost: 3 },
        { nodes: [Cities.Portland, Cities.SaltLakeCity], cost: 22 },
        { nodes: [Cities.SanFrancisco, Cities.SaltLakeCity], cost: 22 },
        { nodes: [Cities.SanFrancisco, Cities.LasVegas], cost: 16 },
        { nodes: [Cities.SaltLakeCity, Cities.LasVegas], cost: 14 },
        { nodes: [Cities.LasVegas, Cities.LosAngeles], cost: 8 },
        { nodes: [Cities.SaltLakeCity, Cities.Denver], cost: 14 },
        { nodes: [Cities.LasVegas, Cities.Denver], cost: 25 },

        // Brown ↔ Orange
        { nodes: [Cities.LosAngeles, Cities.Albuquerque], cost: 25 },
        { nodes: [Cities.LasVegas, Cities.Albuquerque], cost: 18 },
        { nodes: [Cities.Denver, Cities.Albuquerque], cost: 12 },
        { nodes: [Cities.SanDiego, Cities.Juarez], cost: 22 },

        // Orange — internal (Mexico City N ↔ S is the metropolis 0-cost edge;
        // N's external edges are pruned — Dijkstra reaches N via S at zero cost,
        // so build costs are unchanged but the rendered map has fewer parallel lines).
        { nodes: [Cities.Albuquerque, Cities.Juarez], cost: 9 },
        { nodes: [Cities.Juarez, Cities.Chihuahua], cost: 8 },
        { nodes: [Cities.Chihuahua, Cities.Monterrey], cost: 14 },
        { nodes: [Cities.Chihuahua, Cities.Guadalajara], cost: 23 },
        { nodes: [Cities.Monterrey, Cities.Guadalajara], cost: 16 },
        { nodes: [Cities.Monterrey, Cities.MexicoCityS], cost: 17 },
        { nodes: [Cities.Guadalajara, Cities.MexicoCityS], cost: 10 },
        { nodes: [Cities.MexicoCityN, Cities.MexicoCityS], cost: 0 },

        // Orange ↔ Blue
        { nodes: [Cities.Albuquerque, Cities.OklahomaCity], cost: 18 },

        // Orange ↔ Green
        { nodes: [Cities.Juarez, Cities.DallasFortWorth], cost: 19 },
        { nodes: [Cities.Juarez, Cities.SanAntonio], cost: 18 },
        { nodes: [Cities.Chihuahua, Cities.SanAntonio], cost: 16 },
        { nodes: [Cities.Monterrey, Cities.SanAntonio], cost: 10 },

        // Blue — internal
        { nodes: [Cities.Milwaukee, Cities.Chicago], cost: 3 },
        { nodes: [Cities.Chicago, Cities.KansasCity], cost: 16 },
        { nodes: [Cities.Chicago, Cities.StLouis], cost: 9 },
        { nodes: [Cities.Chicago, Cities.Indianapolis], cost: 6 },
        { nodes: [Cities.KansasCity, Cities.StLouis], cost: 8 },
        { nodes: [Cities.StLouis, Cities.Indianapolis], cost: 8 },
        { nodes: [Cities.KansasCity, Cities.OklahomaCity], cost: 10 },
        { nodes: [Cities.KansasCity, Cities.Memphis], cost: 14 },
        { nodes: [Cities.StLouis, Cities.Memphis], cost: 9 },
        { nodes: [Cities.OklahomaCity, Cities.Memphis], cost: 15 },

        // Blue ↔ Pink
        { nodes: [Cities.Milwaukee, Cities.Minneapolis], cost: 10 },
        { nodes: [Cities.KansasCity, Cities.Minneapolis], cost: 14 },

        // Blue ↔ Brown
        { nodes: [Cities.KansasCity, Cities.Denver], cost: 19 },
        { nodes: [Cities.OklahomaCity, Cities.Denver], cost: 17 },

        // Blue ↔ Green
        { nodes: [Cities.OklahomaCity, Cities.DallasFortWorth], cost: 7 },
        { nodes: [Cities.Memphis, Cities.DallasFortWorth], cost: 15 },
        { nodes: [Cities.Memphis, Cities.NewOrleans], cost: 14 },
        { nodes: [Cities.Memphis, Cities.Atlanta], cost: 12 },

        // Green — internal
        { nodes: [Cities.DallasFortWorth, Cities.SanAntonio], cost: 9 },
        { nodes: [Cities.DallasFortWorth, Cities.Houston], cost: 8 },
        { nodes: [Cities.DallasFortWorth, Cities.NewOrleans], cost: 16 },
        { nodes: [Cities.SanAntonio, Cities.Houston], cost: 6 },
        { nodes: [Cities.Houston, Cities.NewOrleans], cost: 12 },
        { nodes: [Cities.NewOrleans, Cities.Atlanta], cost: 16 },
        { nodes: [Cities.NewOrleans, Cities.Jacksonville], cost: 20 },
        { nodes: [Cities.Atlanta, Cities.Jacksonville], cost: 10 },
        { nodes: [Cities.Jacksonville, Cities.Miami], cost: 12 },

        // Green ↔ Yellow
        { nodes: [Cities.Atlanta, Cities.Nashville], cost: 9 },
        { nodes: [Cities.Atlanta, Cities.Charlotte], cost: 8 },
        { nodes: [Cities.Jacksonville, Cities.Charlotte], cost: 12 },

        // Yellow — internal
        { nodes: [Cities.Toronto, Cities.Detroit], cost: 8 },
        { nodes: [Cities.Toronto, Cities.Pittsburgh], cost: 11 },
        { nodes: [Cities.Detroit, Cities.Columbus], cost: 7 },
        { nodes: [Cities.Columbus, Cities.Pittsburgh], cost: 6 },
        { nodes: [Cities.Nashville, Cities.Columbus], cost: 15 },
        { nodes: [Cities.Nashville, Cities.Washington], cost: 22 },
        { nodes: [Cities.Nashville, Cities.Charlotte], cost: 12 },
        { nodes: [Cities.Columbus, Cities.Washington], cost: 12 },
        { nodes: [Cities.Washington, Cities.Pittsburgh], cost: 7 },
        { nodes: [Cities.Washington, Cities.Charlotte], cost: 12 },

        // Yellow ↔ Blue
        { nodes: [Cities.Detroit, Cities.Chicago], cost: 10 },
        { nodes: [Cities.Columbus, Cities.Chicago], cost: 10 },
        { nodes: [Cities.Columbus, Cities.Indianapolis], cost: 7 },
        { nodes: [Cities.Nashville, Cities.Indianapolis], cost: 9 },
        { nodes: [Cities.Nashville, Cities.StLouis], cost: 9 },
        { nodes: [Cities.Nashville, Cities.Memphis], cost: 7 },

        // Yellow ↔ Red — NY N parallels are pruned (see Red internal note).
        { nodes: [Cities.Toronto, Cities.Ottawa], cost: 8 },
        { nodes: [Cities.Toronto, Cities.NewYorkS], cost: 14 },
        { nodes: [Cities.Pittsburgh, Cities.NewYorkS], cost: 11 },
        { nodes: [Cities.Pittsburgh, Cities.Philadelphia], cost: 9 },
        { nodes: [Cities.Washington, Cities.Philadelphia], cost: 5 },

        // Red — internal (New York N ↔ S is the metropolis 0-cost edge;
        // N's external edges are pruned — Dijkstra reaches N via S at zero cost,
        // so build costs are unchanged but the rendered map has fewer parallel lines).
        { nodes: [Cities.Quebec, Cities.Montreal], cost: 5 },
        { nodes: [Cities.Montreal, Cities.Boston], cost: 9 },
        { nodes: [Cities.Ottawa, Cities.Montreal], cost: 3 },
        { nodes: [Cities.Ottawa, Cities.NewYorkS], cost: 13 },
        { nodes: [Cities.Montreal, Cities.NewYorkS], cost: 12 },
        { nodes: [Cities.NewYorkS, Cities.Boston], cost: 7 },
        { nodes: [Cities.NewYorkS, Cities.Philadelphia], cost: 3 },
        { nodes: [Cities.NewYorkN, Cities.NewYorkS], cost: 0 },
    ],
    layout: 'Landscape',
    // First-pass fit for landscape map area (~1100x720) from displayed-photo
    // coord space (~2000x1716). Tune after first render.
    adjustRatio: [0.5, 0.38],
    mapPosition: [70, 50],
    // Slight counterclockwise tilt to keep the pink region out of the power-plant
    // header row at the top of the layout.
    mapRotation: -5,

    // Resupply table verified with John from the NA refill summary cards.
    // Indexed [resource][playerCount-2][step-1].
    // Note: 2P and 3P rows are intentionally identical on the printed cards.
    resupply: [
        // Coal
        [
            [2, 5, 2], // 2P
            [2, 5, 2], // 3P
            [3, 6, 3], // 4P
            [4, 7, 4], // 5P
            [5, 8, 5], // 6P
        ],
        // Oil
        [
            [3, 1, 3], // 2P
            [3, 1, 3], // 3P
            [3, 2, 4], // 4P
            [4, 2, 5], // 5P
            [5, 3, 6], // 6P
        ],
        // Garbage
        [
            [2, 2, 4], // 2P
            [2, 2, 4], // 3P
            [3, 3, 5], // 4P
            [3, 3, 6], // 5P
            [4, 4, 7], // 6P
        ],
        // Uranium
        [
            [2, 1, 2], // 2P
            [2, 1, 2], // 3P
            [2, 1, 2], // 4P
            [3, 2, 3], // 5P
            [3, 2, 4], // 6P
        ],
    ],
    // North America uses price spaces 1–9, identical per-price slot layout to Europe
    // (verified with John from the printed board):
    //   Coal    [4,4,4,2,2,2,2,2,2]  total 24 market slots
    //   Oil     [2,2,2,2,2,2,2,2,4]  total 20 market slots
    //   Garbage [3,3,3,3,3,3,3,3,0]  total 24 market slots
    //   Uranium [1,1,1,1,1,1,2,2,2]  total 12 market slots
    //
    // Oil note: same overflow situation as Europe — 20 market slots but
    // startingSupply keeps 24 cubes in the game. Defer to publisher guidance
    // (Mike's pending question to 2F-Spiele); drop oil supply to 20 if confirmed.
    coalPrices: [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9],
    oilPrices: [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 9, 9],
    garbagePrices: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8],
    uraniumPrices: [1, 2, 3, 4, 5, 6, 7, 7, 8, 8, 9, 9],
    // Initial market fill from the rules (coal 2–9, oil 4–9, garbage 3–8, uranium space 9 only):
    //   coal    = 4+4+2+2+2+2+2+2 = 20
    //   oil     = 2+2+2+2+2+4     = 14
    //   garbage = 3+3+3+3+3+3     = 18
    //   uranium = 2               = 2
    startingResources: [20, 14, 18, 2],
    // Total cubes in the game (used cubes return here; refill draws from here).
    startingSupply: [24, 24, 24, 12],
    mapSpecificRules:
        'The metropolises of New York and Mexico City each consist of 2 cities ' +
        '(New York N / New York S and Mexico City N / Mexico City S) connected by ' +
        'a 0-cost edge. The official rules cap a player at 1 house per side of a ' +
        'metropolis; this implementation does not enforce that cap pending publisher ' +
        'clarification, so a player may build in both sides if they wish.',
};
