from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.conf import settings

# Create your models here.

#Guest  --- Movie ---Reservation


class Movie(models.Model):
    hall = models.CharField(max_length=10)
    movie = models.CharField(max_length=100)
    date = models.DateField()
    
    def __str__(self):
        return self.movie
    
class Guset(models.Model):
    name=models.CharField(max_length=50)
    mobile=models.CharField(max_length=15)
    
    def __str__(self):
        return self.name
    
    
class Reservation(models.Model):
    guest = models.ForeignKey(Guset,related_name='reservation',on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie,related_name='reservation',on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Guest {str(self.guest)} will watch ({str(self.movie)})"
    
    
    

@receiver(post_save,sender=settings.AUTH_USER_MODEL)
def Tokencreate(sender, instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)