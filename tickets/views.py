from django.shortcuts import render
from .models import *
from django.http.response import JsonResponse
from rest_framework.decorators import api_view
from .serializers import *
from rest_framework.response import Response 
from rest_framework import status,filters
from rest_framework.views import APIView
from django.http import Http404
from rest_framework import mixins,generics,viewsets
from rest_framework.authentication import BasicAuthentication,TokenAuthentication
from rest_framework.permissions import IsAuthenticated


# 1 without REST and no model query FBV

def no_rest_no_model(request):
    guests=[
        {
            'id':1,
            'name':'mahmoud',
            'mobile':'01235478952',
                
        },
        {
            'id':2,
            'name':'hozaa',
            'mobile':'01236547896',
        }
    ]  
    return JsonResponse(guests,safe=False)
    
# 2  without rest ffrom model data default django

def no_rest_from_model(request):
    data = Guset.objects.all()
    return JsonResponse({'guests':list(data.values('name','mobile'))}) #JSON التي يمكن تحويلها إلى  (Dictionaries) لتحويل البيانات مباشرةً إلى قائمة من القواميس  .values() بسهولةاستخدمنا 

#3 Function based views 
#3.1 GET  POST 
@api_view(['GET','POST']) 
def FBV_list(request):
    
    #GET
    if request.method == 'GET':
        guests = Guset.objects.all()
        serializer = Guestserializer(guests , many=True)
        return Response(serializer.data)
    
    #POST
    elif request.method == 'POST':
        serializer = Guestserializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.data,status=status.HTTP_400_BAD_REQUEST)


#3.2 GET  PUT  DELETE
@api_view(['GET','PUT','DELETE']) 
def FBV_pk(request,pk):
    try:
        guest = Guset.objects.get(pk=pk)
    except Guset.DoesNotExist :
        return Response(status=status.HTTP_400_BAD_REQUEST) 
    #GET 
    if request.method == 'GET':
        serializer = Guestserializer(guest , many=False)
        return Response(serializer.data)
    
    #PUT
    elif request.method == 'PUT':
        serializer = Guestserializer(guest , data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data , status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    #DELETE 
    elif request.method =='DELETE':
        guest.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
#4.1 cbv class based view GET  POST
class CBV_list(APIView):
    def get(self , request):
        guests=Guset.objects.all()
        serializer=Guestserializer(guests,many=True)
        return Response(serializer.data)
    
    def post(self , request):
        serializer=Guestserializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.data , status=status.HTTP_400_BAD_REQUEST)
    
#4.2  GET PUT DELETE  clas based view CBV 
class CBV_pk(APIView):
    
    def get_object(self,pk):
        try:
            return Guset.objects.get(pk=pk)
        except Guset.DoesNotExist:
            raise Http404
    
    def get(self ,request,pk ):
        guests=self.get_object(pk)
        serializer=Guestserializer(guests,many=False)
        return Response(serializer.data)
    
    def put(self ,request ,pk):
        guests=self.get_object(pk)
        serializer=Guestserializer(guests,data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.data,status=status.HTTP_400_BAD_REQUEST)
    def delete(self ,request ,pk):
        guests=self.get_object(pk)
        guests.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
  
  
  
#5.1 mixins  GIT,POST

class Mixins_list(mixins.ListModelMixin,mixins.CreateModelMixin,generics.GenericAPIView):
    queryset=Guset.objects.all()  
    serializer_class=Guestserializer
    
    def get(self,request):
        return self.list(request)
    def post(self,request):
        return self.create(request)
        
   
#5.2 mixins  GIT,PUT,DELETE 
class Mixins_pk(mixins.RetrieveModelMixin,mixins.UpdateModelMixin,mixins.DestroyModelMixin,generics.GenericAPIView):
    queryset=Guset.objects.all()  
    serializer_class=Guestserializer
    
    def get(self,request,pk):
        return self.retrieve(request)
    def put(self,request,pk):
        return self.update(request)
    def delete(self,request,pk):
        return self.destroy(request)

#6.1 generics  GIT,POST
class Generics_list(generics.ListCreateAPIView):
    queryset=Guset.objects.all()
    serializer_class=Guestserializer
    authentication_classes=[TokenAuthentication]
    permission_classes=[IsAuthenticated]


#6.2 generics  GIT,PUT,DELETE
class Generics_pk(generics.RetrieveUpdateDestroyAPIView):
    queryset=Guset.objects.all()
    serializer_class=Guestserializer
    authentication_classes=[TokenAuthentication]
    permission_classes=[IsAuthenticated]
    
#7 viewsets 
class viewsets_guest(viewsets.ModelViewSet):
    queryset=Guset.objects.all()
    serializer_class=Guestserializer
    
#-----------------------------------------------------complete

class viewsets_movie(viewsets.ModelViewSet):
    queryset=Movie.objects.all()
    serializer_class=Movieserializer
    filter_backends = [filters.SearchFilter]
    search_fileds=['movie']
    
    
class viewsets_reservation(viewsets.ModelViewSet):
    queryset=Reservation.objects.all()
    serializer_class=Reservationserializer
    
    
    
#8 find movie
@api_view(['GET'])
def find_movie(request):
    movies=Movie.objects.filter(
        hall=request.data['hall'],
        movie=request.data['movie'],
    )
    serializer=Movieserializer(movies,many=True)
    return Response(serializer.data)


#9 create reservation 
@api_view(['POST'])
def new_reservation(request):
    movie=Movie.objects.get(
        hall=request.data['hall'],
        movie=request.data['movie'],
    )
    
    guest=Guset()
    guest.name=request.data['name']
    guest.mobile=request.data['mobile']
    guest.save()
    
    
    
    reservation=Reservation()
    reservation.guest=guest
    reservation.movie=movie
    reservation.save()
    
    return Response(request.data , status=status.HTTP_201_CREATED)
