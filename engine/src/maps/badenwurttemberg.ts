import { GameMap } from './../maps';

export enum Regions {
    Purple = 'purple',
    Green = 'green',
    Red = 'red',
    Blue = 'blue',
    Yellow = 'yellow',
}

export enum Cities {
    Friedrichshafen = 'Friedrichshafen',
    Ravensburg = 'Ravensburg',
    Biberach = 'Biberach',
    Sigmarincen = 'Sigmarincen',
    Konstanz = 'Konstanz',
    Ulm = 'Ulm',
    Augsburg = 'Augsburg',
    Basel = 'Basel',
    Waldshuttiencen = 'Waldshut-Tiencen',
    Singen = 'Singen',
    Tuttlincen = 'Tuttlincen',
    Donaueschingen = 'Donaueschingen',
    Freiburg = 'Freiburg',
    Lorrach = 'Lorrach',
    Tauberbischofsheim = 'Tauberbischofsheim',
    Schwabischhall = 'Schwabisch Hall',
    Heilbronn = 'Heilbronn',
    Sinsheim = 'Sinsheim',
    Heidelber = 'Heidelber',
    Mannheim = 'Mannheim',
    Luowigshafen = 'Luowigshafen',
    Nurnberg = 'Nurnberg',
    Ellwangen = 'Ellwangen',
    Coppingen = 'Coppingen',
    Reutlincen = 'Reutlincen',
    Stuttgart = 'Stuttgart',
    Ludwigsburg = 'Ludwigsburg',
    Boblingen = 'Boblingen',
    Laha = 'Laha',
    Badenbaden = 'Baden-Baden',
    Offenburg = 'Offenburg',
    Strasbourg = 'Strasbourg',
    Pforzheim = 'Pforzheim',
    Rastatt = 'Rastatt',
    Karlsruhf = 'Karlsruhf',
}

export const map: GameMap = {
    name: 'Baden-Württemberg',
    cities: [
        { name: Cities.Friedrichshafen, region: Regions.Purple, x: 1286, y: 2177 },
        { name: Cities.Ravensburg, region: Regions.Purple, x: 1365, y: 2023 },
        { name: Cities.Biberach, region: Regions.Purple, x: 1451, y: 1779 },
        { name: Cities.Sigmarincen, region: Regions.Purple, x: 1111, y: 1803 },
        { name: Cities.Konstanz, region: Regions.Purple, x: 1088, y: 2163 },
        { name: Cities.Ulm, region: Regions.Purple, x: 1541, y: 1499 },
        { name: Cities.Augsburg, region: Regions.Purple, x: 1830, y: 1505 },
        { name: Cities.Basel, region: Regions.Green, x: 103, y: 2271 },
        { name: Cities.Waldshuttiencen, region: Regions.Green, x: 502, y: 2166 },
        { name: Cities.Singen, region: Regions.Green, x: 874, y: 2084 },
        { name: Cities.Tuttlincen, region: Regions.Green, x: 870, y: 1854 },
        { name: Cities.Donaueschingen, region: Regions.Green, x: 669, y: 1923 },
        { name: Cities.Freiburg, region: Regions.Green, x: 290, y: 1828 },
        { name: Cities.Lorrach, region: Regions.Green, x: 212, y: 2141 },
        { name: Cities.Tauberbischofsheim, region: Regions.Red, x: 1354, y: 450 },
        { name: Cities.Schwabischhall, region: Regions.Red, x: 1415, y: 899 },
        { name: Cities.Heilbronn, region: Regions.Red, x: 1115, y: 872 },
        { name: Cities.Sinsheim, region: Regions.Red, x: 920, y: 785 },
        { name: Cities.Heidelber, region: Regions.Red, x: 817, y: 660 },
        { name: Cities.Mannheim, region: Regions.Red, x: 710, y: 540 },
        { name: Cities.Luowigshafen, region: Regions.Red, x: 579, y: 588 },
        { name: Cities.Nurnberg, region: Regions.Blue, x: 1837, y: 771 },
        { name: Cities.Ellwangen, region: Regions.Blue, x: 1637, y: 1030 },
        { name: Cities.Coppingen, region: Regions.Blue, x: 1387, y: 1233 },
        { name: Cities.Reutlincen, region: Regions.Blue, x: 1107, y: 1443 },
        { name: Cities.Stuttgart, region: Regions.Blue, x: 1106, y: 1217 },
        { name: Cities.Ludwigsburg, region: Regions.Blue, x: 1099, y: 1047 },
        { name: Cities.Boblingen, region: Regions.Blue, x: 956, y: 1277 },
        { name: Cities.Laha, region: Regions.Yellow, x: 296, y: 1575 },
        { name: Cities.Badenbaden, region: Regions.Yellow, x: 554, y: 1259 },
        { name: Cities.Offenburg, region: Regions.Yellow, x: 395, y: 1422 },
        { name: Cities.Strasbourg, region: Regions.Yellow, x: 211, y: 1330 },
        { name: Cities.Pforzheim, region: Regions.Yellow, x: 794, y: 1095 },
        { name: Cities.Rastatt, region: Regions.Yellow, x: 509, y: 1109 },
        { name: Cities.Karlsruhf, region: Regions.Yellow, x: 638, y: 974 },
    ],
    connections: [
        { nodes: [Cities.Luowigshafen, Cities.Mannheim], cost: 0 },
        { nodes: [Cities.Mannheim, Cities.Heidelber], cost: 4 },
        { nodes: [Cities.Mannheim, Cities.Karlsruhf], cost: 10 },
        { nodes: [Cities.Karlsruhf, Cities.Heidelber], cost: 9 },
        { nodes: [Cities.Heidelber, Cities.Sinsheim], cost: 5 },
        { nodes: [Cities.Sinsheim, Cities.Tauberbischofsheim], cost: 15 },
        { nodes: [Cities.Tauberbischofsheim, Cities.Heilbronn], cost: 13 },
        { nodes: [Cities.Heilbronn, Cities.Sinsheim], cost: 6 },
        { nodes: [Cities.Sinsheim, Cities.Karlsruhf], cost: 9 },
        { nodes: [Cities.Karlsruhf, Cities.Rastatt], cost: 4 },
        { nodes: [Cities.Karlsruhf, Cities.Pforzheim], cost: 6 },
        { nodes: [Cities.Pforzheim, Cities.Sinsheim], cost: 10 },
        { nodes: [Cities.Tauberbischofsheim, Cities.Schwabischhall], cost: 13 },
        { nodes: [Cities.Schwabischhall, Cities.Ellwangen], cost: 8 },
        { nodes: [Cities.Ellwangen, Cities.Nurnberg], cost: 18 },
        { nodes: [Cities.Schwabischhall, Cities.Coppingen], cost: 11 },
        { nodes: [Cities.Coppingen, Cities.Ellwangen], cost: 10 },
        { nodes: [Cities.Ludwigsburg, Cities.Heilbronn], cost: 5 },
        { nodes: [Cities.Heilbronn, Cities.Schwabischhall], cost: 9 },
        { nodes: [Cities.Schwabischhall, Cities.Ludwigsburg], cost: 10 },
        { nodes: [Cities.Ludwigsburg, Cities.Coppingen], cost: 9 },
        { nodes: [Cities.Coppingen, Cities.Stuttgart], cost: 8 },
        { nodes: [Cities.Ludwigsburg, Cities.Sinsheim], cost: 10 },
        { nodes: [Cities.Ludwigsburg, Cities.Pforzheim], cost: 8 },
        { nodes: [Cities.Pforzheim, Cities.Badenbaden], cost: 9 },
        { nodes: [Cities.Badenbaden, Cities.Rastatt], cost: 2 },
        { nodes: [Cities.Strasbourg, Cities.Offenburg], cost: 5 },
        { nodes: [Cities.Offenburg, Cities.Badenbaden], cost: 8 },
        { nodes: [Cities.Pforzheim, Cities.Stuttgart], cost: 8 },
        { nodes: [Cities.Stuttgart, Cities.Ludwigsburg], cost: 2 },
        { nodes: [Cities.Stuttgart, Cities.Boblingen], cost: 4 },
        { nodes: [Cities.Boblingen, Cities.Pforzheim], cost: 7 },
        { nodes: [Cities.Boblingen, Cities.Badenbaden], cost: 15 },
        { nodes: [Cities.Reutlincen, Cities.Stuttgart], cost: 9 },
        { nodes: [Cities.Boblingen, Cities.Reutlincen], cost: 8 },
        { nodes: [Cities.Reutlincen, Cities.Badenbaden], cost: 22 },
        { nodes: [Cities.Offenburg, Cities.Reutlincen], cost: 30 },
        { nodes: [Cities.Reutlincen, Cities.Coppingen], cost: 10 },
        { nodes: [Cities.Coppingen, Cities.Ulm], cost: 10 },
        { nodes: [Cities.Ulm, Cities.Reutlincen], cost: 16 },
        { nodes: [Cities.Ellwangen, Cities.Ulm], cost: 19 },
        { nodes: [Cities.Ulm, Cities.Augsburg], cost: 16 },
        { nodes: [Cities.Reutlincen, Cities.Tuttlincen], cost: 17 },
        { nodes: [Cities.Reutlincen, Cities.Sigmarincen], cost: 11 },
        { nodes: [Cities.Sigmarincen, Cities.Ulm], cost: 14 },
        { nodes: [Cities.Ulm, Cities.Biberach], cost: 8 },
        { nodes: [Cities.Biberach, Cities.Sigmarincen], cost: 11 },
        { nodes: [Cities.Biberach, Cities.Ravensburg], cost: 9 },
        { nodes: [Cities.Ravensburg, Cities.Sigmarincen], cost: 10 },
        { nodes: [Cities.Sigmarincen, Cities.Tuttlincen], cost: 7 },
        { nodes: [Cities.Tuttlincen, Cities.Offenburg], cost: 27 },
        { nodes: [Cities.Offenburg, Cities.Laha], cost: 3 },
        { nodes: [Cities.Laha, Cities.Freiburg], cost: 8 },
        { nodes: [Cities.Laha, Cities.Donaueschingen], cost: 19 },
        { nodes: [Cities.Donaueschingen, Cities.Tuttlincen], cost: 6 },
        { nodes: [Cities.Tuttlincen, Cities.Singen], cost: 7 },
        { nodes: [Cities.Singen, Cities.Donaueschingen], cost: 7 },
        { nodes: [Cities.Donaueschingen, Cities.Freiburg], cost: 13 },
        { nodes: [Cities.Freiburg, Cities.Lorrach], cost: 10 },
        { nodes: [Cities.Freiburg, Cities.Waldshuttiencen], cost: 15 },
        { nodes: [Cities.Waldshuttiencen, Cities.Lorrach], cost: 9 },
        { nodes: [Cities.Lorrach, Cities.Basel], cost: 2 },
        { nodes: [Cities.Waldshuttiencen, Cities.Donaueschingen], cost: 11 },
        { nodes: [Cities.Singen, Cities.Konstanz], cost: 6 },
        { nodes: [Cities.Konstanz, Cities.Friedrichshafen], cost: 9 },
        { nodes: [Cities.Friedrichshafen, Cities.Ravensburg], cost: 3 },
        { nodes: [Cities.Friedrichshafen, Cities.Sigmarincen], cost: 11 },
        { nodes: [Cities.Sigmarincen, Cities.Konstanz], cost: 14 },
        { nodes: [Cities.Konstanz, Cities.Tuttlincen], cost: 11 },
    ],
    layout: 'Portrait',
    adjustRatio: [0.425, 0.425],
    mapPosition: [100, -90],
};
