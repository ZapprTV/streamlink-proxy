import time
import base64
import validators
import re
from starlette.applications import Starlette
from starlette.responses import RedirectResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route
from streamlink import Streamlink
from streamlink.exceptions import PluginError, NoStreamsError
from requests.exceptions import HTTPError
from urllib.parse import parse_qs

lowerCacheExpiryPlugins = ["raiplay"]
cache = {}

def IsBase64(string):
    try:
        return base64.b64encode(base64.b64decode(string)).decode("utf-8") == string
    except Exception:
        return False

def GetCachedURL(key):
    entry = cache.get(key)
    if entry:
        ttl, expires_at, url = entry
        if expires_at > time.time():
            return ttl, url
        else:
            del cache[key]
    return None

def SetCachedURL(ttl, key, url):
    cache[key] = (ttl, time.time() + ttl, url)

async def DefaultRequest(request):
    return RedirectResponse("https://zapprtv.github.io/streamlink-proxy", status_code=301, headers={"Access-Control-Allow-Origin": "*"})

async def BlankRequest(request):
    return PlainTextResponse("", status_code=200, headers={"Access-Control-Allow-Origin": "*"})

async def StreamRequest(request):
    CACHE_TTL = 900
    headers = {"Access-Control-Allow-Origin": "*"}
    key = str(request.path_params)

    if GetCachedURL(key):
        ttl, cachedURL = GetCachedURL(key)
        headers["Cache-Control"] = f"public, max-age={ttl}, s-maxage={ttl}"
        return RedirectResponse(cachedURL, status_code=307, headers=headers)
    
    requestedURL = request.path_params.get("url")
    if not requestedURL:
        return PlainTextResponse("URL parameter required", status_code=400, headers=headers)
    requestedURL = re.sub(r'^(https?):/(?!/)', r'\1://', requestedURL)
    if not validators.url(requestedURL):
        return PlainTextResponse("Invalid URL", status_code=400, headers=headers)

    if request.path_params.get("options") and request.path_params.get("options") != "default":
        optionsString = request.path_params.get("options")
        if IsBase64(optionsString):
            optionsString = base64.b64decode(optionsString).decode("utf-8")
        options = parse_qs(optionsString)
    else:
        options = {}

    session = Streamlink()
    for key, value in options.items():
        session.set_option(key, value[0])

    try:
        pluginName = session.resolve_url(requestedURL)[0]
        if pluginName in lowerCacheExpiryPlugins:
            CACHE_TTL = 120
        headers["Cache-Control"] = f"public, max-age={CACHE_TTL}, s-maxage={CACHE_TTL}"

        plugin = session.resolve_url(requestedURL)[1]
        streamsList = plugin(session, requestedURL, options)._get_streams()
        if not streamsList:
            raise NoStreamsError("No streams found")
        streams = dict(streamsList)
        url = streams[list(streams)[-1]].to_manifest_url()
        SetCachedURL(CACHE_TTL, key, url)
    except Exception as error:
        if type(error) == PluginError and error and vars(error).get("err") and type(error.err) == HTTPError and error.err.request.url != requestedURL:
            url = error.err.request.url
        else:
            return PlainTextResponse(f"{type(error).__name__}{f' - {str(error)}' if str(error) else ''}", status_code=500, headers=headers)

    return RedirectResponse(url, status_code=307, headers=headers)

app = Starlette(routes=[
    Route("/.well-known/appspecific/com.chrome.devtools.json", BlankRequest),
    Route("/favicon.ico", BlankRequest),
    Route("/", DefaultRequest),
    Route("/{options}/{url:path}", StreamRequest),
])