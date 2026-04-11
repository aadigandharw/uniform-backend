from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, full_name=None):  # ✅ FIX
        if not email:
            raise ValueError("Email required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            full_name=full_name  # ✅ FIX
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, full_name=None):  # ✅ FIX
        user = self.create_user(email, password, full_name)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True  # ✅ superuser always active
        user.save()
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)

    is_active = models.BooleanField(default=False)  # 🔥 IMPORTANT CHANGE
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email