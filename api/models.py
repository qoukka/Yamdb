from django.contrib.auth.models import (AbstractBaseUser, AbstractUser,
                                        BaseUserManager)
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from simple_email_confirmation.models import SimpleEmailConfirmationUserMixin

from api.validators import max_value_current_year


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self,  email, username=None, password=None):
        user = self.create_user(
            email,
            password=password,
        )
        user.is_staff = True
        user.role = 'admin'
        if not username:
            username = email
        user.username = username
        user.save(using=self._db)
        return user


class Role(models.TextChoices):
    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'


class User(SimpleEmailConfirmationUserMixin, AbstractUser):
    first_name = models.TextField(
        verbose_name='имя пользователя',
        null=True
    )
    last_name = models.TextField(
        verbose_name='фамилия пользователя',
        null=True
    )
    username = models.TextField(
        verbose_name='username пользователя',
        null=True,
        unique=True
    )
    bio = models.TextField(verbose_name='информация', null=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    role = models.CharField(
        verbose_name='роль пользователя',
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True


class Category(models.Model):
    name = models.CharField(
        verbose_name='название категории',
        max_length=100,
        unique=True
    )
    slug = models.SlugField(
        verbose_name='slug категории',
        null=True,
        unique=True
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(
        verbose_name='название жанра',
        max_length=20
    )
    slug = models.SlugField(
        verbose_name='slug жанра',
        null=True,
        unique=True
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Title(models.Model):
    name = models.TextField(verbose_name='название', max_length=100)
    year = models.PositiveIntegerField(
        verbose_name='год создания',
        db_index=True,
        validators=[
            MinValueValidator(1900),
            max_value_current_year
        ]
    )
    rating = models.PositiveIntegerField(verbose_name='рейтинг', null=True)
    description = models.TextField(verbose_name='описание', null=True)
    category = models.ForeignKey(
        Category,
        related_name="titles",
        verbose_name='категория',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    genre = models.ManyToManyField(
        Genre,
        related_name="titles",
        verbose_name='жанр'
    )

    class Meta:
        ordering = ["-name"]

    def __str__(self):
        return self.name


class Review(models.Model):
    title = models.ForeignKey(
        Title,
        verbose_name='произведение',
        related_name="review",
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    text = models.TextField(verbose_name='отзыв')
    author = models.ForeignKey(
        User, verbose_name='автор отзыва',
        on_delete=models.CASCADE,
    )
    score = models.PositiveIntegerField(
        verbose_name='оценка',
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10)
        ]
    )
    pub_date = models.DateTimeField(
        verbose_name='дата публикации',
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-pub_date"]
        unique_together = ('title', 'author')

    def __str__(self):
        return (f'{self.author.username} оценил '
                f'{self.title.name} на {self.score}')


class Comment(models.Model):
    review = models.ForeignKey(
        Review,
        related_name="comments",
        verbose_name='отзыв',
        on_delete=models.CASCADE,
        null=True
    )
    text = models.TextField(verbose_name='текст комментария',)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    pub_date = models.DateTimeField(
        verbose_name='дата публикации',
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-pub_date"]

    def __str__(self):
        return self.text


class Rate(models.Model):
    title = models.ForeignKey(
        Title,
        verbose_name='произведение',
        on_delete=models.SET_NULL, blank=True, null=True
    )
    sum_vote = models.PositiveIntegerField(
        verbose_name='сумма оценок',
        default=0
    )
    count_vote = models.PositiveIntegerField(
        verbose_name='количество оценок',
        default=0
    )

    class Meta:
        ordering = ["-id"]
