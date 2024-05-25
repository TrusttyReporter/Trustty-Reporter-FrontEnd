appConf = {
    "OAUTH2_CLIENT_ID": "559238676752-o7b2ernstpjk9gml4sn0thki1bvc3rjs.apps.googleusercontent.com",
    "OAUTH2_CLIENT_SECRET": "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",
    "OAUTH2_META_URL": "https://accounts.google.com/.well-known/openid-configuration",
    "FLASK_SECRET": "bd40525b-319d-4f34-a046-705ad18d5009",
    "FLASK_PORT": 5000,
    "SESSION_TYPE": 'redis',
    "SESSION_REDIS": 'redis://red-cp6u63i0si5c73akiku0:6379'
    #"SESSION_REDIS": 'redis://localhost:6379'
}

SQLALCHEMY_DATABASE_URI = "postgresql://postgres.qswtiyzhtnalwqxmpbgz:6EryE4*(5yQc%s#@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
SECRET_KEY = appConf.get("FLASK_SECRET")
SESSION_TYPE = appConf.get("SESSION_TYPE")
SESSION_REDIS = appConf.get("SESSION_REDIS")