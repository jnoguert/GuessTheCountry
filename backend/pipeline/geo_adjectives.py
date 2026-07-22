"""Curated lists of geographic / nationality adjectives to black out.

Why this exists
---------------
The term-based censor pass (censor.py Pass 1) only knows the demonyms of a
country's *bordering* neighbours and of the country itself, and it gets those
from Wikidata's P1549. That data is very sparse outside English: of 194
countries only ~89 have a Catalan demonym and ~60 a Spanish one, and the
commonest ones referenced across articles (europeu, noruec, danès, britànic,
portuguès, africà, ...) are frequently missing. Continents and historical
regions/empires aren't modelled as countries at all, so they're never fetched.

Wikipedia articles are full of these *lowercase* adjectives ("un estat insular
europeu", "el capità noruec", "l'imperialisme britànic"). They escape every
existing pass: Pass 1 doesn't know them, Pass 2 only blacks out *capitalized*
words, and Pass 3 only covers the country's *own* name. Each one is a strong
geographic tell, so we censor them everywhere.

English is intentionally omitted: English nationality/continent adjectives are
always capitalized (European, Norwegian, British) and are already caught by the
proper-noun pass.

Forms are written out explicitly (masc/fem, singular/plural) rather than
generated, because Catalan/Spanish adjective morphology is too irregular
(Dinamarca->danès, Anglaterra->anglès, Egipte->faraònic, txec->txeca) for a
suffix expander to get right. Matching is whole-word and case-insensitive
(see create_censor_regex), so listing exact forms keeps over-censoring to
effectively zero.
"""

# Continents, sub-continental regions and broad cultural spheres.
_REGIONS_CA = [
    'europeu', 'europea', 'europeus', 'europees',
    'africà', 'africana', 'africans', 'africanes',
    'nord-africà', 'nord-africana', 'nord-africans', 'nord-africanes',
    'subsaharià', 'subsahariana', 'subsaharians', 'subsaharianes',
    'asiàtic', 'asiàtica', 'asiàtics', 'asiàtiques',
    'americà', 'americana', 'americans', 'americanes',
    'nord-americà', 'nord-americana', 'nord-americans', 'nord-americanes',
    'sud-americà', 'sud-americana', 'sud-americans', 'sud-americanes',
    'centreamericà', 'centreamericana', 'centreamericans', 'centreamericanes',
    'llatinoamericà', 'llatinoamericana', 'llatinoamericans', 'llatinoamericanes',
    'escandinau', 'escandinava', 'escandinaus', 'escandinaves',
    'nòrdic', 'nòrdica', 'nòrdics', 'nòrdiques',
    'balcànic', 'balcànica', 'balcànics', 'balcàniques',
    'bàltic', 'bàltica', 'bàltics', 'bàltiques',
    'caucàsic', 'caucàsica', 'caucàsics', 'caucàsiques',
    'caribeny', 'caribenya', 'caribenys', 'caribenyes',
    'eslau', 'eslava', 'eslaus', 'eslaves',
    'ibèric', 'ibèrica', 'ibèrics', 'ibèriques',
]

# Nationalities of the powers / neighbours / historical states that most
# often show up as adjectives inside *other* countries' articles.
_NATIONS_CA = [
    'britànic', 'britànica', 'britànics', 'britàniques',
    'anglès', 'anglesa', 'anglesos', 'angleses',
    'escocès', 'escocesa', 'escocesos', 'escoceses',
    'gal·lès', 'gal·lesa', 'gal·lesos', 'gal·leses',
    'irlandès', 'irlandesa', 'irlandesos', 'irlandeses',
    'francès', 'francesa', 'francesos', 'franceses',
    'espanyol', 'espanyola', 'espanyols', 'espanyoles',
    'portuguès', 'portuguesa', 'portuguesos', 'portugueses',
    'alemany', 'alemanya', 'alemanys', 'alemanyes',
    'italià', 'italiana', 'italians', 'italianes',
    'neerlandès', 'neerlandesa', 'neerlandesos', 'neerlandeses',
    'holandès', 'holandesa', 'holandesos', 'holandeses',
    'belga', 'belgues',
    'suís', 'suïssa', 'suïssos', 'suïsses',
    'austríac', 'austríaca', 'austríacs', 'austríaques',
    'rus', 'russa', 'russos', 'russes',
    'soviètic', 'soviètica', 'soviètics', 'soviètiques',
    'polonès', 'polonesa', 'polonesos', 'poloneses',
    'txec', 'txeca', 'txecs', 'txeques',
    'hongarès', 'hongaresa', 'hongaresos', 'hongareses',
    'romanès', 'romanesa', 'romanesos', 'romaneses',
    'grec', 'grega', 'grecs', 'gregues',
    'romà', 'romana', 'romans', 'romanes',
    'bizantí', 'bizantina', 'bizantins', 'bizantines',
    'otomà', 'otomana', 'otomans', 'otomanes',
    'turc', 'turca', 'turcs', 'turques',
    'persa', 'perses',
    'àrab', 'àrabs',
    'xinès', 'xinesa', 'xinesos', 'xineses',
    'japonès', 'japonesa', 'japonesos', 'japoneses',
    'mongol', 'mongola', 'mongols', 'mongoles',
    'danès', 'danesa', 'danesos', 'daneses',
    'noruec', 'noruega', 'noruecs', 'noruegues',
    'suec', 'sueca', 'suecs', 'sueques',
    'finlandès', 'finlandesa', 'finlandesos', 'finlandeses',
    'islandès', 'islandesa', 'islandesos', 'islandeses',
    'egipci', 'egípcia', 'egipcis', 'egípcies',
    'faraònic', 'faraònica', 'faraònics', 'faraòniques',
]

_REGIONS_ES = [
    'europeo', 'europea', 'europeos', 'europeas',
    'africano', 'africana', 'africanos', 'africanas',
    'norteafricano', 'norteafricana', 'norteafricanos', 'norteafricanas',
    'subsahariano', 'subsahariana', 'subsaharianos', 'subsaharianas',
    'asiático', 'asiática', 'asiáticos', 'asiáticas',
    'americano', 'americana', 'americanos', 'americanas',
    'norteamericano', 'norteamericana', 'norteamericanos', 'norteamericanas',
    'sudamericano', 'sudamericana', 'sudamericanos', 'sudamericanas',
    'suramericano', 'suramericana', 'suramericanos', 'suramericanas',
    'centroamericano', 'centroamericana', 'centroamericanos', 'centroamericanas',
    'latinoamericano', 'latinoamericana', 'latinoamericanos', 'latinoamericanas',
    'escandinavo', 'escandinava', 'escandinavos', 'escandinavas',
    'nórdico', 'nórdica', 'nórdicos', 'nórdicas',
    'balcánico', 'balcánica', 'balcánicos', 'balcánicas',
    'báltico', 'báltica', 'bálticos', 'bálticas',
    'caucásico', 'caucásica', 'caucásicos', 'caucásicas',
    'caribeño', 'caribeña', 'caribeños', 'caribeñas',
    'eslavo', 'eslava', 'eslavos', 'eslavas',
    'ibérico', 'ibérica', 'ibéricos', 'ibéricas',
]

_NATIONS_ES = [
    'británico', 'británica', 'británicos', 'británicas',
    'inglés', 'inglesa', 'ingleses', 'inglesas',
    'escocés', 'escocesa', 'escoceses', 'escocesas',
    'galés', 'galesa', 'galeses', 'galesas',
    'irlandés', 'irlandesa', 'irlandeses', 'irlandesas',
    'francés', 'francesa', 'franceses', 'francesas',
    'español', 'española', 'españoles', 'españolas',
    'portugués', 'portuguesa', 'portugueses', 'portuguesas',
    'alemán', 'alemana', 'alemanes', 'alemanas',
    'italiano', 'italiana', 'italianos', 'italianas',
    'neerlandés', 'neerlandesa', 'neerlandeses', 'neerlandesas',
    'holandés', 'holandesa', 'holandeses', 'holandesas',
    'belga', 'belgas',
    'suizo', 'suiza', 'suizos', 'suizas',
    'austriaco', 'austriaca', 'austriacos', 'austriacas',
    'austríaco', 'austríaca', 'austríacos', 'austríacas',
    'ruso', 'rusa', 'rusos', 'rusas',
    'soviético', 'soviética', 'soviéticos', 'soviéticas',
    'polaco', 'polaca', 'polacos', 'polacas',
    'checo', 'checa', 'checos', 'checas',
    'húngaro', 'húngara', 'húngaros', 'húngaras',
    'rumano', 'rumana', 'rumanos', 'rumanas',
    'griego', 'griega', 'griegos', 'griegas',
    'romano', 'romana', 'romanos', 'romanas',
    'bizantino', 'bizantina', 'bizantinos', 'bizantinas',
    'otomano', 'otomana', 'otomanos', 'otomanas',
    'turco', 'turca', 'turcos', 'turcas',
    'persa', 'persas',
    'árabe', 'árabes',
    'chino', 'china', 'chinos', 'chinas',
    'japonés', 'japonesa', 'japoneses', 'japonesas',
    'mongol', 'mongola', 'mongoles', 'mongolas',
    'danés', 'danesa', 'daneses', 'danesas',
    'noruego', 'noruega', 'noruegos', 'noruegas',
    'sueco', 'sueca', 'suecos', 'suecas',
    'finlandés', 'finlandesa', 'finlandeses', 'finlandesas',
    'islandés', 'islandesa', 'islandeses', 'islandesas',
    'egipcio', 'egipcia', 'egipcios', 'egipcias',
    'faraónico', 'faraónica', 'faraónicos', 'faraónicas',
]

GEO_ADJECTIVES = {
    'ca': _REGIONS_CA + _NATIONS_CA,
    'es': _REGIONS_ES + _NATIONS_ES,
    'en': [],  # English demonyms are capitalized -> handled by the proper-noun pass
}
