from django.db import transaction
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


class NewReservationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    mobile = serializers.CharField(max_length=15)
    hall = serializers.CharField(max_length=10)
    movie = serializers.CharField(max_length=100)

    def validate(self, attrs):
        matches = list(
            Movie.objects.filter(hall=attrs["hall"], movie=attrs["movie"])[:2]
        )
        if not matches:
            raise serializers.ValidationError(
                {"movie": "No movie matches the supplied hall and title."}
            )
        if len(matches) > 1:
            raise serializers.ValidationError(
                {
                    "movie": (
                        "The supplied hall and title match multiple movies; "
                        "the request cannot identify one unambiguously."
                    )
                }
            )
        attrs["movie_instance"] = matches[0]
        return attrs

    def create(self, validated_data):
        movie = validated_data.pop("movie_instance")
        validated_data.pop("hall")
        validated_data.pop("movie")
        with transaction.atomic():
            guest = Guset.objects.create(**validated_data)
            return Reservation.objects.create(guest=guest, movie=movie)
