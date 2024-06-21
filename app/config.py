import redis

appConf = {
    "OAUTH2_CLIENT_ID": "559238676752-o7b2ernstpjk9gml4sn0thki1bvc3rjs.apps.googleusercontent.com",
    "OAUTH2_CLIENT_SECRET": "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",
    "OAUTH2_META_URL": "https://accounts.google.com/.well-known/openid-configuration",
    "FLASK_SECRET": "bd40525b-319d-4f34-a046-705ad18d5009",
    "FLASK_PORT": 5000,
    "PREFERRED_URL_SCHEME" : 'https',
    "MAIL_SERVER" : 'smtp.sendgrid.net',
    "MAIL_PORT" : 587,
    "MAIL_USE_TLS" : True,
    "MAIL_USERNAME" : 'apikey',
    "MAIL_PASSWORD" : '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',
    "MAIL_DEFAULT_SENDER" : 'no-reply@trusttyreporter.com',
    "SESSION_TYPE" : 'redis',
    "SESSION_REDIS" : redis.from_url('redis://red-cp6u63i0si5c73akiku0:6379')
    #"SESSION_REDIS" : redis.from_url('redis://localhost:6379')
    #"SESSION_REDIS" : redis.from_url('rediss://red-cp6u63i0si5c73akiku0:xpdVwG97463HyBDa4Y8t09srpw0BNQ1M@oregon-redis.render.com:6379')
}

SQLALCHEMY_DATABASE_URI = "postgresql://postgres.qswtiyzhtnalwqxmpbgz:6EryE4*(5yQc%s#@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
SECRET_KEY = appConf.get("FLASK_SECRET")
SESSION_TYPE = appConf.get("SESSION_TYPE")
SESSION_REDIS = appConf.get("SESSION_REDIS")
SQLALCHEMY_POOL_SIZE = 5