from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': "SimpleCache", 'CACHE_DEFAULT_TIMEOUT': 300})


def init_cache(app):
    cache.init_app(app)