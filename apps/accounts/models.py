from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model kept intentionally small for the MVP admin role."""

    full_name_kh = models.CharField("ឈ្មោះជាភាសាខ្មែរ", max_length=150, blank=True)
    phone_number = models.CharField("លេខទូរសព្ទ", max_length=30, blank=True)

    def __str__(self):
        return self.get_full_name() or self.full_name_kh or self.username

