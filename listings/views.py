from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Listing
from .serializers import CategorySerializer, ListingSerializer
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ListingListView(generics.ListAPIView):
    queryset = Listing.objects.all().order_by('-featured', '-rating')
    serializer_class = ListingSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    
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
        queryset = super().get_queryset()
        
        # Custom filtering logic can go here, for example:
        min_price = self.request.query_params.get('minPrice')
        if min_price:
            # This is a simplified example. Assumes price is stored in a way that can be filtered.
            # You would need to parse the price_range field or have a dedicated price field.
            pass

        sort = self.request.query_params.get('sort')
        if sort == 'price-asc':
            # queryset = queryset.order_by('price_field') # Replace with your actual price field
            pass
        elif sort == 'price-desc':
            # queryset = queryset.order_by('-price_field')
            pass
        elif sort == 'rating-desc':
            queryset = queryset.order_by('-rating')
        
        return queryset

class FeaturedListingListView(generics.ListAPIView):
    queryset = Listing.objects.filter(featured=True)
    serializer_class = ListingSerializer
    pagination_class = None # No pagination for featured items

class ListingDetailView(generics.RetrieveAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

