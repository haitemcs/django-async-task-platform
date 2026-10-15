# include: Allows nesting other URL configuration files (like app-level urls.py into root urls.py).
# path: Defines a specific URL route string and maps it to a view or router.
from django.urls import include, path

# DefaultRouter: Automatically generates standard RESTful CRUD URL endpoints 
# (List, Create, Retrieve, Update, Destroy) for Django REST Framework ViewSets.
from rest_framework.routers import DefaultRouter

# SimpleJWT views: Built-in authentication views provided by djangorestframework-simplejwt 
# to handle issuing and refreshing JWT tokens.
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Import our custom ViewSets from the current app's views.py file.
from .views import RegisterViewSet, TaskViewSet


# 2. ROUTER CONFIGURATION
# Instantiate DRF's DefaultRouter. Instead of writing 10 manual path() rules for tasks and registration, 
# the router automatically inspects our ViewSets and builds the URLs for us.
router = DefaultRouter()

# Register "tasks" endpoint. Maps to TaskViewSet. 
# basename="task" gives Django a prefix for URL names (e.g., task-list, task-detail) used in reverse-lookup.
router.register("tasks", TaskViewSet, basename="task")

# Register "register" endpoint. Maps to RegisterViewSet for public user sign-ups.
router.register("register", RegisterViewSet, basename="register")


# 3. URL PATTERNS (The Final Route Dispatcher)
urlpatterns = [
    # path("", include(router.urls)): 
    # Takes all the automatically generated CRUD routes created by our DefaultRouter 
    # and mounts them at the root of this app's URL space. 
    # For example, this produces:
    # - GET/POST /tasks/
    # - GET/PUT/DELETE /tasks/<id>/
    # - POST /register/
    path("", include(router.urls)),

    # path("auth/token/"): 
    # Sets up the login/token-generation endpoint. When a user sends a POST request 
    # with their username and password here, TokenObtainPairView validates them 
    # and returns a JSON response containing an Access Token and a Refresh Token.
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),

    # path("auth/token/refresh/"): 
    # Sets up the token-refresh endpoint. Access tokens expire quickly for security. 
    # When an access token expires, the client sends their long-lived refresh token here 
    # to receive a brand-new access token without forcing the user to log in again.
    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
]