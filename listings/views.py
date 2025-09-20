from rest_framework import generics, filters, permissions
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Listing
from .serializers import CategorySerializer, ListingSerializer
from core.permissions import IsProviderOrReadOnly
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    # Cache categories, low-cardinality and rarely-changing
    @method_decorator(cache_page(60 * 60))  # 1 hour
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ListingListView(generics.ListCreateAPIView):
    queryset = Listing.objects.select_related('category').all().order_by('-featured', '-rating')
    serializer_class = ListingSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    permission_classes = [IsProviderOrReadOnly]
    
    # Mapping frontend query params to Django filter lookups
    filterset_fields = {
        'category__slug': ['exact'],
        'location': ['icontains'],
        'rating': ['gte'],
        # More complex filters like price range or capacity may need a custom filter class
    }
    
    search_fields = ['title', 'features']
    
    # Mapping frontend sort values to Django ordering
    ordering_fields = ['rating', 'featured'] # Add more as needed, e.g., a price field
    
    def get_queryset(self):
        qs = super().get_queryset()

        params = self.request.query_params
        # Map SPA params 1:1 per roadmap
        cat = params.get('cat')  # category slug
        city = params.get('city')  # substring search on location
        min_price = params.get('minPrice')
        max_price = params.get('maxPrice')
        rating_gte = params.get('ratingGte')
        sort = params.get('sort')

        if cat:
            qs = qs.filter(category__slug=cat)
        if city:
            qs = qs.filter(location__icontains=city)
        if rating_gte:
            try:
                qs = qs.filter(rating__gte=float(rating_gte))
            except ValueError:
                pass
        if min_price:
            try:
                qs = qs.filter(price_min__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                qs = qs.filter(price_min__lte=float(max_price))
            except ValueError:
                pass

        # Sorting
        if sort == 'featured':
            qs = qs.order_by('-featured', '-rating')
        elif sort == 'price-asc':
            qs = qs.order_by('price_min')
        elif sort == 'price-desc':
            qs = qs.order_by('-price_min')
        elif sort == 'rating-desc':
            qs = qs.order_by('-rating')

        return qs

class FeaturedListingListView(generics.ListAPIView):
    queryset = Listing.objects.select_related('category').filter(featured=True)
    serializer_class = ListingSerializer
    pagination_class = None # No pagination for featured items
    
    # Small list; cache for short TTL (5 minutes)
    @method_decorator(cache_page(60 * 5))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ListingDetailView(generics.RetrieveAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

