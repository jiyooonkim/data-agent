META_ADS_DAILY_COLUMNS = [
    "date date NOT NULL",
    "channel text NOT NULL",
    "product text NOT NULL",
    "campaign text NOT NULL",
    "spend numeric(18, 2) NOT NULL DEFAULT 0",
    "revenue numeric(18, 2) NOT NULL DEFAULT 0",
    "roas numeric(18, 2) NOT NULL DEFAULT 0",
]

META_ADS_DAILY_PRIMARY_KEY = ["date", "channel", "product", "campaign"]

META_ADS_DAILY_INSERT_COLUMNS = [
    "date",
    "channel",
    "product",
    "campaign",
    "spend",
    "revenue",
    "roas",
]
