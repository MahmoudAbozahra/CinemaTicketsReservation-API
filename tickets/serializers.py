from rest_framework import serializers

from .models import Guset, Movie, Reservation

#JSON لكنها ليست مدعومة في QuerySet و Model، مثل (Objects) يستخدم كائنات  Django: المشكلة 
# (Client)عند إرسالها إلى العميل  JSON (Serialization) إلى  Pythonتحويل البيانات من .



class Movieserializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ("id", "hall", "movie", "date")
        
        
class Reservationserializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ("id", "guest", "movie")
        
        
class Guestserializer(serializers.ModelSerializer):
    reservation = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Guset
        fields = ("pk", "reservation", "name", "mobile")
