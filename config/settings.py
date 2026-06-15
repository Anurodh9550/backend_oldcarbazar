"""
Django settings for Old Car Bazar backend.
"""
import os
from datetime import timedelta
from pathlib import Path

import cloudinary
import dj_database_url
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    JWT_ACCESS_LIFETIME_MIN=(int, 60),
    JWT_REFRESH_LIFETIME_DAYS=(int, 30),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="unsafe-dev-secret")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Render injects RENDER_EXTERNAL_HOSTNAME at runtime; auto-trust it.
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS = list(ALLOWED_HOSTS) + [RENDER_EXTERNAL_HOSTNAME]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local apps
    "apps.users",
    "apps.cities",
    "apps.listings",
    "apps.inquiries",
    "apps.adminpanel",
    "apps.subscriptions",
    "apps.core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ----------------------------- Database ----------------------------- #
DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --------------------------- Authentication ------------------------- #
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ----------------------------- I18N -------------------------------- #
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --------------------------- Static / Media ------------------------ #
STATIC_URL = env("STATIC_URL", default="/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------- Cloudinary ---------------------------- #
# Reads credentials from environment (.env). Used by `cloudinary.uploader`
# in views/serializers to upload listing photos, profile avatars, etc.
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----------------------------- DRF --------------------------------- #
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.adminpanel.authentication.OcbJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS":
        "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "120/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ----------------------------- JWT --------------------------------- #
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":
        timedelta(minutes=env("JWT_ACCESS_LIFETIME_MIN")),
    "REFRESH_TOKEN_LIFETIME":
        timedelta(days=env("JWT_REFRESH_LIFETIME_DAYS")),
    # Keep the same refresh token until it expires. Rotation + blacklist caused
    # sellers to get 401 on DELETE/Mark-as-Sold when two tabs refreshed or an
    # old refresh token was still in localStorage after redeploy.
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER":
        "apps.users.serializers.OcbTokenObtainPairSerializer",
}

# ----------------------------- CORS -------------------------------- #
PRODUCTION_FRONTEND_ORIGINS = [
    "https://oldcarbazar.com",
    "https://www.oldcarbazar.com",
]

CORS_ALLOWED_ORIGINS = list(dict.fromkeys([
    *env("CORS_ALLOWED_ORIGINS"),
    *PRODUCTION_FRONTEND_ORIGINS,
]))
CORS_ALLOW_CREDENTIALS = True

# Allow every Vercel deployment URL for this project (production + previews
# + git-branch URLs like https://oldcarbazar-git-main-<user>.vercel.app).
# Without this, the browser blocks the request and the frontend reports
# "Failed to fetch" even though the backend itself is reachable.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://([a-z0-9-]+\.)*vercel\.app$",
    r"^http://localhost(:\d+)?$",
    r"^http://127\.0\.0\.1(:\d+)?$",
]

# Cross-site POSTs from the frontend (login, listings, uploads) need this.
CSRF_TRUSTED_ORIGINS = [
    origin for origin in CORS_ALLOWED_ORIGINS if origin.startswith(("http://", "https://"))
]
# Trust all Vercel-hosted frontends for CSRF as well (matches CORS regex above).
CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# --------------------------- API schema ---------------------------- #
SPECTACULAR_SETTINGS = {
    "TITLE": "Old Car Bazar API",
    "DESCRIPTION": "REST API for the Old Car Bazar marketplace.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --------------------------- App settings -------------------------- #
OTP_PROVIDER = env("OTP_PROVIDER", default="console")
OTP_EXPIRY_SECONDS = 5 * 60

# Subscriptions: until the real payment gateway (Razorpay) is wired,
# /subscriptions/activate/ is gated by this flag so that production
# does not accidentally hand out paid plans for free. Setting it to
# True is safe in DEBUG / staging — that's where sellers test the
# upgrade flow.
SUBSCRIPTION_ALLOW_DEMO_ACTIVATION = env.bool(
    "SUBSCRIPTION_ALLOW_DEMO_ACTIVATION",
    default=DEBUG,
)

# Razorpay payment gateway. KEY_ID is safe to return to the frontend during
# checkout; KEY_SECRET and WEBHOOK_SECRET must stay server-side only.
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")

# GST / tax invoice. 18% is added on top of every paid plan/boost price and
# the seller GSTIN is printed on each tax invoice. Override via env if the
# business registration changes; defaults match the registered business.
GST_RATE_PERCENT = env.int("GST_RATE_PERCENT", default=18)
GST_SELLER_GSTIN = env("GST_SELLER_GSTIN", default="09BUUPK1450R1ZQ")
GST_SELLER_NAME = env("GST_SELLER_NAME", default="Old Car Bazar")

# Security tightening for production
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
# backend test