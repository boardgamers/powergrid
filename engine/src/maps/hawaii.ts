import { GameMap } from './../maps';

// HawaiiCustom: a community custom map (draft). Six regions across the island chain,
// warped as a fan (Kauai at the tip, the Big Island across the wide end).
// Twist = Hawaii's real economics: house prices by island, a higher payout, and
// sea crossings priced by real channel width. Generated from the layout draft.

export enum Regions {
    Green = 'green', // Kauai
    Red = 'red', // Oahu: Honolulu + Windward
    Yellow = 'yellow', // Oahu: North Shore + West
    Purple = 'purple', // Maui Nui
    Blue = 'blue', // Big Island West
    Brown = 'brown', // Big Island East
}

export enum Cities {
    Hanalei = 'Hanalei',
    NaPali = 'Na Pali',
    KalalauLookout = 'Kalalau Lookout',
    Kapaa = 'Kapaa',
    WaimeaCanyon = 'Waimea Canyon',
    Lihue = 'Lihue',
    Poipu = 'Poipu',
    Waianae = 'Waianae',
    Haleiwa = 'Haleiwa',
    WaimeaBay = 'Waimea Bay',
    SunsetBeach = 'Sunset Beach',
    Kahuku = 'Kahuku',
    Wahiawa = 'Wahiawa',
    KoOlina = 'Ko Olina',
    Kualoa = 'Kualoa',
    Kaneohe = 'Kaneohe',
    PearlHarbor = 'Pearl Harbor',
    Kailua = 'Kailua',
    Honolulu = 'Honolulu',
    Waikiki = 'Waikiki',
    HanaumaBay = 'Hanauma Bay',
    Kalaupapa = 'Kalaupapa',
    Lanai = 'Lanai',
    Kaanapali = 'Kaanapali',
    IaoValley = 'Iao Valley',
    Paia = 'Paia',
    Kihei = 'Kihei',
    Wailea = 'Wailea',
    Haleakala = 'Haleakala',
    Hana = 'Hana',
    Hawi = 'Hawi',
    Kamuela = 'Kamuela',
    Hapuna = 'Hapuna',
    Waikoloa = 'Waikoloa',
    Kona = 'Kona',
    CaptainCook = 'Captain Cook',
    PuuhonuaoHonaunau = 'Puuhonua o Honaunau',
    Waipio = 'Waipio',
    AkakaFalls = 'Akaka Falls',
    MaunaKea = 'Mauna Kea',
    Hilo = 'Hilo',
    Volcano = 'Volcano',
    Pahoa = 'Pahoa',
    Punaluu = 'Punaluu',
}

// House prices by island (standard is 10/15/20). Maui and Oahu are dear, the Big
// Island cheap. Kauai is standard: it already has the cheapest links on the board,
// so cheap houses on top made it too strong (BootlegTampico, Discord, 2026-11-17).
const MAUI = [12, 18, 24];
const OAHU = [11, 17, 22];
const KAUAI = [10, 15, 20];
const CHEAP = [8, 13, 18];

// Payout one Elektro higher at every step than the standard table: Hawaii's
// electricity is the most expensive in the US.
const paymentTable = [
    10, 22, 33, 44, 54, 64, 73, 82, 90, 98, 105, 112, 118, 124, 129, 134, 138, 142, 145, 148, 150, 150,
].map((v) => v + 1);

export const map: GameMap = {
    name: 'HawaiiCustom',
    cities: [
        { name: Cities.Hanalei, region: Regions.Green, slotCosts: KAUAI, x: 189, y: 115 },
        { name: Cities.NaPali, region: Regions.Green, slotCosts: KAUAI, x: 110, y: 161 },
        { name: Cities.KalalauLookout, region: Regions.Green, slotCosts: KAUAI, x: 112, y: 243 },
        { name: Cities.Kapaa, region: Regions.Green, slotCosts: KAUAI, x: 285, y: 137 },
        { name: Cities.WaimeaCanyon, region: Regions.Green, slotCosts: KAUAI, x: 174, y: 295 },
        { name: Cities.Lihue, region: Regions.Green, slotCosts: KAUAI, x: 297, y: 217 },
        { name: Cities.Poipu, region: Regions.Green, slotCosts: KAUAI, x: 255, y: 302 },
        { name: Cities.Waianae, region: Regions.Yellow, slotCosts: OAHU, x: 356, y: 392 },
        { name: Cities.Haleiwa, region: Regions.Yellow, slotCosts: OAHU, x: 379, y: 314 },
        { name: Cities.WaimeaBay, region: Regions.Yellow, slotCosts: OAHU, x: 416, y: 242 },
        { name: Cities.SunsetBeach, region: Regions.Yellow, slotCosts: OAHU, x: 453, y: 169 },
        { name: Cities.Kahuku, region: Regions.Yellow, slotCosts: OAHU, x: 531, y: 148 },
        { name: Cities.Wahiawa, region: Regions.Yellow, slotCosts: OAHU, x: 454, y: 348 },
        { name: Cities.KoOlina, region: Regions.Yellow, slotCosts: OAHU, x: 425, y: 439 },
        { name: Cities.Kualoa, region: Regions.Red, slotCosts: OAHU, x: 581, y: 212 },
        { name: Cities.Kaneohe, region: Regions.Red, slotCosts: OAHU, x: 627, y: 279 },
        { name: Cities.PearlHarbor, region: Regions.Red, slotCosts: OAHU, x: 513, y: 411 },
        { name: Cities.Kailua, region: Regions.Red, slotCosts: OAHU, x: 708, y: 281 },
        { name: Cities.Honolulu, region: Regions.Red, slotCosts: OAHU, x: 593, y: 400 },
        { name: Cities.Waikiki, region: Regions.Red, slotCosts: OAHU, x: 675, y: 400 },
        { name: Cities.HanaumaBay, region: Regions.Red, slotCosts: OAHU, x: 749, y: 351 },
        { name: Cities.Kalaupapa, region: Regions.Purple, slotCosts: MAUI, x: 711, y: 497 },
        { name: Cities.Lanai, region: Regions.Purple, slotCosts: MAUI, x: 700, y: 620 },
        { name: Cities.Kaanapali, region: Regions.Purple, slotCosts: MAUI, x: 791, y: 516 },
        { name: Cities.IaoValley, region: Regions.Purple, slotCosts: MAUI, x: 855, y: 567 },
        { name: Cities.Paia, region: Regions.Purple, slotCosts: MAUI, x: 934, y: 551 },
        { name: Cities.Kihei, region: Regions.Purple, slotCosts: MAUI, x: 835, y: 646 },
        { name: Cities.Wailea, region: Regions.Purple, slotCosts: MAUI, x: 865, y: 722 },
        { name: Cities.Haleakala, region: Regions.Purple, slotCosts: MAUI, x: 946, y: 636 },
        { name: Cities.Hana, region: Regions.Purple, slotCosts: MAUI, x: 1031, y: 609 },
        { name: Cities.Hawi, region: Regions.Blue, slotCosts: CHEAP, x: 912, y: 788 },
        { name: Cities.Kamuela, region: Regions.Blue, slotCosts: CHEAP, x: 932, y: 867 },
        { name: Cities.Hapuna, region: Regions.Blue, slotCosts: CHEAP, x: 821, y: 879 },
        { name: Cities.Waikoloa, region: Regions.Blue, slotCosts: CHEAP, x: 779, y: 961 },
        { name: Cities.Kona, region: Regions.Blue, slotCosts: CHEAP, x: 744, y: 1042 },
        { name: Cities.CaptainCook, region: Regions.Blue, slotCosts: CHEAP, x: 689, y: 1102 },
        { name: Cities.PuuhonuaoHonaunau, region: Regions.Blue, slotCosts: CHEAP, x: 787, y: 1125 },
        { name: Cities.Waipio, region: Regions.Brown, slotCosts: CHEAP, x: 1015, y: 792 },
        { name: Cities.AkakaFalls, region: Regions.Brown, slotCosts: CHEAP, x: 1126, y: 830 },
        { name: Cities.MaunaKea, region: Regions.Brown, slotCosts: CHEAP, x: 1011, y: 921 },
        { name: Cities.Hilo, region: Regions.Brown, slotCosts: CHEAP, x: 1236, y: 865 },
        { name: Cities.Volcano, region: Regions.Brown, slotCosts: CHEAP, x: 1110, y: 1007 },
        { name: Cities.Pahoa, region: Regions.Brown, slotCosts: CHEAP, x: 1280, y: 944 },
        { name: Cities.Punaluu, region: Regions.Brown, slotCosts: CHEAP, x: 980, y: 1105 },
    ],
    connections: [
        { nodes: [Cities.Hanalei, Cities.NaPali], cost: 4 },
        { nodes: [Cities.Hanalei, Cities.Kapaa], cost: 5 },
        { nodes: [Cities.NaPali, Cities.KalalauLookout], cost: 3 },
        { nodes: [Cities.KalalauLookout, Cities.WaimeaCanyon], cost: 3 },
        { nodes: [Cities.WaimeaCanyon, Cities.Poipu], cost: 4 },
        { nodes: [Cities.Poipu, Cities.Lihue], cost: 4 },
        { nodes: [Cities.Lihue, Cities.Kapaa], cost: 3 },
        { nodes: [Cities.KalalauLookout, Cities.Kapaa], cost: 9 },
        { nodes: [Cities.WaimeaCanyon, Cities.Lihue], cost: 7 },
        { nodes: [Cities.Lihue, Cities.Waianae], cost: 12, sea: true },
        { nodes: [Cities.Kapaa, Cities.Haleiwa], cost: 12, sea: true },
        { nodes: [Cities.Waianae, Cities.Haleiwa], cost: 6 },
        { nodes: [Cities.Haleiwa, Cities.WaimeaBay], cost: 4 },
        { nodes: [Cities.WaimeaBay, Cities.SunsetBeach], cost: 5 },
        { nodes: [Cities.SunsetBeach, Cities.Kahuku], cost: 5 },
        { nodes: [Cities.Kahuku, Cities.Kualoa], cost: 5 },
        { nodes: [Cities.Kualoa, Cities.Kaneohe], cost: 5 },
        { nodes: [Cities.Kaneohe, Cities.Kailua], cost: 5 },
        { nodes: [Cities.Kailua, Cities.HanaumaBay], cost: 5 },
        { nodes: [Cities.HanaumaBay, Cities.Waikiki], cost: 6 },
        { nodes: [Cities.Waikiki, Cities.Honolulu], cost: 5 },
        { nodes: [Cities.Honolulu, Cities.PearlHarbor], cost: 6 },
        { nodes: [Cities.PearlHarbor, Cities.KoOlina], cost: 6 },
        { nodes: [Cities.KoOlina, Cities.Waianae], cost: 6 },
        { nodes: [Cities.Wahiawa, Cities.Haleiwa], cost: 5 },
        { nodes: [Cities.Wahiawa, Cities.WaimeaBay], cost: 8 },
        { nodes: [Cities.Wahiawa, Cities.PearlHarbor], cost: 6 },
        { nodes: [Cities.Honolulu, Cities.Kaneohe], cost: 10 },
        { nodes: [Cities.HanaumaBay, Cities.Kalaupapa], cost: 8, sea: true },
        { nodes: [Cities.Honolulu, Cities.Lanai], cost: 10, sea: true },
        { nodes: [Cities.Kalaupapa, Cities.Lanai], cost: 4, sea: true },
        { nodes: [Cities.Kalaupapa, Cities.Kaanapali], cost: 4, sea: true },
        { nodes: [Cities.Lanai, Cities.Kaanapali], cost: 4, sea: true },
        { nodes: [Cities.Kaanapali, Cities.IaoValley], cost: 5 },
        { nodes: [Cities.IaoValley, Cities.Paia], cost: 6 },
        { nodes: [Cities.IaoValley, Cities.Kihei], cost: 5 },
        { nodes: [Cities.Kihei, Cities.Wailea], cost: 4 },
        { nodes: [Cities.Wailea, Cities.Haleakala], cost: 8 },
        { nodes: [Cities.Paia, Cities.Haleakala], cost: 6 },
        { nodes: [Cities.Paia, Cities.Hana], cost: 9 },
        { nodes: [Cities.Haleakala, Cities.Hana], cost: 7 },
        { nodes: [Cities.Kihei, Cities.Haleakala], cost: 7 },
        { nodes: [Cities.Hana, Cities.Hawi], cost: 9, sea: true },
        { nodes: [Cities.Wailea, Cities.Hapuna], cost: 10, sea: true },
        { nodes: [Cities.Hawi, Cities.Kamuela], cost: 7 },
        { nodes: [Cities.Hawi, Cities.Hapuna], cost: 11 },
        { nodes: [Cities.Kamuela, Cities.Hapuna], cost: 10 },
        { nodes: [Cities.Hapuna, Cities.Waikoloa], cost: 8 },
        { nodes: [Cities.Kamuela, Cities.Waikoloa], cost: 16 },
        { nodes: [Cities.Waikoloa, Cities.Kona], cost: 8 },
        { nodes: [Cities.Kona, Cities.CaptainCook], cost: 7 },
        { nodes: [Cities.CaptainCook, Cities.PuuhonuaoHonaunau], cost: 8 },
        { nodes: [Cities.Kamuela, Cities.Waipio], cost: 9 },
        { nodes: [Cities.Waipio, Cities.AkakaFalls], cost: 10 },
        { nodes: [Cities.AkakaFalls, Cities.Hilo], cost: 10 },
        { nodes: [Cities.Kamuela, Cities.MaunaKea], cost: 9 },
        { nodes: [Cities.MaunaKea, Cities.Hilo], cost: 20 },
        { nodes: [Cities.MaunaKea, Cities.Waikoloa], cost: 20 },
        { nodes: [Cities.Hilo, Cities.Pahoa], cost: 8 },
        { nodes: [Cities.Hilo, Cities.Volcano], cost: 16 },
        { nodes: [Cities.Pahoa, Cities.Volcano], cost: 16 },
        { nodes: [Cities.Volcano, Cities.Punaluu], cost: 14 },
        { nodes: [Cities.Punaluu, Cities.PuuhonuaoHonaunau], cost: 17 },
        // The ferry: Kauai and the Big Island sit at the two ends of the chain, so they
        // get a direct (and dear) crossing, drawn as a curve over open water.
        { nodes: [Cities.Poipu, Cities.Kona], cost: 31, sea: true, ignoreForRegions: true, via: [65, 672] },
    ],
    paymentTable,
    // Fuel is shipped in: the market starts with the three cheapest coal and the three
    // cheapest oil left in the supply, so coal starts at 2 and oil at 4. Garbage and
    // uranium start as each variant has them (Recharged fills garbage to 9).
    startingResources: { original: [21, 15, 6, 2], recharged: [21, 15, 9, 2] },
    mapSpecificRules:
        'House prices differ by island (see the key on the board). Payout is 1 Elektro higher at every step. ' +
        'Fuel is shipped in: at the start, coal begins at 2 and oil at 4. ' +
        'Dashed blue links are sea crossings. The Kauai-Big Island ferry (31) is a direct link, but it never ' +
        'counts as a border when regions are chosen: regions in play always join up over land and short crossings.',
    houseLegend: {
        position: [950, 150],
        names: {
            [Regions.Green]: 'Kauai',
            [Regions.Yellow]: 'Oahu North & West',
            [Regions.Red]: 'Oahu Honolulu',
            [Regions.Purple]: 'Maui Nui',
            [Regions.Blue]: 'Big Island West',
            [Regions.Brown]: 'Big Island East',
        },
    },
    // Portrait frame: the board gets the tall left side, the supply sits bottom-middle.
    layout: 'Portrait',
};
