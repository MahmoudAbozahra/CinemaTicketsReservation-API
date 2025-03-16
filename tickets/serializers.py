from rest_framework import serializers
from .models import *

#JSON لكنها ليست مدعومة في QuerySet و Model، مثل (Objects) يستخدم كائنات  Django: المشكلة 
# (Client)عند إرسالها إلى العميل  JSON (Serialization) إلى  Pythonتحويل البيانات من .



class Movieserializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = '__all__'
        
        
class Reservationserializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = '__all__'
        
        
class Guestserializer(serializers.ModelSerializer):
    class Meta:
        model = Guset
        fields = ['pk','reservation','name','mobile']             #uuid slug