from django.http import JsonResponse
from rest_framework import filters, generics, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Guset, Movie, Reservation
from .serializers import (
    GuestSerializer,
    MovieSearchSerializer,
    MovieSerializer,
    NewReservationSerializer,
    ReservationSerializer,
)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAdminUser])
def no_rest_no_model(request):
    guests = [
        {
            "id": 1,
            "name": "Example Guest",
            "mobile": "00000000000",
        },
        {
            "id": 2,
            "name": "Another Guest",
            "mobile": "00000000001",
        },
    ]
    return JsonResponse(guests, safe=False)
    
# 2  without rest ffrom model data default django

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAdminUser])
def no_rest_from_model(request):
    data = Guset.objects.all()
    return JsonResponse({'guests':list(data.values('name','mobile'))}) #JSON التي يمكن تحويلها إلى  (Dictionaries) لتحويل البيانات مباشرةً إلى قائمة من القواميس  .values() بسهولةاستخدمنا 

class GuestListView(generics.ListCreateAPIView):
    queryset = Guset.objects.prefetch_related("reservation")
    serializer_class = GuestSerializer
    permission_classes = [IsAdminUser]


class GuestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Guset.objects.prefetch_related("reservation")
    serializer_class = GuestSerializer
    permission_classes = [IsAdminUser]
    
class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guset.objects.prefetch_related("reservation")
    serializer_class = GuestSerializer
    permission_classes = [IsAdminUser]
    
class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["movie"]

    def get_permissions(self):
        permission_class = (
            IsAuthenticated
            if self.action in {"list", "retrieve"}
            else IsAdminUser
        )
        return [permission_class()]
    
    
class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related("guest", "movie")
    serializer_class = ReservationSerializer
    permission_classes = [IsAdminUser]
    
    
    
#8 find movie
@api_view(['GET'])
def find_movie(request):
    search = MovieSearchSerializer(data=request.query_params)
    search.is_valid(raise_exception=True)
    movies = Movie.objects.filter(
        hall=search.validated_data["hall"],
        movie=search.validated_data["movie"],
    )
    return Response(MovieSerializer(movies, many=True).data)


#9 create reservation 
@api_view(['POST'])
@permission_classes([IsAdminUser])
def new_reservation(request):
    serializer = NewReservationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reservation = serializer.save()
    return Response(
        ReservationSerializer(reservation).data,
        status=status.HTTP_201_CREATED,
    )
