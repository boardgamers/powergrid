import { GameMap } from './../maps';

export enum Regions {
    Yellow = 'yellow',
    Red = 'red',
    Brown = 'brown',
    Green = 'green',
    Purple = 'purple',
    Pink = 'pink',
}

export enum Cities {
    Gyeongju = 'Gyeongju',
    Ulsan = 'Ulsan',
    Busan = 'Busan',
    Jinju = 'Jinju',
    Daegu = 'Daegu',
    Andong = 'Andong',
    Sangju = 'Sangju',
    Rasun = 'Rasun',
    Cheongjin = 'Cheongjin',
    Gyeongseong = 'Gyeongseong',
    Seongjin = 'Seongjin',
    Hyesan = 'Hyesan',
    Hamheung = 'Hamheung',
    Wonsan = 'Wonsan',
    Samcheok = 'Samcheok',
    Donghae = 'Donghae',
    Taeraek = 'Taeraek',
    Gangneung = 'Gangneung',
    Sokcho = 'Sokcho',
    Wonju = 'Wonju',
    Chuncheon = 'Chuncheon',
    Chungju = 'Chungju',
    Cheongju = 'Cheongju',
    Jeju = 'Jeju',
    Gwangju = 'Gwangju',
    Naju = 'Naju',
    Jeonju = 'Jeonju',
    Daejeon = 'Daejeon',
    Yongin = 'Yongin',
    Seoul = 'Seoul',
    Suwon = 'Suwon',
    Goyang = 'Goyang',
    Anyang = 'Anyang',
    Incheon = 'Incheon',
    Gaesung = 'Gaesung',
    Ganggye = 'Ganggye',
    Haeju = 'Haeju',
    Pyeongyang = 'Pyeongyang',
    Hwangju = 'Hwangju',
    Nampo = 'Nampo',
    Anju = 'Anju',
    Sinuiju = 'Sinuiju',
}

export const map: GameMap = {
    name: 'Korea',
    cities: [
        { name: Cities.Gyeongju, region: Regions.Yellow, x: 2161, y: 2980 },
        { name: Cities.Ulsan, region: Regions.Yellow, x: 2185, y: 3226 },
        { name: Cities.Busan, region: Regions.Yellow, x: 2041, y: 3440 },
        { name: Cities.Jinju, region: Regions.Yellow, x: 1676, y: 3431 },
        { name: Cities.Daegu, region: Regions.Yellow, x: 1876, y: 3062 },
        { name: Cities.Andong, region: Regions.Yellow, x: 1987, y: 2737 },
        { name: Cities.Sangju, region: Regions.Yellow, x: 1747, y: 2827 },
        { name: Cities.Rasun, region: Regions.Red, x: 2485, y: 361 },
        { name: Cities.Cheongjin, region: Regions.Red, x: 2309, y: 491 },
        { name: Cities.Gyeongseong, region: Regions.Red, x: 2209, y: 689 },
        { name: Cities.Seongjin, region: Regions.Red, x: 2060, y: 1001 },
        { name: Cities.Hyesan, region: Regions.Red, x: 1783, y: 665 },
        { name: Cities.Hamheung, region: Regions.Red, x: 1516, y: 1283 },
        { name: Cities.Wonsan, region: Regions.Red, x: 1484, y: 1600 },
        { name: Cities.Samcheok, region: Regions.Brown, x: 2171, y: 2437 },
        { name: Cities.Donghae, region: Regions.Brown, x: 2041, y: 2299 },
        { name: Cities.Taeraek, region: Regions.Brown, x: 1999, y: 2528 },
        { name: Cities.Gangneung, region: Regions.Brown, x: 1949, y: 2092 },
        { name: Cities.Sokcho, region: Regions.Brown, x: 1832, y: 1915 },
        { name: Cities.Wonju, region: Regions.Brown, x: 1735, y: 2293 },
        { name: Cities.Chuncheon, region: Regions.Brown, x: 1594, y: 2056 },
        { name: Cities.Chungju, region: Regions.Green, x: 1744, y: 2552 },
        { name: Cities.Cheongju, region: Regions.Green, x: 1547, y: 2645 },
        { name: Cities.Jeju, region: Regions.Green, x: 1223, y: 4051 },
        { name: Cities.Gwangju, region: Regions.Green, x: 1309, y: 3380 },
        { name: Cities.Naju, region: Regions.Green, x: 1121, y: 3569 },
        { name: Cities.Jeonju, region: Regions.Green, x: 1363, y: 3109 },
        { name: Cities.Daejeon, region: Regions.Green, x: 1462, y: 2839 },
        { name: Cities.Yongin, region: Regions.Purple, x: 1532, y: 2371 },
        { name: Cities.Seoul, region: Regions.Purple, x: 1400, y: 2203 },
        { name: Cities.Suwon, region: Regions.Purple, x: 1366, y: 2488 },
        { name: Cities.Goyang, region: Regions.Purple, x: 1219, y: 2270 },
        { name: Cities.Anyang, region: Regions.Purple, x: 1156, y: 2446 },
        { name: Cities.Incheon, region: Regions.Purple, x: 1028, y: 2311 },
        { name: Cities.Gaesung, region: Regions.Purple, x: 1171, y: 2042 },
        { name: Cities.Ganggye, region: Regions.Pink, x: 1213, y: 809 },
        { name: Cities.Haeju, region: Regions.Pink, x: 856, y: 2135 },
        { name: Cities.Pyeongyang, region: Regions.Pink, x: 938, y: 1642 },
        { name: Cities.Hwangju, region: Regions.Pink, x: 901, y: 1886 },
        { name: Cities.Nampo, region: Regions.Pink, x: 677, y: 1763 },
        { name: Cities.Anju, region: Regions.Pink, x: 812, y: 1391 },
        { name: Cities.Sinuiju, region: Regions.Pink, x: 433, y: 1105 },
    ],
    connections: [
        { nodes: [Cities.Naju, Cities.Jeju], cost: 19 },
        { nodes: [Cities.Naju, Cities.Jinju], cost: 15 },
        { nodes: [Cities.Jinju, Cities.Gwangju], cost: 14 },
        { nodes: [Cities.Gwangju, Cities.Naju], cost: 2 },
        { nodes: [Cities.Gwangju, Cities.Jeonju], cost: 11 },
        { nodes: [Cities.Jeonju, Cities.Jinju], cost: 15 },
        { nodes: [Cities.Jinju, Cities.Busan], cost: 11 },
        { nodes: [Cities.Jinju, Cities.Daegu], cost: 11 },
        { nodes: [Cities.Daegu, Cities.Jeonju], cost: 16 },
        { nodes: [Cities.Daegu, Cities.Busan], cost: 12 },
        { nodes: [Cities.Busan, Cities.Ulsan], cost: 7 },
        { nodes: [Cities.Ulsan, Cities.Daegu], cost: 10 },
        { nodes: [Cities.Jeonju, Cities.Daejeon], cost: 9 },
        { nodes: [Cities.Daejeon, Cities.Daegu], cost: 15 },
        { nodes: [Cities.Andong, Cities.Gyeongju], cost: 11 },
        { nodes: [Cities.Gyeongju, Cities.Daegu], cost: 7 },
        { nodes: [Cities.Gyeongju, Cities.Ulsan], cost: 3 },
        { nodes: [Cities.Daegu, Cities.Sangju], cost: 9 },
        { nodes: [Cities.Sangju, Cities.Daejeon], cost: 8 },
        { nodes: [Cities.Daegu, Cities.Andong], cost: 10 },
        { nodes: [Cities.Andong, Cities.Sangju], cost: 6 },
        { nodes: [Cities.Andong, Cities.Taeraek], cost: 8 },
        { nodes: [Cities.Taeraek, Cities.Samcheok], cost: 5 },
        { nodes: [Cities.Samcheok, Cities.Donghae], cost: 0 },
        { nodes: [Cities.Donghae, Cities.Gangneung], cost: 4 },
        { nodes: [Cities.Chungju, Cities.Taeraek], cost: 13 },
        { nodes: [Cities.Andong, Cities.Chungju], cost: 11 },
        { nodes: [Cities.Chungju, Cities.Cheongju], cost: 7 },
        { nodes: [Cities.Cheongju, Cities.Sangju], cost: 8 },
        { nodes: [Cities.Sangju, Cities.Chungju], cost: 9 },
        { nodes: [Cities.Daejeon, Cities.Cheongju], cost: 4 },
        { nodes: [Cities.Wonju, Cities.Donghae], cost: 14 },
        { nodes: [Cities.Wonju, Cities.Taeraek], cost: 13 },
        { nodes: [Cities.Chungju, Cities.Wonju], cost: 5 },
        { nodes: [Cities.Wonju, Cities.Gangneung], cost: 12 },
        { nodes: [Cities.Wonju, Cities.Sokcho], cost: 15 },
        { nodes: [Cities.Sokcho, Cities.Gangneung], cost: 6 },
        { nodes: [Cities.Chuncheon, Cities.Wonju], cost: 7 },
        { nodes: [Cities.Sinuiju, Cities.Ganggye], cost: 25 },
        { nodes: [Cities.Ganggye, Cities.Hyesan], cost: 20 },
        { nodes: [Cities.Sinuiju, Cities.Anju], cost: 13 },
        { nodes: [Cities.Anju, Cities.Ganggye], cost: 22 },
        { nodes: [Cities.Ganggye, Cities.Hamheung], cost: 19 },
        { nodes: [Cities.Hamheung, Cities.Anju], cost: 20 },
        { nodes: [Cities.Anju, Cities.Nampo], cost: 10 },
        { nodes: [Cities.Anju, Cities.Pyeongyang], cost: 7 },
        { nodes: [Cities.Pyeongyang, Cities.Nampo], cost: 5 },
        { nodes: [Cities.Nampo, Cities.Hwangju], cost: 4 },
        { nodes: [Cities.Hwangju, Cities.Pyeongyang], cost: 4 },
        { nodes: [Cities.Pyeongyang, Cities.Wonsan], cost: 18 },
        { nodes: [Cities.Pyeongyang, Cities.Hamheung], cost: 23 },
        { nodes: [Cities.Hamheung, Cities.Wonsan], cost: 11 },
        { nodes: [Cities.Pyeongyang, Cities.Gaesung], cost: 14 },
        { nodes: [Cities.Gaesung, Cities.Haeju], cost: 8 },
        { nodes: [Cities.Haeju, Cities.Hwangju], cost: 8 },
        { nodes: [Cities.Gaesung, Cities.Goyang], cost: 7 },
        { nodes: [Cities.Anyang, Cities.Suwon], cost: 3 },
        { nodes: [Cities.Suwon, Cities.Yongin], cost: 2 },
        { nodes: [Cities.Goyang, Cities.Incheon], cost: 0 },
        { nodes: [Cities.Incheon, Cities.Anyang], cost: 0 },
        { nodes: [Cities.Goyang, Cities.Seoul], cost: 0 },
        { nodes: [Cities.Suwon, Cities.Cheongju], cost: 10 },
        { nodes: [Cities.Seoul, Cities.Yongin], cost: 2 },
        { nodes: [Cities.Gaesung, Cities.Chuncheon], cost: 13 },
        { nodes: [Cities.Gaesung, Cities.Wonsan], cost: 18 },
        { nodes: [Cities.Wonsan, Cities.Sokcho], cost: 18 },
        { nodes: [Cities.Wonsan, Cities.Chuncheon], cost: 19 },
        { nodes: [Cities.Sokcho, Cities.Chuncheon], cost: 10 },
        { nodes: [Cities.Chuncheon, Cities.Seoul], cost: 8 },
        { nodes: [Cities.Chuncheon, Cities.Yongin], cost: 9 },
        { nodes: [Cities.Yongin, Cities.Wonju], cost: 8 },
        { nodes: [Cities.Yongin, Cities.Chungju], cost: 10 },
        { nodes: [Cities.Yongin, Cities.Cheongju], cost: 10 },
        { nodes: [Cities.Rasun, Cities.Cheongjin], cost: 8 },
        { nodes: [Cities.Cheongjin, Cities.Gyeongseong], cost: 4 },
        { nodes: [Cities.Gyeongseong, Cities.Seongjin], cost: 16 },
        { nodes: [Cities.Hyesan, Cities.Gyeongseong], cost: 18 },
        { nodes: [Cities.Hyesan, Cities.Seongjin], cost: 14 },
        { nodes: [Cities.Seongjin, Cities.Hamheung], cost: 17 },
        { nodes: [Cities.Hamheung, Cities.Hyesan], cost: 23 },
    ],
    layout: 'Portrait',
    adjustRatio: [0.22, 0.22],
    mapPosition: [80, 30],
    // Taller than the default Portrait viewBox to make room for Korea's stacked
    // dual resource markets (North above South).
    viewBox: [1480, 1180],
    supplyPosition: [675, 1040],
    // South-side resource market.
    // Indexed [resource][playerCount-2][step-1].
    // Verified from the Korea Recharged rulebook resource table (S rows).
    resupply: [
        // Coal (S)
        [
            [2, 2, 2], // 2P
            [2, 3, 2], // 3P
            [3, 3, 2], // 4P
            [3, 4, 3], // 5P
            [4, 5, 3], // 6P
        ],
        // Oil (S)
        [
            [1, 1, 3],
            [1, 2, 3],
            [2, 3, 3],
            [3, 3, 4],
            [3, 4, 4],
        ],
        // Garbage (S)
        [
            [1, 1, 2],
            [1, 1, 2],
            [1, 2, 2],
            [2, 2, 3],
            [2, 3, 3],
        ],
        // Uranium (S only — North bans nuclear resupply)
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 2, 2],
            [2, 3, 2],
            [2, 3, 3],
        ],
    ],
    // North-side resource market. Three resources only (no uranium row).
    // Verified from the Korea Recharged rulebook resource table (N rows).
    resupplyNorth: [
        // Coal (N)
        [
            [1, 2, 1],
            [2, 2, 1],
            [2, 3, 2],
            [2, 3, 2],
            [3, 4, 3],
        ],
        // Oil (N)
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 2],
            [1, 2, 2],
            [2, 2, 3],
        ],
        // Garbage (N)
        [
            [0, 1, 1],
            [0, 1, 1],
            [1, 1, 2],
            [1, 1, 2],
            [1, 2, 3],
        ],
    ],
    // Korea has custom slot counts per price space, different per side.
    // Total resources (across both markets + supply) match standard Power Grid:
    // 24 coal, 24 oil, 24 garbage, 12 uranium.
    //
    // North slots per price [1..8]:
    //   coal [2,2,2,2,1,1,1,1] = 12 total
    //   oil  [1,1,1,1,1,1,1,1] = 8 total
    //   garbage [1,1,1,1,1,1,1,1] = 8 total
    //
    // South slots per price [1..8] (uranium prices [1..8,10,12,14,16]):
    //   coal [1,1,1,1,2,2,2,2] = 12 total
    //   oil  [2,2,2,2,2,2,2,2] = 16 total
    //   garbage [2,2,2,2,2,2,2,2] = 16 total
    //   uranium [1,1,1,1,1,1,1,1,1,1,1,1] = 12 total
    //
    // Initial market fill per rulebook:
    //   North: coal 1–8 (12), oil 3–8 (6), garbage 7–8 (2).
    //   South: coal 1–8 (12), oil 3–8 (12), garbage 7–8 (4), uranium 14–16 (2).
    startingResources: [12, 12, 4, 2], // South initial market: coal, oil, garbage, uranium
    startingResourcesNorth: [12, 6, 2], // North initial market: coal, oil, garbage
    // Total cubes in the game across BOTH markets + shared supply.
    // Used cubes return to the shared supply; on bureaucracy, North restocks
    // first, then South from whatever remains.
    startingSupply: [24, 24, 24, 12],
    coalPrices: [1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    oilPrices: [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    garbagePrices: [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    uraniumPrices: [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16],
    coalPricesNorth: [1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 7, 8],
    oilPricesNorth: [1, 2, 3, 4, 5, 6, 7, 8],
    garbagePricesNorth: [1, 2, 3, 4, 5, 6, 7, 8],
    mapSpecificRules:
        'Korea has two separate resource markets: North and South. On your buying turn, choose one side — all resources you buy that turn must come from that side. The next turn you may choose the other side. The North market has no uranium track; uranium is only available from the South market. Each market restocks independently from its own supply pool during the bureaucracy phase.',
};
