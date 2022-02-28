import { GameMap } from './../maps';

export enum Regions {
    Brown = 'brown',
    Purple = 'purple',
    Red = 'red',
    Green = 'green',
    Yellow = 'yellow',
    Blue = 'blue',
}

export enum Cities {
    Siracusa = 'Siracusa',
    Reggiodical = 'Reggio Di Cal',
    Cosenza = 'Cosenza',
    Messina = 'Messina',
    Palermo = 'Palermo',
    Catania = 'Catania',
    Brindisi = 'Brindisi',
    Taranto = 'Taranto',
    Bari = 'Bari',
    Foggia = 'Foggia',
    Pesara = 'Pesara',
    Napoli = 'Napoli',
    Salerno = 'Salerno',
    Roma = 'Roma',
    Ancona = 'Ancona',
    Rimini = 'Rimini',
    Ravenna = 'Ravenna',
    Sanmarino = 'San Marino',
    Perugia = 'Perugia',
    Frienze = 'Frienze',
    Udine = 'Udine',
    Trieste = 'Trieste',
    Bolanzo = 'Bolanzo',
    Mestre = 'Mestre',
    Venezia = 'Venezia',
    Vicenza = 'Vicenza',
    Padua = 'Padua',
    Ferrara = 'Ferrara',
    Bologna = 'Bologna',
    Modena = 'Modena',
    Reggio = 'Reggio',
    Pisa = 'Pisa',
    Parma = 'Parma',
    Laspezia = 'La Spezia',
    Torino = 'Torino',
    Bergamo = 'Bergamo',
    Milano = 'Milano',
    Brescia = 'Brescia',
    Picenza = 'Picenza',
    Genova = 'Genova',
    Verona = 'Verona',
    Lovorno = 'Lovorno',
}

export const map: GameMap = {
    name: 'Italy',
    cities: [
        // { name: Cities.Siracusa, region: Regions.Brown, x: 117, y: 1048 },
        // { name: Cities.Reggiodical, region: Regions.Brown, x: 231, y: 1013 },
        // { name: Cities.Cosenza, region: Regions.Brown, x: 327, y: 960 },
        // { name: Cities.Messina, region: Regions.Brown, x: 214, y: 975 },
        // { name: Cities.Palermo, region: Regions.Brown, x: 120, y: 875 },
        // { name: Cities.Catania, region: Regions.Brown, x: 127, y: 1007 },
        // { name: Cities.Brindisi, region: Regions.Purple, x: 542, y: 945 },
        // { name: Cities.Taranto, region: Regions.Brown, x: 462, y: 933 },
        // { name: Cities.Bari, region: Regions.Purple, x: 516, y: 871 },
        // { name: Cities.Foggia, region: Regions.Purple, x: 483, y: 777 },
        // { name: Cities.Pesara, region: Regions.Purple, x: 476, y: 646 },
        // { name: Cities.Napoli, region: Regions.Purple, x: 344, y: 747 },
        // { name: Cities.Salerno, region: Regions.Purple, x: 353, y: 799 },
        // { name: Cities.Roma, region: Regions.Purple, x: 338, y: 583 },
        // { name: Cities.Ancona, region: Regions.Red, x: 531, y: 549 },
        // { name: Cities.Rimini, region: Regions.Red, x: 534, y: 459 },
        // { name: Cities.Ravenna, region: Regions.Red, x: 550, y: 401 },
        // { name: Cities.Sanmarino, region: Regions.Red, x: 465, y: 456 },
        // { name: Cities.Perugia, region: Regions.Red, x: 434, y: 507 },
        // { name: Cities.Frienze, region: Regions.Red, x: 401, y: 389 },
        // { name: Cities.Udine, region: Regions.Green, x: 734, y: 358 },
        // { name: Cities.Trieste, region: Regions.Green, x: 710, y: 410 },
        // { name: Cities.Bolanzo, region: Regions.Green, x: 702, y: 197 },
        // { name: Cities.Mestre, region: Regions.Green, x: 650, y: 318 },
        // { name: Cities.Venezia, region: Regions.Green, x: 639, y: 349 },
        // { name: Cities.Vicenza, region: Regions.Green, x: 626, y: 235 },
        // { name: Cities.Padua, region: Regions.Green, x: 611, y: 279 },
        // { name: Cities.Ferrara, region: Regions.Yellow, x: 548, y: 333 },
        // { name: Cities.Bologna, region: Regions.Yellow, x: 468, y: 350 },
        // { name: Cities.Modena, region: Regions.Yellow, x: 480, y: 303 },
        // { name: Cities.Reggio, region: Regions.Yellow, x: 458, y: 263 },
        // { name: Cities.Pisa, region: Regions.Yellow, x: 366, y: 304 },
        // { name: Cities.Parma, region: Regions.Yellow, x: 472, y: 224 },
        // { name: Cities.Laspezia, region: Regions.Yellow, x: 358, y: 245 },
        // { name: Cities.Torino, region: Regions.Blue, x: 350, y: 57 },
        // { name: Cities.Bergamo, region: Regions.Blue, x: 533, y: 125 },
        // { name: Cities.Milano, region: Regions.Blue, x: 453, y: 123 },
        // { name: Cities.Brescia, region: Regions.Blue, x: 544, y: 182 },
        // { name: Cities.Picenza, region: Regions.Blue, x: 450, y: 182 },
        // { name: Cities.Genova, region: Regions.Blue, x: 348, y: 182 },
        // { name: Cities.Verona, region: Regions.Blue, x: 557, y: 231 },
        // { name: Cities.Lovorno, region: Regions.Red, x: 349, y: 333 },
        { name: Cities.Siracusa, region: Regions.Brown, x: 1048, y: 471 },
        { name: Cities.Reggiodical, region: Regions.Brown, x: 1013, y: 346 },
        { name: Cities.Cosenza, region: Regions.Brown, x: 960, y: 240 },
        { name: Cities.Messina, region: Regions.Brown, x: 975, y: 365 },
        { name: Cities.Palermo, region: Regions.Brown, x: 875, y: 468 },
        { name: Cities.Catania, region: Regions.Brown, x: 1007, y: 460 },
        { name: Cities.Brindisi, region: Regions.Purple, x: 945, y: 4 },
        { name: Cities.Taranto, region: Regions.Brown, x: 933, y: 92 },
        { name: Cities.Bari, region: Regions.Purple, x: 871, y: 32 },
        { name: Cities.Foggia, region: Regions.Purple, x: 777, y: 69 },
        { name: Cities.Pesara, region: Regions.Purple, x: 646, y: 76 },
        { name: Cities.Napoli, region: Regions.Purple, x: 747, y: 222 },
        { name: Cities.Salerno, region: Regions.Purple, x: 799, y: 212 },
        { name: Cities.Roma, region: Regions.Purple, x: 583, y: 228 },
        { name: Cities.Ancona, region: Regions.Red, x: 549, y: 16 },
        { name: Cities.Rimini, region: Regions.Red, x: 459, y: 13 },
        { name: Cities.Ravenna, region: Regions.Red, x: 401, y: -5 },
        { name: Cities.Sanmarino, region: Regions.Red, x: 456, y: 88 },
        { name: Cities.Perugia, region: Regions.Red, x: 507, y: 123 },
        { name: Cities.Frienze, region: Regions.Red, x: 389, y: 159 },
        { name: Cities.Udine, region: Regions.Green, x: 358, y: -207 },
        { name: Cities.Trieste, region: Regions.Green, x: 410, y: -181 },
        { name: Cities.Bolanzo, region: Regions.Green, x: 197, y: -172 },
        { name: Cities.Mestre, region: Regions.Green, x: 318, y: -115 },
        { name: Cities.Venezia, region: Regions.Green, x: 349, y: -103 },
        { name: Cities.Vicenza, region: Regions.Green, x: 235, y: -89 },
        { name: Cities.Padua, region: Regions.Green, x: 279, y: -72 },
        { name: Cities.Torino, region: Regions.Blue, x: 57, y: 215 },
        { name: Cities.Bergamo, region: Regions.Blue, x: 125, y: 14 },
        { name: Cities.Milano, region: Regions.Blue, x: 123, y: 102 },
        { name: Cities.Brescia, region: Regions.Blue, x: 182, y: 2 },
        { name: Cities.Picenza, region: Regions.Blue, x: 182, y: 105 },
        { name: Cities.Genova, region: Regions.Blue, x: 182, y: 217 },
        { name: Cities.Verona, region: Regions.Blue, x: 231, y: -13 },
        { name: Cities.Lovorno, region: Regions.Red, x: 333, y: 216 },
        { name: Cities.Ferrara, region: Regions.Yellow, x: 333, y: -3 },
        { name: Cities.Bologna, region: Regions.Yellow, x: 350, y: 85 },
        { name: Cities.Modena, region: Regions.Yellow, x: 303, y: 72 },
        { name: Cities.Reggio, region: Regions.Yellow, x: 263, y: 96 },
        { name: Cities.Pisa, region: Regions.Yellow, x: 304, y: 197 },
        { name: Cities.Parma, region: Regions.Yellow, x: 224, y: 81 },
        { name: Cities.Laspezia, region: Regions.Yellow, x: 245, y: 206 },
    ],
    connections: [
        { nodes: [Cities.Palermo, Cities.Catania], cost: 15 },
        { nodes: [Cities.Catania, Cities.Siracusa], cost: 3 },
        { nodes: [Cities.Catania, Cities.Messina], cost: 6 },
        { nodes: [Cities.Messina, Cities.Palermo], cost: 15 },
        { nodes: [Cities.Messina, Cities.Reggiodical], cost: 3 },
        { nodes: [Cities.Reggiodical, Cities.Cosenza], cost: 13 },
        { nodes: [Cities.Cosenza, Cities.Salerno], cost: 18 },
        { nodes: [Cities.Cosenza, Cities.Taranto], cost: 15 },
        { nodes: [Cities.Taranto, Cities.Brindisi], cost: 4 },
        { nodes: [Cities.Brindisi, Cities.Bari], cost: 7 },
        { nodes: [Cities.Bari, Cities.Taranto], cost: 7 },
        { nodes: [Cities.Taranto, Cities.Salerno], cost: 19 },
        { nodes: [Cities.Salerno, Cities.Bari], cost: 16 },
        { nodes: [Cities.Bari, Cities.Foggia], cost: 8 },
        { nodes: [Cities.Foggia, Cities.Salerno], cost: 10 },
        { nodes: [Cities.Salerno, Cities.Napoli], cost: 3 },
        { nodes: [Cities.Napoli, Cities.Foggia], cost: 12 },
        { nodes: [Cities.Napoli, Cities.Roma], cost: 14 },
        { nodes: [Cities.Roma, Cities.Foggia], cost: 22 },
        { nodes: [Cities.Foggia, Cities.Pesara], cost: 10 },
        { nodes: [Cities.Pesara, Cities.Roma], cost: 14 },
        { nodes: [Cities.Roma, Cities.Ancona], cost: 17 },
        { nodes: [Cities.Roma, Cities.Perugia], cost: 13 },
        { nodes: [Cities.Perugia, Cities.Sanmarino], cost: 12 },
        { nodes: [Cities.Sanmarino, Cities.Rimini], cost: 0 },
        { nodes: [Cities.Rimini, Cities.Ancona], cost: 6 },
        { nodes: [Cities.Ancona, Cities.Perugia], cost: 10 },
        { nodes: [Cities.Roma, Cities.Frienze], cost: 20 },
        { nodes: [Cities.Lovorno, Cities.Roma], cost: 19 },
        { nodes: [Cities.Frienze, Cities.Perugia], cost: 13 },
        { nodes: [Cities.Frienze, Cities.Sanmarino], cost: 12 },
        { nodes: [Cities.Genova, Cities.Torino], cost: 12 },
        { nodes: [Cities.Torino, Cities.Milano], cost: 8 },
        { nodes: [Cities.Milano, Cities.Bergamo], cost: 3 },
        { nodes: [Cities.Bergamo, Cities.Bolanzo], cost: 12 },
        { nodes: [Cities.Bolanzo, Cities.Brescia], cost: 12 },
        { nodes: [Cities.Bolanzo, Cities.Mestre], cost: 12 },
        { nodes: [Cities.Bolanzo, Cities.Udine], cost: 14 },
        { nodes: [Cities.Udine, Cities.Trieste], cost: 4 },
        { nodes: [Cities.Udine, Cities.Venezia], cost: 7 },
        { nodes: [Cities.Venezia, Cities.Mestre], cost: 0 },
        { nodes: [Cities.Genova, Cities.Laspezia], cost: 5 },
        { nodes: [Cities.Laspezia, Cities.Pisa], cost: 5 },
        { nodes: [Cities.Pisa, Cities.Lovorno], cost: 0 },
        { nodes: [Cities.Genova, Cities.Milano], cost: 9 },
        { nodes: [Cities.Milano, Cities.Picenza], cost: 4 },
        { nodes: [Cities.Picenza, Cities.Parma], cost: 4 },
        { nodes: [Cities.Parma, Cities.Reggio], cost: 2 },
        { nodes: [Cities.Reggio, Cities.Modena], cost: 2 },
        { nodes: [Cities.Modena, Cities.Bologna], cost: 3 },
        { nodes: [Cities.Bologna, Cities.Pisa], cost: 12 },
        { nodes: [Cities.Pisa, Cities.Reggio], cost: 10 },
        { nodes: [Cities.Laspezia, Cities.Parma], cost: 9 },
        { nodes: [Cities.Laspezia, Cities.Reggio], cost: 9 },
        { nodes: [Cities.Genova, Cities.Picenza], cost: 7 },
        { nodes: [Cities.Genova, Cities.Parma], cost: 11 },
        { nodes: [Cities.Milano, Cities.Brescia], cost: 4 },
        { nodes: [Cities.Brescia, Cities.Bergamo], cost: 3 },
        { nodes: [Cities.Brescia, Cities.Verona], cost: 4 },
        { nodes: [Cities.Bolanzo, Cities.Vicenza], cost: 10 },
        { nodes: [Cities.Vicenza, Cities.Padua], cost: 3 },
        { nodes: [Cities.Vicenza, Cities.Verona], cost: 3 },
        { nodes: [Cities.Verona, Cities.Parma], cost: 6 },
        { nodes: [Cities.Parma, Cities.Brescia], cost: 6 },
        { nodes: [Cities.Verona, Cities.Padua], cost: 5 },
        { nodes: [Cities.Padua, Cities.Mestre], cost: 3 },
        { nodes: [Cities.Venezia, Cities.Ravenna], cost: 12 },
        { nodes: [Cities.Ravenna, Cities.Ferrara], cost: 4 },
        { nodes: [Cities.Ferrara, Cities.Venezia], cost: 9 },
        { nodes: [Cities.Ferrara, Cities.Padua], cost: 7 },
        { nodes: [Cities.Ferrara, Cities.Verona], cost: 7 },
        { nodes: [Cities.Verona, Cities.Modena], cost: 8 },
        { nodes: [Cities.Frienze, Cities.Pisa], cost: 5 },
        { nodes: [Cities.Frienze, Cities.Ravenna], cost: 10 },
        { nodes: [Cities.Ravenna, Cities.Rimini], cost: 4 },
        { nodes: [Cities.Frienze, Cities.Bologna], cost: 8 },
        { nodes: [Cities.Bologna, Cities.Ravenna], cost: 4 },
        { nodes: [Cities.Bologna, Cities.Ferrara], cost: 3 },
        { nodes: [Cities.Ferrara, Cities.Modena], cost: 4 },
    ],
    mapPosition: [-20, 320],
    startingResources: [18, 15, 12, 2],
    mapSpecificRules: 'Stop resupplying uranium after power plant 39 has been bought.',
};
