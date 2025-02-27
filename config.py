# config.py
import os

# Cloudinary Configuration for LARP Script Covers
CLOUDINARY_COVER_CLOUD_NAME = os.getenv("CLOUDINARY_COVER_CLOUD_NAME")
CLOUDINARY_COVER_API_KEY = os.getenv("CLOUDINARY_COVER_API_KEY")
CLOUDINARY_COVER_API_SECRET = os.getenv("CLOUDINARY_COVER_API_SECRET")

# Cloudinary Configuration for LARP Script Image Content
CLOUDINARY_CONTENT_CLOUD_NAME = os.getenv("CLOUDINARY_CONTENT_CLOUD_NAME")
CLOUDINARY_CONTENT_API_KEY = os.getenv("CLOUDINARY_CONTENT_API_KEY")
CLOUDINARY_CONTENT_API_SECRET = os.getenv("CLOUDINARY_CONTENT_API_SECRET")

# API Endpoints
HOST = "https://api.h5.helloaba.cn/"
SCRIPT_SEARCH_PAGE = "script/v9/scriptSearchPage"
PLAT_FORM_SCRIPT_INFO = "script/v2/platformScriptInfo"

# Request Configuration
REQUEST_TIMEOUT = 60
TIMEOUT_RETRY_LIMIT = 8

# File Paths
SCRIPT_LIST_PATH = "data/script_data_simple.csv"
DETAILED_CSV_PATH = "data/script_data_detailed.csv"
TRANSLATED_CSV_PATH = "data/translated/script_data_detailed.csv"
SCRIPT_COVER_FOLDER = "data/downloaded/script_cover"
SCRIPT_IMAGE_CONTENT_FOLDER = "data/downloaded/script_image_content"
LOG_FOLDER = "log"
INCREMENTAL_OUTPUT_FOLDER_PATH = "data/incremental"

# Compression Threshold
COMPRESSION_THRESHOLD = 5 * 1024 * 1024  # 5 MB

# Other Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

TAG_MAPPING = {
    "日式": "isBackgroundJapanese",
    "歐美": "isBackgroundEuropean",
    "港澳": "isBackgroundHongKongMacau",
    "中式": "isBackgroundChinese",
    "虛構": "isBackgroundFictional",
    "架空": "isBackgroundPartiallyFictional",
    "古風": "isBackgroundAncient",
    "民國": "isBackgroundRepublicOfChina",
    "未來": "isBackgroundFuturistic",
    "現代": "isBackgroundModern",
    "国外": "isBackgroundForeign",
    "情感": "isScriptEmotional",
    "機制": "isScriptMechanism",
    "推理": "isScriptReasoning",
    "還原": "isScriptDiscovering",
    "陣營": "isScriptMultiSide",
    "歡樂": "isScriptFun",
    "恐怖": "isScriptHorror",
    "治癒": "isGamePlayHealing",
    "立意": "isGamePlayMeaningful",
    "演繹": "isGamePlayActing",
    "沉浸": "isGamePlayImmersive",
    "驚栗": "isGamePlayTerror",
    "懸疑": "isGamePlaySuspense",
    "演繹法": "isGamePlayDeductiveReasoning",
    "博奕": "isGamePlayGameTheory",
    "設定": "isGamePlaySetting",
    "刑偵": "isGamePlayCrimeInvestigation",
    "跑團": "isGamePlayTRPG",
    "神話": "isThemeMythology",
    "科幻": "isThemeSciFi",
    "武俠": "isThemeMartialArts",
    "戰爭": "isThemeWar",
    "校園": "isThemeSchool",
    "末日": "isThemeApocalypse",
    "家國": "isThemeNation",
    "動物": "isThemeAnimal",
    "都市": "isThemeUrban",
    "豪門": "isThemeEliteFamily",
    "宮廷": "isThemePalace",
    "怪談": "isThemeGhostStory",
    "仙俠": "isThemeImmortalHero",
    "玄幻": "isThemeFantasy",
    "穿越": "isThemeTimeTravel",
    "歷史": "isThemeHistory",
    "擬人": "isThemeAnthropomorphism",
    "克蘇魯": "isThemeCthulhu",
    "二次元": "isThemeAnime",
    "魔法": "isThemeMagic",
    "思辨": "isThemePhilosophical",
    "權謀": "isThemePoliticalIntrigue",
    "鄉土": "isThemeRural",
    "成長": "isThemeComingOfAge",
    "童話": "isThemeFairyTale",
}

# Difficulty mappings for LARPScript boolean fields
DIFFICULTY_MAPPING = {
    "新手": "isLevelJunior",
    "進階": "isLevelAdvanced",
    "高階": "isLevelSenior",
}

# Sold-by mappings for LARPScript boolean fields
SOLD_BY_MAPPING = {
    "1": "isSoldByBox",
    "2": "isSoldByCitySolo",
    "3": "isSoldByCityMulti",
}

DATABASE_URL = os.getenv("DATABASE_URL")