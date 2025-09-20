from rest_framework import generics, filters, permissions, views
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Listing
from .serializers import CategorySerializer, ListingSerializer
from core.permissions import IsProviderOwnerOrReadOnly
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
import uuid
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import requests

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    
    # Cache categories, low-cardinality and rarely-changing
    @method_decorator(cache_page(60 * 60))  # 1 hour
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ListingListView(generics.ListCreateAPIView):
    serializer_class = ListingSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    permission_classes = [IsProviderOwnerOrReadOnly]
    
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
        # Base public queryset = published listings only
        qs = Listing.objects.select_related('category', 'created_by').filter(status='published').order_by('-featured', '-rating')

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
    queryset = Listing.objects.select_related('category', 'created_by').filter(featured=True, status='published')
    serializer_class = ListingSerializer
    pagination_class = None # No pagination for featured items
    
    # Small list; cache for short TTL (5 minutes)
    @method_decorator(cache_page(60 * 5))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ListingDetailView(generics.RetrieveAPIView):
    queryset = Listing.objects.select_related('category', 'created_by')
    serializer_class = ListingSerializer
    permission_classes = [IsProviderOwnerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            # Owner can see drafts
            return qs.filter(models.Q(status='published') | models.Q(created_by=user))
        return qs.filter(status='published')


class MyListingListView(generics.ListAPIView):
    serializer_class = ListingSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsProviderOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Listing.objects.none()
        return Listing.objects.select_related('category', 'created_by').filter(created_by=user).order_by('-id')


class PublishListingView(generics.UpdateAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [IsProviderOwnerOrReadOnly]

    def update(self, request, *args, **kwargs):
        listing = self.get_object()
        if listing.status == 'published':
            return Response({'detail': 'Already published'}, status=status.HTTP_200_OK)
        listing.status = 'published'
        if not listing.published_at:
            listing.published_at = timezone.now()
        listing.save(update_fields=['status', 'published_at'])
        serializer = self.get_serializer(listing)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ImageUploadView(views.APIView):
    """Upload an image and return its public URL.

    Strategy:
    - If MEDIA_STORAGE_BACKEND == 'supabase': upload via Supabase Storage REST API using service role key.
    - Else: save to local MEDIA_ROOT under uploads/ and return served URL.
    """
    permission_classes = [permissions.IsAuthenticated]
    # Enable handling of multipart/form-data for file uploads (global settings only allow JSONParser)
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'No file provided (expected field name `file`)'}, status=400)

        # Validate content type
        allowed_types = getattr(settings, 'ALLOWED_IMAGE_TYPES', {'image/jpeg', 'image/png', 'image/webp'})
        if file_obj.content_type not in allowed_types:
            return Response({'detail': 'Unsupported image type', 'allowed': list(allowed_types)}, status=415)
        # Validate size
        max_mb = getattr(settings, 'MAX_UPLOAD_IMAGE_MB', 5)
        size_mb = file_obj.size / (1024 * 1024)
        if size_mb > max_mb:
            return Response({'detail': f'File too large ({size_mb:.2f}MB > {max_mb}MB)'}, status=413)

        backend = getattr(settings, 'MEDIA_STORAGE_BACKEND', 'local')
        # Allow an 'auto' mode: if Supabase creds present, use supabase, else local
        if backend == 'auto':
            if all([
                getattr(settings, 'SUPABASE_URL', ''),
                getattr(settings, 'SUPABASE_BUCKET', ''),
                getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', ''),
            ]):
                backend = 'supabase'
            else:
                backend = 'local'
        filename_root, ext = os.path.splitext(file_obj.name)
        if not ext:
            ext = '.jpg'
        unique_name = f"{uuid.uuid4().hex}{ext.lower()}"

        if backend == 'supabase':
            supabase_url = getattr(settings, 'SUPABASE_URL', '')
            bucket = getattr(settings, 'SUPABASE_BUCKET', '')
            service_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '')
            if not (supabase_url and bucket and service_key):
                return Response({'detail': 'Supabase storage not fully configured'}, status=500)
            storage_endpoint = f"{supabase_url}/storage/v1/object/{bucket}/uploads/{unique_name}"
            try:
                resp = requests.post(
                    storage_endpoint,
                    headers={
                        'Authorization': f"Bearer {service_key}",
                        'Content-Type': file_obj.content_type or 'application/octet-stream',
                    },
                    data=file_obj.read(),
                    timeout=15,
                )
            except requests.RequestException as exc:
                return Response({'detail': f'Upload error: {exc}'}, status=502)
            if resp.status_code not in (200, 201):
                return Response({'detail': 'Supabase upload failed', 'status_code': resp.status_code, 'body': resp.text[:400]}, status=502)
            # Return both full public URL (for immediate preview) and relative path (recommended to store in DB)
            relative_path = f"uploads/{unique_name}"
            private_bucket = getattr(settings, 'SUPABASE_PRIVATE_BUCKET', False)
            if private_bucket:
                # Generate signed URL via Supabase storage API
                signed_ttl = getattr(settings, 'SUPABASE_SIGNED_URL_TTL', 3600)
                sign_endpoint = f"{supabase_url}/storage/v1/object/sign/{bucket}/{relative_path}"
                try:
                    sign_resp = requests.post(sign_endpoint, headers={'Authorization': f'Bearer {service_key}', 'Content-Type': 'application/json'}, json={'expiresIn': signed_ttl})
                    if sign_resp.status_code not in (200, 201):
                        return Response({'detail': 'Failed to sign URL', 'status_code': sign_resp.status_code, 'body': sign_resp.text[:400]}, status=502)
                    signed_data = sign_resp.json()
                    public_url = signed_data.get('signedURL') or signed_data.get('signedUrl') or ''
                except requests.RequestException as exc:
                    return Response({'detail': f'Failed to sign URL: {exc}'}, status=502)
            else:
                public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{relative_path}"

            # Create a thumbnail (only for public or private; store as uploads/thumbs/<uuid>.jpg)
            thumb_relative = None
            try:
                from io import BytesIO
                from PIL import Image
                # Need original bytes again; re-download if needed when file_obj already consumed
                # For simplicity, assume we can re-fetch from Supabase just uploaded
                get_endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{relative_path}"
                img_resp = requests.get(get_endpoint, headers={'Authorization': f'Bearer {service_key}'}, timeout=10)
                if img_resp.status_code in (200, 201):
                    im = Image.open(BytesIO(img_resp.content))
                    im.thumbnail((400, 400))
                    buf = BytesIO()
                    im.save(buf, format='JPEG', quality=80)
                    thumb_name = f"thumbs/{unique_name.rsplit('.',1)[0]}.jpg"
                    put_thumb_endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{thumb_name}"
                    put_resp = requests.post(put_thumb_endpoint, headers={'Authorization': f'Bearer {service_key}', 'Content-Type': 'image/jpeg'}, data=buf.getvalue(), timeout=15)
                    if put_resp.status_code in (200, 201):
                        thumb_relative = thumb_name
            except Exception:
                pass  # Fail silently for thumbnail

            return Response({'url': public_url, 'path': relative_path, 'thumb_path': thumb_relative}, status=201)

        # Local fallback
        saved_path = default_storage.save(f"uploads/{unique_name}", ContentFile(file_obj.read()))
        if hasattr(default_storage, 'url'):
            url = request.build_absolute_uri(default_storage.url(saved_path))
        else:
            url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")
        return Response({'url': url, 'path': saved_path}, status=201)

