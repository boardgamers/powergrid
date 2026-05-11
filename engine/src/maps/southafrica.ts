import { GameMap } from './../maps';

export enum Regions {
    Orange = 'orange',
    Green = 'green',
    Yellow = 'yellow',
    Brown = 'brown',
    Red = 'red',
}

export enum Cities {
    Zimbabwe = 'Zimbabwe',
    Musina = 'Musina',
    Botswana = 'Botswana',
    Polokwane = 'Polokwane',
    PretoriaN = 'Pretoria N',
    PretoriaS = 'Pretoria S',
    Rustenburg = 'Rustenburg',
    Mozambique = 'Mozambique',
    Mbombela = 'Mbombela',
    Eswatini = 'Eswatini',
    Germiston = 'Germiston',
    JohannesburgN = 'Johannesburg N',
    JohannesburgS = 'Johannesburg S',
    Ladysmith = 'Ladysmith',
    Newcastle = 'Newcastle',
    Pietermaritzburg = 'Pietermaritzburg',
    DurbanN = 'Durban N',
    DurbanS = 'Durban S',
    Jkl = 'Jkl',
    Lesotho = 'Lesotho',
    Bloemfontein = 'Bloemfontein',
    Klerksdorp = 'Klerksdorp',
    Welkom = 'Welkom',
    Kuruman = 'Kuruman',
    Kimberly = 'Kimberly',
    Upington = 'Upington',
    Springbok = 'Springbok',
    Namibia = 'Namibia',
    DeAar = 'De Aar',
    BeaufortWest = 'Beaufort West',
    EastLondon = 'East London',
    PortElizabeth = 'Port Elizabeth',
    George = 'George',
    CapeTownN = 'Cape Town N',
    CapeTownS = 'Cape Town S',
}

export const map: GameMap = {
    name: 'South Africa',
    cities: [
        { name: Cities.Zimbabwe, region: Regions.Orange, x: 1060, y: 29 },
        { name: Cities.Musina, region: Regions.Orange, x: 1027, y: 125 },
        { name: Cities.Botswana, region: Regions.Orange, x: 665, y: 186 },
        { name: Cities.Polokwane, region: Regions.Orange, x: 944, y: 188 },
        { name: Cities.PretoriaN, region: Regions.Orange, x: 894, y: 271 },
        { name: Cities.PretoriaS, region: Regions.Orange, x: 894, y: 306 },
        { name: Cities.Rustenburg, region: Regions.Orange, x: 787, y: 327 },
        { name: Cities.Mozambique, region: Regions.Green, x: 1184, y: 167 },
        { name: Cities.Mbombela, region: Regions.Green, x: 1046, y: 287 },
        { name: Cities.Eswatini, region: Regions.Green, x: 1086, y: 375 },
        { name: Cities.Germiston, region: Regions.Green, x: 983, y: 375 },
        { name: Cities.JohannesburgN, region: Regions.Green, x: 887, y: 365 },
        { name: Cities.JohannesburgS, region: Regions.Green, x: 889, y: 398 },
        { name: Cities.Ladysmith, region: Regions.Green, x: 968, y: 495 },
        { name: Cities.Newcastle, region: Regions.Yellow, x: 1122, y: 521 },
        { name: Cities.Pietermaritzburg, region: Regions.Yellow, x: 1000, y: 558 },
        { name: Cities.DurbanN, region: Regions.Yellow, x: 1049, y: 618 },
        { name: Cities.DurbanS, region: Regions.Yellow, x: 1048, y: 651 },
        { name: Cities.Jkl, region: Regions.Yellow, x: 931, y: 733 },
        { name: Cities.Lesotho, region: Regions.Yellow, x: 894, y: 572 },
        { name: Cities.Bloemfontein, region: Regions.Yellow, x: 776, y: 556 },
        { name: Cities.Klerksdorp, region: Regions.Brown, x: 780, y: 387 },
        { name: Cities.Welkom, region: Regions.Brown, x: 771, y: 467 },
        { name: Cities.Kuruman, region: Regions.Brown, x: 595, y: 415 },
        { name: Cities.Kimberly, region: Regions.Brown, x: 670, y: 541 },
        { name: Cities.Upington, region: Regions.Brown, x: 456, y: 492 },
        { name: Cities.Springbok, region: Regions.Brown, x: 264, y: 580 },
        { name: Cities.Namibia, region: Regions.Brown, x: 239, y: 329 },
        { name: Cities.DeAar, region: Regions.Red, x: 641, y: 735 },
        { name: Cities.BeaufortWest, region: Regions.Red, x: 513, y: 782 },
        { name: Cities.EastLondon, region: Regions.Red, x: 852, y: 833 },
        { name: Cities.PortElizabeth, region: Regions.Red, x: 712, y: 903 },
        { name: Cities.George, region: Regions.Red, x: 526, y: 903 },
        { name: Cities.CapeTownN, region: Regions.Red, x: 290, y: 871 },
        { name: Cities.CapeTownS, region: Regions.Red, x: 287, y: 904 },
    ],
    connections: [
        { nodes: [Cities.Springbok, Cities.Namibia], cost: 30 },
        { nodes: [Cities.Bloemfontein, Cities.Lesotho], cost: 30 },
        { nodes: [Cities.Germiston, Cities.Eswatini], cost: 30 },
        { nodes: [Cities.Mbombela, Cities.Mozambique], cost: 30 },
        { nodes: [Cities.Botswana, Cities.Rustenburg], cost: 30 },
        { nodes: [Cities.Zimbabwe, Cities.Musina], cost: 30 },
        { nodes: [Cities.CapeTownS, Cities.CapeTownN], cost: 0 },
        { nodes: [Cities.CapeTownS, Cities.George], cost: 16 },
        { nodes: [Cities.George, Cities.PortElizabeth], cost: 12 },
        { nodes: [Cities.PortElizabeth, Cities.EastLondon], cost: 13 },
        { nodes: [Cities.EastLondon, Cities.Jkl], cost: 8 },
        { nodes: [Cities.Jkl, Cities.DurbanS], cost: 13 },
        { nodes: [Cities.DurbanS, Cities.DurbanN], cost: 0 },
        { nodes: [Cities.DurbanN, Cities.Pietermaritzburg], cost: 3 },
        { nodes: [Cities.DurbanN, Cities.Newcastle], cost: 9 },
        { nodes: [Cities.Newcastle, Cities.Pietermaritzburg], cost: 9 },
        { nodes: [Cities.Pietermaritzburg, Cities.Ladysmith], cost: 5 },
        { nodes: [Cities.Ladysmith, Cities.Newcastle], cost: 10 },
        { nodes: [Cities.Bloemfontein, Cities.Jkl], cost: 18 },
        { nodes: [Cities.Bloemfontein, Cities.EastLondon], cost: 22 },
        { nodes: [Cities.EastLondon, Cities.DeAar], cost: 22 },
        { nodes: [Cities.DeAar, Cities.PortElizabeth], cost: 18 },
        { nodes: [Cities.George, Cities.DeAar], cost: 17 },
        { nodes: [Cities.DeAar, Cities.BeaufortWest], cost: 10 },
        { nodes: [Cities.BeaufortWest, Cities.George], cost: 8 },
        { nodes: [Cities.BeaufortWest, Cities.CapeTownN], cost: 22 },
        { nodes: [Cities.CapeTownN, Cities.Springbok], cost: 22 },
        { nodes: [Cities.Springbok, Cities.BeaufortWest], cost: 24 },
        { nodes: [Cities.DeAar, Cities.Springbok], cost: 26 },
        { nodes: [Cities.Springbok, Cities.Upington], cost: 16 },
        { nodes: [Cities.Upington, Cities.DeAar], cost: 16 },
        { nodes: [Cities.DeAar, Cities.Bloemfontein], cost: 13 },
        { nodes: [Cities.Bloemfontein, Cities.Kimberly], cost: 6 },
        { nodes: [Cities.Kimberly, Cities.DeAar], cost: 10 },
        { nodes: [Cities.Kimberly, Cities.Upington], cost: 14 },
        { nodes: [Cities.Kimberly, Cities.Welkom], cost: 9 },
        { nodes: [Cities.Welkom, Cities.Bloemfontein], cost: 6 },
        { nodes: [Cities.Bloemfontein, Cities.Ladysmith], cost: 19 },
        { nodes: [Cities.Jkl, Cities.Pietermaritzburg], cost: 12 },
        { nodes: [Cities.Upington, Cities.Kuruman], cost: 11 },
        { nodes: [Cities.Musina, Cities.Polokwane], cost: 8 },
        { nodes: [Cities.Polokwane, Cities.PretoriaN], cost: 11 },
        { nodes: [Cities.PretoriaN, Cities.PretoriaS], cost: 0 },
        { nodes: [Cities.PretoriaS, Cities.JohannesburgN], cost: 2 },
        { nodes: [Cities.JohannesburgN, Cities.JohannesburgS], cost: 0 },
        { nodes: [Cities.JohannesburgS, Cities.Germiston], cost: 1 },
        { nodes: [Cities.JohannesburgN, Cities.Mbombela], cost: 13 },
        { nodes: [Cities.Mbombela, Cities.Germiston], cost: 13 },
        { nodes: [Cities.PretoriaN, Cities.Mbombela], cost: 13 },
        { nodes: [Cities.Mbombela, Cities.Polokwane], cost: 10 },
        { nodes: [Cities.Musina, Cities.Mbombela], cost: 15 },
        { nodes: [Cities.PretoriaN, Cities.Rustenburg], cost: 4 },
        { nodes: [Cities.Rustenburg, Cities.JohannesburgN], cost: 4 },
        { nodes: [Cities.JohannesburgN, Cities.Klerksdorp], cost: 7 },
        { nodes: [Cities.Klerksdorp, Cities.Welkom], cost: 5 },
        { nodes: [Cities.Bloemfontein, Cities.JohannesburgS], cost: 16 },
        { nodes: [Cities.Kuruman, Cities.Rustenburg], cost: 18 },
        { nodes: [Cities.Klerksdorp, Cities.Kuruman], cost: 12 },
        { nodes: [Cities.Kuruman, Cities.Kimberly], cost: 8 },
        { nodes: [Cities.JohannesburgS, Cities.Ladysmith], cost: 13 },
        { nodes: [Cities.Ladysmith, Cities.Germiston], cost: 13 },
    ],

    // Resupply per South Africa refill summary cards. Indexed as
    // [resource][playerCount-2][step-1]. Note: 2P and 3P rows are intentionally
    // identical on the printed cards (same pattern as North America).
    resupply: [
        // Coal
        [
            [4, 7, 5], // 2P
            [4, 7, 5], // 3P
            [5, 8, 6], // 4P
            [6, 9, 7], // 5P
            [7, 10, 8], // 6P
        ],
        // Oil
        [
            [1, 2, 1], // 2P
            [1, 2, 1], // 3P
            [2, 3, 2], // 4P
            [2, 4, 3], // 5P
            [4, 5, 4], // 6P
        ],
        // Garbage
        [
            [1, 3, 3], // 2P
            [1, 3, 3], // 3P
            [2, 4, 4], // 4P
            [3, 4, 5], // 5P
            [3, 6, 6], // 6P
        ],
        // Uranium
        [
            [1, 1, 2], // 2P
            [1, 1, 2], // 3P
            [2, 2, 3], // 4P
            [2, 3, 3], // 5P
            [2, 3, 4], // 6P
        ],
    ],
};
