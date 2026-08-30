import math
from datetime import timedelta

from django.db.models import FloatField, Prefetch, Value
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from .models import Ride, RideEvent, User
from .serializers import RideEventSerializer, RideSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class RideEventViewSet(viewsets.ModelViewSet):
    queryset = RideEvent.objects.select_related("ride")
    serializer_class = RideEventSerializer


class RideViewSet(viewsets.ModelViewSet):
    serializer_class = RideSerializer

    def get_queryset(self):
        cutoff = timezone.now() - timedelta(hours=24)
        recent_events = RideEvent.objects.filter(created_at__gte=cutoff).order_by(
            "created_at", "id_ride_event"
        )

        queryset = Ride.objects.select_related("rider", "driver").prefetch_related(
            Prefetch("events", queryset=recent_events, to_attr="todays_ride_events_cache")
        )

        status = self.request.query_params.get("status")
        if status:
            valid_statuses = {choice for choice, _ in Ride.Status.choices}
            if status not in valid_statuses:
                raise ValidationError({"status": f"Choose one of: {', '.join(sorted(valid_statuses))}."})
            queryset = queryset.filter(status=status)

        rider_email = self.request.query_params.get("rider_email")
        if rider_email:
            queryset = queryset.filter(rider__email__iexact=rider_email.strip())

        ordering = self.request.query_params.get("ordering", "pickup_time")
        if ordering in {"pickup_time", "-pickup_time"}:
            direction = "-" if ordering.startswith("-") else ""
            return queryset.order_by(f"{direction}pickup_time", f"{direction}id_ride")

        if ordering not in {"distance", "-distance"}:
            raise ValidationError(
                {"ordering": "Use pickup_time, -pickup_time, distance, or -distance."}
            )

        latitude = self._coordinate("pickup_latitude", -90.0, 90.0)
        longitude = self._coordinate("pickup_longitude", -180.0, 180.0)

        cosine = (
            Sin(Radians("pickup_latitude")) * math.sin(math.radians(latitude))
            + Cos(Radians("pickup_latitude"))
            * math.cos(math.radians(latitude))
            * Cos(Radians("pickup_longitude") - Value(math.radians(longitude)))
        )
        distance = Value(6371, output_field=FloatField()) * ACos(
            Least(Greatest(cosine, Value(-1.0)), Value(1.0))
        )
        direction = "-" if ordering.startswith("-") else ""
        return queryset.annotate(distance_km=distance).order_by(
            f"{direction}distance_km", "id_ride"
        )

    def _coordinate(self, name, minimum, maximum):
        raw_value = self.request.query_params.get(name)
        if raw_value is None:
            raise ValidationError({name: "This parameter is required for distance ordering."})
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            raise ValidationError({name: "Enter a valid number."})
        if not minimum <= value <= maximum:
            raise ValidationError({name: f"Enter a value between {minimum} and {maximum}."})
        return value

