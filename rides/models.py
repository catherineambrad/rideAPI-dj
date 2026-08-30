from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("role") != User.Role.ADMIN:
            raise ValueError("A superuser must have the admin role.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        RIDER = "rider", "Rider"
        DRIVER = "driver", "Driver"

    id_user = models.AutoField(primary_key=True)
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    phone_number = models.CharField(max_length=30, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        db_table = "user"
        ordering = ("id_user",)

    def __str__(self):
        return self.email


class Ride(models.Model):
    class Status(models.TextChoices):
        EN_ROUTE = "en-route", "En route"
        PICKUP = "pickup", "Pickup"
        DROPOFF = "dropoff", "Dropoff"

    id_ride = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    rider = models.ForeignKey(
        User, db_column="id_rider", related_name="rides_as_rider", on_delete=models.PROTECT
    )
    driver = models.ForeignKey(
        User, db_column="id_driver", related_name="rides_as_driver", on_delete=models.PROTECT
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride"
        ordering = ("pickup_time", "id_ride")
        indexes = [
            models.Index(fields=("status", "pickup_time"), name="ride_status_pickup_idx"),
            models.Index(fields=("rider", "pickup_time"), name="ride_rider_pickup_idx"),
        ]

    def __str__(self):
        return f"Ride {self.id_ride} ({self.status})"


class RideEvent(models.Model):
    id_ride_event = models.AutoField(primary_key=True)
    ride = models.ForeignKey(
        Ride, db_column="id_ride", related_name="events", on_delete=models.CASCADE
    )
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride_event"
        ordering = ("created_at", "id_ride_event")
        indexes = [
            models.Index(fields=("ride", "created_at"), name="ride_event_ride_time_idx"),
            models.Index(fields=("description", "created_at"), name="ride_event_desc_time_idx"),
        ]

    def __str__(self):
        return f"Event {self.id_ride_event} for ride {self.ride_id}"
