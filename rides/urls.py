from rest_framework.routers import DefaultRouter

from .views import RideEventViewSet, RideViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("rides", RideViewSet, basename="ride")
router.register("ride-events", RideEventViewSet)

urlpatterns = router.urls

