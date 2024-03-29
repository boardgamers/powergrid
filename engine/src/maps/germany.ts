import { GameMap } from './../maps';

export enum Regions {
    Purple = 'purple',
    Green = 'green',
    Red = 'red',
    Yellow = 'yellow',
    Cyan = 'cyan',
    Brown = 'brown',
}

export enum Cities {
    Flensburg = 'Flensburg',
    Kiel = 'Kiel',
    Hamburg = 'Hamburg',
    Hannover = 'Hannover',
    Bremen = 'Bremen',
    Wilhelmshaven = 'Wilhelmshaven',
    Cuxhaven = 'Cuxhaven',
    Lubeck = 'Lubeck',
    Rostock = 'Rostock',
    Schwerin = 'Schwerin',
    Torgelow = 'Torgelow',
    Magdeburg = 'Magdeburg',
    Berlin = 'Berlin',
    FrankfurtO = 'Frankfurt-O',
    Halle = 'Halle',
    Leipzig = 'Leipzig',
    Dresden = 'Dresden',
    Erfurt = 'Erfurt',
    Fulda = 'Fulda',
    Würzburg = 'Würzburg',
    Nurnberg = 'Nurnberg',
    Osnabrück = 'Osnabrück',
    Münster = 'Münster',
    Essen = 'Essen',
    Duisburg = 'Duisburg',
    Dortmund = 'Dortmund',
    Dusseldorf = 'Dusseldorf',
    Kassel = 'Kassel',
    Aachen = 'Aachen',
    Köln = 'Köln',
    Trier = 'Trier',
    Wiesbaden = 'Wiesbaden',
    FrankfurtM = 'Frankfurt-M',
    Saarbrücken = 'Saarbrücken',
    Mannheim = 'Mannheim',
    Freiburg = 'Freiburg',
    Stuttgart = 'Stuttgart',
    Konstanz = 'Konstanz',
    Augsburg = 'Augsburg',
    Regensburg = 'Regensburg',
    München = 'München',
    Passau = 'Passau',
    Stralsund = 'Stralsund',
    Mainz = 'Mainz',
}

export const map: GameMap = {
    name: 'Germany',
    cities: [
        { name: Cities.Flensburg, region: Regions.Green, x: 37, y: 427 },
        { name: Cities.Kiel, region: Regions.Green, x: 106, y: 392 },
        { name: Cities.Hamburg, region: Regions.Green, x: 212, y: 396 },
        { name: Cities.Hannover, region: Regions.Green, x: 378, y: 395 },
        { name: Cities.Bremen, region: Regions.Green, x: 276, y: 463 },
        { name: Cities.Wilhelmshaven, region: Regions.Green, x: 211, y: 521 },
        { name: Cities.Cuxhaven, region: Regions.Green, x: 168, y: 474 },
        { name: Cities.Lubeck, region: Regions.Brown, x: 153, y: 341 },
        { name: Cities.Rostock, region: Regions.Brown, x: 128, y: 256 },
        { name: Cities.Schwerin, region: Regions.Brown, x: 217, y: 297 },
        { name: Cities.Torgelow, region: Regions.Brown, x: 210, y: 126 },
        { name: Cities.Magdeburg, region: Regions.Brown, x: 389, y: 271 },
        { name: Cities.Berlin, region: Regions.Brown, x: 355, y: 170 },
        { name: Cities.FrankfurtO, region: Regions.Brown, x: 381, y: 99 },
        { name: Cities.Halle, region: Regions.Yellow, x: 493, y: 259 },
        { name: Cities.Leipzig, region: Regions.Yellow, x: 526, y: 222 },
        { name: Cities.Dresden, region: Regions.Yellow, x: 572, y: 126 },
        { name: Cities.Erfurt, region: Regions.Yellow, x: 567, y: 309 },
        { name: Cities.Fulda, region: Regions.Yellow, x: 628, y: 398 },
        { name: Cities.Würzburg, region: Regions.Yellow, x: 735, y: 386 },
        { name: Cities.Nurnberg, region: Regions.Yellow, x: 780, y: 309 },
        { name: Cities.Osnabrück, region: Regions.Red, x: 359, y: 516 },
        { name: Cities.Münster, region: Regions.Red, x: 427, y: 554 },
        { name: Cities.Essen, region: Regions.Red, x: 475, y: 603 },
        { name: Cities.Duisburg, region: Regions.Red, x: 456, y: 645 },
        { name: Cities.Dortmund, region: Regions.Red, x: 505, y: 543 },
        { name: Cities.Dusseldorf, region: Regions.Red, x: 537, y: 635 },
        { name: Cities.Kassel, region: Regions.Red, x: 524, y: 430 },
        { name: Cities.Aachen, region: Regions.Cyan, x: 614, y: 654 },
        { name: Cities.Köln, region: Regions.Cyan, x: 590, y: 589 },
        { name: Cities.Trier, region: Regions.Cyan, x: 739, y: 628 },
        { name: Cities.Wiesbaden, region: Regions.Cyan, x: 697, y: 514 },
        { name: Cities.FrankfurtM, region: Regions.Cyan, x: 672, y: 473 },
        { name: Cities.Saarbrücken, region: Regions.Cyan, x: 818, y: 568 },
        { name: Cities.Mannheim, region: Regions.Cyan, x: 796, y: 479 },
        { name: Cities.Freiburg, region: Regions.Purple, x: 966, y: 537 },
        { name: Cities.Stuttgart, region: Regions.Purple, x: 884, y: 458 },
        { name: Cities.Konstanz, region: Regions.Purple, x: 1011, y: 459 },
        { name: Cities.Augsburg, region: Regions.Purple, x: 911, y: 346 },
        { name: Cities.Regensburg, region: Regions.Purple, x: 846, y: 256 },
        { name: Cities.München, region: Regions.Purple, x: 967, y: 278 },
        { name: Cities.Passau, region: Regions.Purple, x: 904, y: 153 },
    ],
    connections: [
        { nodes: [Cities.Flensburg, Cities.Kiel], cost: 4 },
        { nodes: [Cities.Kiel, Cities.Hamburg], cost: 8 },
        { nodes: [Cities.Kiel, Cities.Lubeck], cost: 4 },
        { nodes: [Cities.Hamburg, Cities.Hannover], cost: 17 },
        { nodes: [Cities.Hamburg, Cities.Bremen], cost: 11 },
        { nodes: [Cities.Hamburg, Cities.Cuxhaven], cost: 11 },
        { nodes: [Cities.Hamburg, Cities.Lubeck], cost: 6 },
        { nodes: [Cities.Hamburg, Cities.Schwerin], cost: 8 },
        { nodes: [Cities.Bremen, Cities.Wilhelmshaven], cost: 11 },
        { nodes: [Cities.Bremen, Cities.Hannover], cost: 10 },
        { nodes: [Cities.Bremen, Cities.Cuxhaven], cost: 8 },
        { nodes: [Cities.Bremen, Cities.Osnabrück], cost: 11 },
        { nodes: [Cities.Hannover, Cities.Schwerin], cost: 19 },
        { nodes: [Cities.Hannover, Cities.Magdeburg], cost: 15 },
        { nodes: [Cities.Hannover, Cities.Erfurt], cost: 19 },
        { nodes: [Cities.Hannover, Cities.Osnabrück], cost: 16 },
        { nodes: [Cities.Hannover, Cities.Kassel], cost: 15 },
        { nodes: [Cities.Wilhelmshaven, Cities.Osnabrück], cost: 14 },
        { nodes: [Cities.Lubeck, Cities.Schwerin], cost: 6 },
        { nodes: [Cities.Schwerin, Cities.Rostock], cost: 6 },
        { nodes: [Cities.Schwerin, Cities.Torgelow], cost: 19 },
        { nodes: [Cities.Schwerin, Cities.Berlin], cost: 18 },
        { nodes: [Cities.Schwerin, Cities.Magdeburg], cost: 16 },
        { nodes: [Cities.Torgelow, Cities.Rostock], cost: 19 },
        { nodes: [Cities.Torgelow, Cities.Berlin], cost: 15 },
        { nodes: [Cities.Berlin, Cities.Magdeburg], cost: 10 },
        { nodes: [Cities.Berlin, Cities.FrankfurtO], cost: 6 },
        { nodes: [Cities.Berlin, Cities.Halle], cost: 17 },
        { nodes: [Cities.Magdeburg, Cities.Halle], cost: 11 },
        { nodes: [Cities.FrankfurtO, Cities.Leipzig], cost: 21 },
        { nodes: [Cities.FrankfurtO, Cities.Dresden], cost: 16 },
        { nodes: [Cities.Halle, Cities.Leipzig], cost: 0 },
        { nodes: [Cities.Leipzig, Cities.Dresden], cost: 13 },
        { nodes: [Cities.Erfurt, Cities.Halle], cost: 6 },
        { nodes: [Cities.Erfurt, Cities.Dresden], cost: 19 },
        { nodes: [Cities.Erfurt, Cities.Nurnberg], cost: 21 },
        { nodes: [Cities.Erfurt, Cities.Fulda], cost: 13 },
        { nodes: [Cities.Erfurt, Cities.Kassel], cost: 15 },
        { nodes: [Cities.Fulda, Cities.Würzburg], cost: 11 },
        { nodes: [Cities.Fulda, Cities.Kassel], cost: 8 },
        { nodes: [Cities.Fulda, Cities.FrankfurtM], cost: 8 },
        { nodes: [Cities.Würzburg, Cities.Nurnberg], cost: 8 },
        { nodes: [Cities.Würzburg, Cities.FrankfurtM], cost: 13 },
        { nodes: [Cities.Würzburg, Cities.Mannheim], cost: 10 },
        { nodes: [Cities.Würzburg, Cities.Stuttgart], cost: 12 },
        { nodes: [Cities.Würzburg, Cities.Augsburg], cost: 19 },
        { nodes: [Cities.Nurnberg, Cities.Augsburg], cost: 18 },
        { nodes: [Cities.Nurnberg, Cities.Regensburg], cost: 12 },
        { nodes: [Cities.Osnabrück, Cities.Münster], cost: 7 },
        { nodes: [Cities.Osnabrück, Cities.Kassel], cost: 20 },
        { nodes: [Cities.Münster, Cities.Essen], cost: 6 },
        { nodes: [Cities.Münster, Cities.Dortmund], cost: 2 },
        { nodes: [Cities.Essen, Cities.Duisburg], cost: 0 },
        { nodes: [Cities.Essen, Cities.Dusseldorf], cost: 2 },
        { nodes: [Cities.Essen, Cities.Dortmund], cost: 4 },
        { nodes: [Cities.Dortmund, Cities.Kassel], cost: 18 },
        { nodes: [Cities.Dortmund, Cities.Köln], cost: 10 },
        { nodes: [Cities.Dortmund, Cities.FrankfurtM], cost: 20 },
        { nodes: [Cities.Kassel, Cities.FrankfurtM], cost: 13 },
        { nodes: [Cities.Dusseldorf, Cities.Aachen], cost: 9 },
        { nodes: [Cities.Dusseldorf, Cities.Köln], cost: 4 },
        { nodes: [Cities.Aachen, Cities.Köln], cost: 7 },
        { nodes: [Cities.Aachen, Cities.Trier], cost: 19 },
        { nodes: [Cities.Trier, Cities.Köln], cost: 20 },
        { nodes: [Cities.Trier, Cities.Wiesbaden], cost: 18 },
        { nodes: [Cities.Trier, Cities.Saarbrücken], cost: 11 },
        { nodes: [Cities.Wiesbaden, Cities.FrankfurtM], cost: 0 },
        { nodes: [Cities.Wiesbaden, Cities.Köln], cost: 21 },
        { nodes: [Cities.Wiesbaden, Cities.Saarbrücken], cost: 10 },
        { nodes: [Cities.Wiesbaden, Cities.Mannheim], cost: 11 },
        { nodes: [Cities.Mannheim, Cities.Saarbrücken], cost: 11 },
        { nodes: [Cities.Mannheim, Cities.Stuttgart], cost: 6 },
        { nodes: [Cities.Stuttgart, Cities.Saarbrücken], cost: 17 },
        { nodes: [Cities.Stuttgart, Cities.Freiburg], cost: 16 },
        { nodes: [Cities.Stuttgart, Cities.Konstanz], cost: 16 },
        { nodes: [Cities.Stuttgart, Cities.Augsburg], cost: 15 },
        { nodes: [Cities.Konstanz, Cities.Freiburg], cost: 14 },
        { nodes: [Cities.Konstanz, Cities.Augsburg], cost: 17 },
        { nodes: [Cities.Regensburg, Cities.Augsburg], cost: 13 },
        { nodes: [Cities.Regensburg, Cities.München], cost: 10 },
        { nodes: [Cities.Regensburg, Cities.Passau], cost: 12 },
        { nodes: [Cities.Augsburg, Cities.München], cost: 6 },
        { nodes: [Cities.Passau, Cities.München], cost: 14 },
    ],
    layout: 'Landscape',
    mapPosition: [20, 20],
};

export const mapRecharged: GameMap = {
    name: 'Germany',
    cities: [
        { name: Cities.Flensburg, region: Regions.Green, x: 37, y: 427 },
        { name: Cities.Kiel, region: Regions.Green, x: 106, y: 392 },
        { name: Cities.Hamburg, region: Regions.Green, x: 212, y: 396 },
        { name: Cities.Hannover, region: Regions.Green, x: 378, y: 395 },
        { name: Cities.Bremen, region: Regions.Green, x: 276, y: 463 },
        { name: Cities.Wilhelmshaven, region: Regions.Green, x: 211, y: 521 },
        { name: Cities.Cuxhaven, region: Regions.Green, x: 168, y: 474 },
        { name: Cities.Lubeck, region: Regions.Brown, x: 153, y: 341 },
        { name: Cities.Rostock, region: Regions.Brown, x: 128, y: 256 },
        { name: Cities.Schwerin, region: Regions.Brown, x: 217, y: 297 },
        { name: Cities.Stralsund, region: Regions.Brown, x: 210, y: 126 },
        { name: Cities.Magdeburg, region: Regions.Brown, x: 389, y: 271 },
        { name: Cities.Berlin, region: Regions.Brown, x: 355, y: 170 },
        { name: Cities.FrankfurtO, region: Regions.Brown, x: 381, y: 99 },
        { name: Cities.Halle, region: Regions.Yellow, x: 493, y: 259 },
        { name: Cities.Leipzig, region: Regions.Yellow, x: 526, y: 222 },
        { name: Cities.Dresden, region: Regions.Yellow, x: 572, y: 126 },
        { name: Cities.Erfurt, region: Regions.Yellow, x: 567, y: 309 },
        { name: Cities.Fulda, region: Regions.Yellow, x: 628, y: 398 },
        { name: Cities.Würzburg, region: Regions.Yellow, x: 735, y: 386 },
        { name: Cities.Nurnberg, region: Regions.Yellow, x: 780, y: 309 },
        { name: Cities.Osnabrück, region: Regions.Red, x: 359, y: 516 },
        { name: Cities.Münster, region: Regions.Red, x: 427, y: 554 },
        { name: Cities.Essen, region: Regions.Red, x: 475, y: 603 },
        { name: Cities.Duisburg, region: Regions.Red, x: 456, y: 645 },
        { name: Cities.Dortmund, region: Regions.Red, x: 505, y: 543 },
        { name: Cities.Dusseldorf, region: Regions.Red, x: 537, y: 635 },
        { name: Cities.Kassel, region: Regions.Red, x: 524, y: 430 },
        { name: Cities.Aachen, region: Regions.Cyan, x: 614, y: 654 },
        { name: Cities.Köln, region: Regions.Cyan, x: 590, y: 589 },
        { name: Cities.Trier, region: Regions.Cyan, x: 739, y: 628 },
        { name: Cities.Mainz, region: Regions.Cyan, x: 697, y: 514 },
        { name: Cities.FrankfurtM, region: Regions.Cyan, x: 672, y: 473 },
        { name: Cities.Saarbrücken, region: Regions.Cyan, x: 818, y: 568 },
        { name: Cities.Mannheim, region: Regions.Cyan, x: 796, y: 479 },
        { name: Cities.Freiburg, region: Regions.Purple, x: 966, y: 537 },
        { name: Cities.Stuttgart, region: Regions.Purple, x: 884, y: 458 },
        { name: Cities.Konstanz, region: Regions.Purple, x: 1011, y: 459 },
        { name: Cities.Augsburg, region: Regions.Purple, x: 911, y: 346 },
        { name: Cities.Regensburg, region: Regions.Purple, x: 846, y: 256 },
        { name: Cities.München, region: Regions.Purple, x: 967, y: 278 },
        { name: Cities.Passau, region: Regions.Purple, x: 904, y: 153 },
    ],
    connections: [
        { nodes: [Cities.Flensburg, Cities.Kiel], cost: 4 },
        { nodes: [Cities.Kiel, Cities.Hamburg], cost: 8 },
        { nodes: [Cities.Kiel, Cities.Lubeck], cost: 4 },
        { nodes: [Cities.Hamburg, Cities.Hannover], cost: 17 },
        { nodes: [Cities.Hamburg, Cities.Bremen], cost: 11 },
        { nodes: [Cities.Hamburg, Cities.Cuxhaven], cost: 11 },
        { nodes: [Cities.Hamburg, Cities.Lubeck], cost: 6 },
        { nodes: [Cities.Hamburg, Cities.Schwerin], cost: 8 },
        { nodes: [Cities.Bremen, Cities.Wilhelmshaven], cost: 11 },
        { nodes: [Cities.Bremen, Cities.Hannover], cost: 10 },
        { nodes: [Cities.Bremen, Cities.Cuxhaven], cost: 8 },
        { nodes: [Cities.Bremen, Cities.Osnabrück], cost: 11 },
        { nodes: [Cities.Hannover, Cities.Schwerin], cost: 19 },
        { nodes: [Cities.Hannover, Cities.Magdeburg], cost: 15 },
        { nodes: [Cities.Hannover, Cities.Erfurt], cost: 19 },
        { nodes: [Cities.Hannover, Cities.Osnabrück], cost: 16 },
        { nodes: [Cities.Hannover, Cities.Kassel], cost: 15 },
        { nodes: [Cities.Wilhelmshaven, Cities.Osnabrück], cost: 14 },
        { nodes: [Cities.Lubeck, Cities.Schwerin], cost: 6 },
        { nodes: [Cities.Schwerin, Cities.Rostock], cost: 6 },
        { nodes: [Cities.Schwerin, Cities.Stralsund], cost: 19 },
        { nodes: [Cities.Schwerin, Cities.Berlin], cost: 18 },
        { nodes: [Cities.Schwerin, Cities.Magdeburg], cost: 16 },
        { nodes: [Cities.Stralsund, Cities.Rostock], cost: 19 },
        { nodes: [Cities.Stralsund, Cities.Berlin], cost: 15 },
        { nodes: [Cities.Berlin, Cities.Magdeburg], cost: 10 },
        { nodes: [Cities.Berlin, Cities.FrankfurtO], cost: 6 },
        { nodes: [Cities.Berlin, Cities.Halle], cost: 17 },
        { nodes: [Cities.Magdeburg, Cities.Halle], cost: 11 },
        { nodes: [Cities.FrankfurtO, Cities.Leipzig], cost: 21 },
        { nodes: [Cities.FrankfurtO, Cities.Dresden], cost: 16 },
        { nodes: [Cities.Halle, Cities.Leipzig], cost: 0 },
        { nodes: [Cities.Leipzig, Cities.Dresden], cost: 13 },
        { nodes: [Cities.Erfurt, Cities.Halle], cost: 6 },
        { nodes: [Cities.Erfurt, Cities.Dresden], cost: 19 },
        { nodes: [Cities.Erfurt, Cities.Nurnberg], cost: 21 },
        { nodes: [Cities.Erfurt, Cities.Fulda], cost: 13 },
        { nodes: [Cities.Erfurt, Cities.Kassel], cost: 15 },
        { nodes: [Cities.Fulda, Cities.Würzburg], cost: 11 },
        { nodes: [Cities.Fulda, Cities.Kassel], cost: 8 },
        { nodes: [Cities.Fulda, Cities.FrankfurtM], cost: 8 },
        { nodes: [Cities.Würzburg, Cities.Nurnberg], cost: 8 },
        { nodes: [Cities.Würzburg, Cities.FrankfurtM], cost: 13 },
        { nodes: [Cities.Würzburg, Cities.Mannheim], cost: 10 },
        { nodes: [Cities.Würzburg, Cities.Stuttgart], cost: 12 },
        { nodes: [Cities.Würzburg, Cities.Augsburg], cost: 19 },
        { nodes: [Cities.Nurnberg, Cities.Augsburg], cost: 18 },
        { nodes: [Cities.Nurnberg, Cities.Regensburg], cost: 12 },
        { nodes: [Cities.Osnabrück, Cities.Münster], cost: 7 },
        { nodes: [Cities.Osnabrück, Cities.Kassel], cost: 20 },
        { nodes: [Cities.Münster, Cities.Essen], cost: 6 },
        { nodes: [Cities.Münster, Cities.Dortmund], cost: 2 },
        { nodes: [Cities.Essen, Cities.Duisburg], cost: 0 },
        { nodes: [Cities.Essen, Cities.Dusseldorf], cost: 2 },
        { nodes: [Cities.Essen, Cities.Dortmund], cost: 5 },
        { nodes: [Cities.Dortmund, Cities.Kassel], cost: 18 },
        { nodes: [Cities.Dortmund, Cities.Köln], cost: 10 },
        { nodes: [Cities.Dortmund, Cities.FrankfurtM], cost: 20 },
        { nodes: [Cities.Kassel, Cities.FrankfurtM], cost: 13 },
        { nodes: [Cities.Dusseldorf, Cities.Aachen], cost: 9 },
        { nodes: [Cities.Dusseldorf, Cities.Köln], cost: 4 },
        { nodes: [Cities.Aachen, Cities.Köln], cost: 7 },
        { nodes: [Cities.Aachen, Cities.Trier], cost: 19 },
        { nodes: [Cities.Trier, Cities.Köln], cost: 20 },
        { nodes: [Cities.Trier, Cities.Mainz], cost: 18 },
        { nodes: [Cities.Trier, Cities.Saarbrücken], cost: 11 },
        { nodes: [Cities.Mainz, Cities.FrankfurtM], cost: 0 },
        { nodes: [Cities.Mainz, Cities.Köln], cost: 21 },
        { nodes: [Cities.Mainz, Cities.Saarbrücken], cost: 10 },
        { nodes: [Cities.Mainz, Cities.Mannheim], cost: 11 },
        { nodes: [Cities.Mannheim, Cities.Saarbrücken], cost: 16 },
        { nodes: [Cities.Mannheim, Cities.Stuttgart], cost: 6 },
        { nodes: [Cities.Stuttgart, Cities.Saarbrücken], cost: 17 },
        { nodes: [Cities.Stuttgart, Cities.Freiburg], cost: 16 },
        { nodes: [Cities.Stuttgart, Cities.Konstanz], cost: 16 },
        { nodes: [Cities.Stuttgart, Cities.Augsburg], cost: 15 },
        { nodes: [Cities.Konstanz, Cities.Freiburg], cost: 14 },
        { nodes: [Cities.Konstanz, Cities.Augsburg], cost: 17 },
        { nodes: [Cities.Regensburg, Cities.Augsburg], cost: 13 },
        { nodes: [Cities.Regensburg, Cities.München], cost: 10 },
        { nodes: [Cities.Regensburg, Cities.Passau], cost: 12 },
        { nodes: [Cities.Augsburg, Cities.München], cost: 6 },
        { nodes: [Cities.Passau, Cities.München], cost: 14 },
    ],
    layout: 'Landscape',
    mapPosition: [20, 20],
    mapSpecificRules: 'Stop resupplying uranium after power plant 39 has been bought.',
};
