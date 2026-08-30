from rest_framework import serializers

from .models import Ride, RideEvent, User


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id_user", "role", "first_name", "last_name", "email", "phone_number")


class UserSerializer(UserSummarySerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta(UserSummarySerializer.Meta):
        fields = UserSummarySerializer.Meta.fields + ("password",)

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=("password",))
        return instance


class RideEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideEvent
        fields = ("id_ride_event", "ride", "description", "created_at")


class NestedRideEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideEvent
        fields = ("id_ride_event", "description", "created_at")


class RideSerializer(serializers.ModelSerializer):
    id_rider = serializers.PrimaryKeyRelatedField(source="rider", queryset=User.objects.all())
    id_driver = serializers.PrimaryKeyRelatedField(source="driver", queryset=User.objects.all())
    rider = UserSummarySerializer(read_only=True)
    driver = UserSummarySerializer(read_only=True)
    todays_ride_events = serializers.SerializerMethodField()
    distance_km = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = Ride
        fields = (
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "rider",
            "driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
            "distance_km",
            "todays_ride_events",
        )

    def get_todays_ride_events(self, ride):
        events = getattr(ride, "todays_ride_events_cache", ())
        return NestedRideEventSerializer(events, many=True).data

