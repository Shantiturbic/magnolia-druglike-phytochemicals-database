"""Central configuration for BBB Database STC.

Single source of truth for all taxonomic parameters, inclusion/exclusion
thresholds, source registry, evidence tiers, known compounds, and paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT / "data"
RAW_DIR = DATA_ROOT / "raw"
CACHE_DIR = RAW_DIR / ".cache"
OUTPUT_DIR = DATA_ROOT

# ---------------------------------------------------------------------------
# Taxonomic scope
# ---------------------------------------------------------------------------
TAXONOMY_AUTHORITY = "POWO"
TAXONOMY_TREATMENT = "sensu_lato"
GENUS_WIKIDATA_QID = "Q157017"
NCBI_TAXONOMY_ID = "3408"

DR_ENDEMIC_SPECIES = [
    "Magnolia pallescens",
    "Magnolia domingensis",
    "Magnolia hamorii",
]

HISPANIOLA_ENDEMIC_SPECIES = DR_ENDEMIC_SPECIES + [
    "Magnolia ekmanii",
    "Magnolia emarginata",
]

MAJOR_STUDIED_SPECIES = [
    "Magnolia officinalis",
    "Magnolia grandiflora",
    "Magnolia obovata",
    "Magnolia virginiana",
    "Magnolia sieboldii",
    "Magnolia liliiflora",
    "Magnolia biondii",
    "Magnolia kobus",
    "Magnolia denudata",
    "Magnolia champaca",
    "Magnolia acuminata",
    "Magnolia stellata",
    "Magnolia tripetala",
    "Magnolia sprengeri",
    "Magnolia figo",
]

# Wikidata QIDs for SPARQL queries (P703: found in taxon)
# Wikidata QIDs verified against live SPARQL on 2026-05-21.
# All Magnolia taxa with P703-linked compounds on Wikidata.
# Verified via SPARQL on 2026-05-21. 50 taxa (49 species + genus).
# POWO lists 372 accepted species; only these 50 have compound data.
MAGNOLIA_SPECIES_QIDS = {
    "Q157017": "Magnolia (genus)",
    "Q1042288": "Magnolia officinalis",
    "Q161116": "Magnolia grandiflora",
    "Q2386378": "Magnolia obovata",
    "Q1859063": "Magnolia virginiana",
    "Q1378390": "Magnolia sieboldii",
    "Q942031": "Magnolia liliiflora",
    "Q6731965": "Magnolia biondii",
    "Q942409": "Magnolia kobus",
    "Q794061": "Magnolia denudata",
    "Q839507": "Magnolia stellata",
    "Q1249099": "Magnolia acuminata",
    "Q167027": "Magnolia champaca",
    "Q546069": "Magnolia salicifolia",
    "Q3926627": "Magnolia sprengeri",
    "Q3927444": "Magnolia kachirachirai",
    "Q11291825": "Magnolia compressa",
    "Q15493525": "Magnolia ovata",
    "Q4274131": "Magnolia coco",
    "Q731443": "Magnolia x soulangeana",
    "Q15236258": "Magnolia praecocissima",
    "Q5487185": "Magnolia sinica",
    "Q15493493": "Magnolia odora",
    "Q15477939": "Magnolia balansae",
    "Q819208": "Magnolia fraseri",
    "Q12478483": "Magnolia liliifera",
    "Q1040030": "Magnolia henryi",
    "Q15477943": "Magnolia arcabucoana",
    "Q15477936": "Magnolia baillonii",
    "Q2672193": "Magnolia campbellii",
    "Q15488595": "Magnolia cathcartii",
    "Q15488795": "Magnolia chevalieri",
    "Q15489099": "Magnolia crassipes",
    "Q15489490": "Magnolia dodecapetala",
    "Q15600668": "Magnolia elegans",
    "Q28813342": "Magnolia fraseri var. pyramidata",
    "Q15491510": "Magnolia garrettii",
    "Q15491802": "Magnolia gloriensis",
    "Q15492711": "Magnolia lacei",
    "Q15492827": "Magnolia lanuginosa",
    "Q15493323": "Magnolia mexicana",
    "Q6731986": "Magnolia montana",
    "Q87580116": "Magnolia mutabilis",
    "Q15603337": "Magnolia nilagirica",
    "Q15476418": "Magnolia pterocarpa",
    "Q15494116": "Magnolia rajaniana",
    "Q96066603": "Magnolia tomentosa",
    "Q15494555": "Magnolia tsiampacca",
    "Q104864670": "Magnolia wieseneri",
    "Q15494305": "Magnolia yunnanensis",
}

TCM_HERB_NAMES: dict[str, list[str]] = {
    "Magnolia officinalis": ["Houpo", "Hou Po", "厚朴", "Magnoliae Officinalis Cortex"],
    "Magnolia biondii": ["Xinyi", "Xin Yi", "辛夷", "Magnoliae Flos"],
    "Magnolia denudata": ["Yulan", "玉兰"],
    "Magnolia liliiflora": ["Ziyu", "紫玉兰"],
}

SYNONYM_MAP: dict[str, str] = {
    # Magnolia-to-Magnolia synonyms
    "Magnolia hypoleuca": "Magnolia obovata",
    "Magnolia heptapeta": "Magnolia denudata",
    "Magnolia quinquepeta": "Magnolia liliiflora",
    # Michelia → Magnolia (APG IV merger)
    "Michelia champaca": "Magnolia champaca",
    "Michelia alba": "Magnolia x alba",
    "Michelia figo": "Magnolia figo",
    "Michelia compressa": "Magnolia compressa",
    "Michelia baillonii": "Magnolia baillonii",
    "Michelia rajaniana": "Magnolia rajaniana",
    "Michelia balansae": "Magnolia balansae",
    "Michelia cathcartii": "Magnolia cathcartii",
    "Michelia doltsopa": "Magnolia doltsopa",
    "Michelia lanuginosa": "Magnolia lanuginosa",
    "Michelia nilagirica": "Magnolia nilagirica",
    "Michelia montana": "Magnolia montana",
    "Michelia velutina": "Magnolia velutina",
    "Michelia kisopa": "Magnolia kisopa",
    # Talauma → Magnolia
    "Talauma domingensis": "Magnolia domingensis",
    "Talauma pallescens": "Magnolia pallescens",
    "Talauma hamorii": "Magnolia hamorii",
    "Talauma ovata": "Magnolia ovata",
    "Talauma hodgsonii": "Magnolia hodgsonii",
    "Talauma gitigensis": "Magnolia gitigensis",
    # Manglietia → Magnolia
    "Manglietia fordiana": "Magnolia fordiana",
    "Manglietia chevalieri": "Magnolia chevalieri",
    "Manglietia phuthoensis": "Magnolia phuthoensis",
    "Manglietia garrettii": "Magnolia garrettii",
    # Liriopsis, Yulania, others → Magnolia
    "Liriopsis biondii": "Magnolia biondii",
    "Yulania denudata": "Magnolia denudata",
    "Yulania liliiflora": "Magnolia liliiflora",
    "Aromadendron elegans": "Magnolia elegans",
    "Kmeria duperreana": "Magnolia duperreana",
    "Pachylarnax praecalva": "Magnolia praecalva",
    "Paramichelia baillonii": "Magnolia baillonii",
    "Elmerrillia tsiampacca": "Magnolia tsiampacca",
    "Tsoongiodendron odorum": "Magnolia odora",
}

# Old genera merged into Magnolia under APG IV.
# Used as additional search terms in collectors to capture compounds
# still indexed under pre-merger names in external databases.
OLD_GENUS_NAMES: list[str] = [
    "Michelia",
    "Talauma",
    "Manglietia",
    "Liriopsis",
    "Yulania",
    "Aromadendron",
    "Kmeria",
    "Pachylarnax",
    "Paramichelia",
    "Elmerrillia",
    "Tsoongiodendron",
]

# Wikidata QIDs for old genera — for LOTUS SPARQL queries.
# P703 compounds may be annotated under these taxa in Wikidata.
OLD_GENUS_WIKIDATA_QIDS: dict[str, str] = {
    "Q133549": "Michelia",
    "Q2397205": "Talauma",
    "Q1410816": "Manglietia",
    "Q15517866": "Yulania",
    "Q2073599": "Aromadendron",
    "Q6397960": "Kmeria",
    "Q7136483": "Pachylarnax",
    "Q7184875": "Paramichelia",
    "Q5364189": "Elmerrillia",
}

# ---------------------------------------------------------------------------
# Inclusion / exclusion thresholds
# ---------------------------------------------------------------------------
MW_MIN = 100.0
MW_MAX = 1500.0
HEAVY_ATOM_MIN = 5
EXCLUDE_INORGANIC = True
EXCLUDE_PRIMARY_METABOLITES = True

PRIMARY_METABOLITE_INCHIKEYS: frozenset[str] = frozenset([
    "WQZGKKKJIJFFOK",  # glucose
    "GUBGYTABKSRVRQ",  # galactose
    "HMFHBZSHGGEWLO",  # fructose
    "CZMRCDWAGMRECN",  # sucrose
    "AYFVYJQAPQTCCC",  # threonine
    "DCXYFEDJOCDNAF",  # asparagine
    "CKLJMWTZIZZHCS",  # aspartic acid
    "WHUUTDBJXJRKMK",  # glutamic acid
    "ZDXPYRJPNDTMRX",  # glutamine
    "QIVBCDIJIAJPQS",  # alanine
    "COLNVLDHVKWLRT",  # phenylalanine
    "OUYCCCASQSFEME",  # tyrosine
    "QWCKQJZIFLGMSD",  # tryptophan
    "AGPKZVBTJJNPAG",  # isoleucine
    "ROHFNLRQFUQHCH",  # leucine
    "KZSNJWFQEVHDMF",  # valine
    "MTCFGRXMJLQNBG",  # serine
    "AYFVYJQAPQTCCC",  # threonine
    "XUJNEKJLAYXESH",  # cysteine
    "FFEARJCKVFRZRR",  # methionine
    "KDXKERNSBIXSRK",  # lysine
    "ODKSFYDXXFIFQN",  # arginine
    "HNDVDQJCIGZPNO",  # histidine
    "ONIBWKKTOPOVIA",  # proline
    "DHMQDGOQFOQNFH",  # glycine
    "GFFGJBXGBJISGV",  # adenine
    "UYTPUPDQBNUYGX",  # guanine
    "OPTASPLRGRRNAP",  # cytosine
    "RWQNBRDOKXIBIV",  # thymine
    "ISAKRJDGNUQOIC",  # uracil
    "BAWFJGJZGIEFAR",  # citric acid
    "BJEPYKJPYRNKOW",  # malic acid
    "FEWJPZIEWOKRBE",  # succinic acid
    "KRKNYBCHXYNGOX",  # fumaric acid
    "JVTAAEKCZFNVCJ",  # lactic acid
    "QAOWNCQODCNURD",  # pyruvic acid
    "VZCYOOQTPOCHFL",  # palmitic acid
    "QIQXTHQIDYTFRH",  # stearic acid
    "ZQPPMHVWECSIRJ",  # oleic acid
    "OYHQOLUKZRVURQ",  # linoleic acid
    "DTOSIQBPPRVQHS",  # linolenic acid
])

# ---------------------------------------------------------------------------
# Evidence tiers
# ---------------------------------------------------------------------------
class EvidenceTier(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    PROVISIONAL = "provisional"

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SourceConfig:
    name: str
    tier: int
    license: str
    url: str
    unique_contribution: str
    enabled: bool
    fallback: str

SOURCE_REGISTRY: dict[str, SourceConfig] = {
    "lotus_wikidata": SourceConfig(
        name="lotus_wikidata",
        tier=1,
        license="CC0",
        url="https://query.wikidata.org/sparql",
        unique_contribution="Taxonomy-curated compound-species pairs with Wikidata provenance",
        enabled=True,
        fallback="Skip — primary taxonomy source, no alternative",
    ),
    "coconut": SourceConfig(
        name="coconut",
        tier=1,
        license="CC-BY 4.0",
        url="https://coconut.naturalproducts.net",
        unique_contribution="NP Classifier annotations + independent structural confirmation",
        enabled=True,
        fallback="Use cached CSV if download fails",
    ),
    "knapsack": SourceConfig(
        name="knapsack",
        tier=1,
        license="CC-BY 4.0",
        url="http://www.knapsackfamily.com/knapsack_core/top.php",
        unique_contribution="Species-level NP attribution with metabolite IDs",
        enabled=True,
        fallback="Skip — covered by LOTUS for most species",
    ),
    "pubchem_taxonomy": SourceConfig(
        name="pubchem_taxonomy",
        tier=2,
        license="Public domain",
        url="https://pubchem.ncbi.nlm.nih.gov",
        unique_contribution="NCBI taxonomy-linked compound discovery (all PubChem knows about genus Magnolia)",
        enabled=True,
        fallback="Skip — other sources cover core compounds",
    ),
    "chembl_magnolia": SourceConfig(
        name="chembl_magnolia",
        tier=2,
        license="CC-BY-SA 3.0",
        url="https://www.ebi.ac.uk/chembl/",
        unique_contribution="Bioactivity data (IC50, Ki) for Magnolia compounds",
        enabled=True,
        fallback="Skip — bioactivity is enrichment, not discovery",
    ),
    "npatlas": SourceConfig(
        name="npatlas",
        tier=1,
        license="CC-BY-NC 4.0",
        url="https://www.npatlas.org",
        unique_contribution="Curated microbial NP atlas — endophyte-derived compounds from Magnolia hosts",
        enabled=True,
        fallback="API still broken 2026-05-28. Using bulk TSV download (36K compounds) + local filter.",
    ),
    "npass": SourceConfig(
        name="npass",
        tier=1,
        license="Academic use",
        url="https://bidd.group/NPASS/",
        unique_contribution="Species-activity-target triples for NPs (32 Magnolia spp, 1000+ compounds)",
        enabled=True,
        fallback="Site restored 2026-05-28. NPASS 3.0 (2026 release). Bulk TSV download.",
    ),
    "dr_duke": SourceConfig(
        name="dr_duke",
        tier=3,
        license="Public domain (USDA)",
        url="https://phytochem.nal.usda.gov/",
        unique_contribution="Ethnobotanical data: plant parts, traditional uses, concentrations",
        enabled=True,
        fallback="Bulk ZIP behind WAF 2026-05-28. Multi-strategy: bulk ZIP → Drupal API → web scrape.",
    ),
    "literature_miner": SourceConfig(
        name="literature_miner",
        tier=4,
        license="Fair use (abstracts) + CC (PMC)",
        url="https://pubmed.ncbi.nlm.nih.gov",
        unique_contribution="Novel compounds from recent literature not yet in databases",
        enabled=True,
        fallback="Skip — databases cover established compounds",
    ),
    "tcmsp": SourceConfig(
        name="tcmsp",
        tier=2,
        license="Academic use",
        url="https://old.tcmsp-e.com/",
        unique_contribution="TCM pharmacokinetic parameters (OB, DL, BBB)",
        enabled=False,
        fallback="Site down as of 2026-05-21. ADMET predicted independently.",
    ),
    "cmaup": SourceConfig(
        name="cmaup",
        tier=2,
        license="CC-BY 4.0",
        url="http://bidd.group/CMAUP/",
        unique_contribution="Medicinal plant activity-compound pairs",
        enabled=False,
        fallback="404 as of 2026-05-21. Covered by NPASS + ChEMBL.",
    ),
    "foodb": SourceConfig(
        name="foodb",
        tier=3,
        license="CC-BY-NC 4.0",
        url="https://foodb.ca",
        unique_contribution="Food chemistry context",
        enabled=False,
        fallback="Negligible Magnolia coverage. Compounds in COCONUT/LOTUS.",
    ),
    "imppat": SourceConfig(
        name="imppat",
        tier=3,
        license="Academic use",
        url="https://cb.imsc.res.in/imppat/",
        unique_contribution="Indian medicinal plant phytochemistry",
        enabled=False,
        fallback="Fragile site, negligible Magnolia coverage.",
    ),
}

# ---------------------------------------------------------------------------
# Known Magnolia compounds (single canonical list)
# Used for COCONUT name matching and NER dictionary seeding.
# NOT for PubChem search (that uses taxonomy discovery).
# ---------------------------------------------------------------------------
KNOWN_MAGNOLIA_COMPOUNDS: list[str] = [
    "magnolol", "honokiol", "obovatol", "4-o-methylhonokiol",
    "magnoflorine", "magnocurarine", "liriodenine", "anonaine",
    "roemerine", "magnoline", "boldine", "glaucine", "isocorydine",
    "costunolide", "parthenolide", "magnolin", "fargesin",
    "eudesmin", "kobusin", "sesamin", "syringaresinol", "pinoresinol",
    "magnaldehyde", "obovatal", "honokitriol", "randainol",
    "michelalbine", "salicifoline", "dicentrine", "nornuciferine",
    "tubocurarine", "magnosalin", "sinapaldehyde", "micheliolide",
]

# 13 must-have compounds for validation (signature Magnolia phytochemicals)
# InChIKey connectivity (first 14 chars) verified against RDKit 2025.03.3 output
MUST_HAVE_COMPOUNDS: dict[str, str] = {
    "magnolol": "YVMBMEXRHOXCPM",
    "honokiol": "YOVASQUIMPDASA",
    "obovatol": "RVIUPPNYFNZVFG",
    "4-o-methylhonokiol": "OQFHJKZVOALSPV",
    "costunolide": "ZNURDDCKOFUOKI",
    "parthenolide": "ZNURDDCKOFUOKI",
    "magnoflorine": "YLRXAIKMLINXQY",
    "liriodenine": "MUMCCPUVOAUBAN",
    "anonaine": "XVIHBNVDAPQBRH",
    "magnolin": "MFIHSKBTNZNJIK",
    "fargesin": "ITZKNWISERYZRG",
    "sesamin": "YIGQNWGFLQZODP",
    "syringaresinol": "XPBIHYWXQUQBSV",
}

# ---------------------------------------------------------------------------
# Rate limits and timeouts
# ---------------------------------------------------------------------------
HTTP_DELAY = 0.4
HTTP_MAX_RETRIES = 4
HTTP_TIMEOUT = 30
SPARQL_TIMEOUT = 120
SPARQL_INTER_QUERY_DELAY = 2.0

# COCONUT CSV download
COCONUT_CSV_URL = (
    "https://coconut.s3.uni-jena.de/prod/downloads/2026-05/"
    "coconut_csv_lite-05-2026.zip"
)
