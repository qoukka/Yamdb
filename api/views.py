from django.conf import settings
from django.core.mail import send_mail
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import permission_classes, api_view, action
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, Review, Comment, Category, Genre, Title, Rate
from .permissions import IsAdmin, ReviewAndComment, UserPermission
from .serializers import (UserSerializer, TokenWithoutPasswordSerializer,
                          UserAllSerializer, ReviewSerializer,
                          CommentSerializer, CategorySerializer,
                          GenreSerializer, TitleSerializer)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserAllSerializer
    permission_classes = [UserPermission]
    lookup_field = 'username'

    @action(detail=True)
    def get_me(self, request):
        return Response(self.serializer_class(request.user).data)

    @action(detail=True, methods=['patch'])
    def update_me(self, request):
        serializer = self.serializer_class(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['delete'])
    def delete_me(self, request):
        return Response(status=405)


@api_view(['post'])
@permission_classes((AllowAny,))
def send_confirmation_code(request):
    user = request.data
    serializer = UserSerializer(data=user)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    user = get_object_or_404(User, email=request.data.get('email'))
    subject = 'Thank you for registering to YaMDB'
    message = (f'Your confirmation code is {user.confirmation_key}.'
               f'Use code for token taking.')
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [f'{user.email}', ]
    send_mail(subject, message, email_from, recipient_list)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = TokenWithoutPasswordSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, ReviewAndComment]

    def get_queryset(self):
        title = get_object_or_404(Title, pk=self.kwargs.get('title_id'))
        return title.review.all()

    def perform_create(self, serializer):
        title = get_object_or_404(Title, pk=self.kwargs.get('title_id'))
        review = Review.objects.filter(
            author=self.request.user,
            title_id=self.kwargs.get('title_id')
        )
        serializer.check_review(review)
        serializer.save(
            author=self.request.user,
            title_id=self.kwargs.get('title_id')
        )
        rate = get_object_or_404(Rate, title_id=self.kwargs.get('title_id'))
        rate.sum_vote += serializer.data.get('score')
        rate.count_vote += 1
        rate.save()
        title.rating = rate.sum_vote // rate.count_vote
        title.save()

    def perform_update(self, serializer):
        review = get_object_or_404(
            Review,
            author=self.request.user,
            title_id=self.kwargs.get('title_id')
        )
        rate = get_object_or_404(Rate, title_id=self.kwargs.get('title_id'))
        rate.sum_vote -= review.score
        serializer.save(
            author=self.request.user,
            title_id=self.kwargs.get('title_id')
        )
        rate.sum_vote += serializer.data.get('score')
        rate.save()
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        title.rating = rate.sum_vote // rate.count_vote
        title.save()

    def perform_destroy(self, instance):
        get_object_or_404(Title, pk=self.kwargs.get('title_id'))
        rate = get_object_or_404(Rate, title_id=self.kwargs.get('title_id'))
        rate.sum_vote -= instance.score
        rate.count_vote -= 1
        rate.save()
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        title.rating = rate.sum_vote // rate.count_vote
        title.save()
        instance.delete()


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, ReviewAndComment]

    def get_queryset(self):
        review = get_object_or_404(Review, pk=self.kwargs.get('review_id'))
        return review.comments.all()

    def perform_create(self, serializer):
        get_object_or_404(Title, pk=self.kwargs.get('title_id'))
        get_object_or_404(Review, pk=self.kwargs.get('review_id'))
        serializer.save(
            author=self.request.user,
            review_id=self.kwargs.get('review_id')
        )


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAdmin]
    lookup_field = 'slug'
    filter_backends = [SearchFilter]
    search_fields = ['=name']


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAdmin]
    lookup_field = 'slug'
    filter_backends = [SearchFilter]
    search_fields = ['=name']


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.all()
    serializer_class = TitleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['year']

    def get_queryset(self):
        assert self.queryset is not None, (
            "'%s' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
            % self.__class__.__name__
        )
        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            queryset = queryset.all()
        if self.request.query_params.get('name'):
            queryset = queryset.filter(
                name__icontains=self.request.query_params.get('name')
            )
        if self.request.query_params.get('category'):
            queryset = queryset.filter(
                category__slug=self.request.query_params.get('category')
            )
        if self.request.query_params.get('genre'):
            queryset = queryset.filter(
                genre__slug=self.request.query_params.get('genre')
            )
        return queryset

    def perform_create(self, serializer):
        category, genres = serializer.check_category_genre(
            self.request.data.get('category'),
            self.request.data.getlist('genre')
        )
        if category:
            serializer.save(category=category[0], genre=genres)
        else:
            serializer.save(genre=genres)
        Rate.objects.create(
            title_id=serializer.data.get('id'),
            sum_vote=0,
            count_vote=0
        )

    def perform_update(self, serializer):
        category, genres = serializer.check_category_genre(
            self.request.data.get('category'),
            self.request.data.getlist('genre')
        )
        if category:
            serializer.save(category=category[0])
        title = get_object_or_404(Title, pk=self.kwargs.get('pk'))
        for genre in genres:
            title.genre.add(get_object_or_404(Genre, slug=genre))

    def perform_destroy(self, instance):
        rate = get_object_or_404(Rate, title_id=self.kwargs.get('pk'))
        rate.delete()
        instance.delete()
