from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Role(models.TextChoices):
    DRIVER = "DRIVER", "Driver"
    ADMINISTRATOR = "ADMINISTRATOR", "Administrator"


class ParkMeUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMINISTRATOR)
        if extra_fields.get("role") != Role.ADMINISTRATOR:
            raise ValueError("A superuser must have the Administrator role.")
        return super().create_superuser(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )


class User(AbstractUser):
    email = models.EmailField("email address", unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DRIVER,
    )

    objects = ParkMeUserManager()

    def save(self, *args, **kwargs):
        self.username = self.username.strip().lower()
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
