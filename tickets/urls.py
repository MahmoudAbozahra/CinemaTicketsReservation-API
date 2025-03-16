from django.urls import path,include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token


router=DefaultRouter()
router.register('guests',views.viewsets_guest)
router.register('movie',views.viewsets_movie)
router.register('reservations',views.viewsets_reservation)

urlpatterns = [
    
    #1
    
    path('django/jsonresponsenomodel/',views.no_rest_no_model),
    
    #2
    
    path('django/jsonresponsefrommodel/',views.no_rest_from_model),
    
    #3.1 GET , POST from rest frame-work function based view @api_view
    path('rest/fbv_list/',views.FBV_list),
    
    #3.2 GET PUT DELETE from rest frame-work function based view @api_view
    path('rest/fbv_pk/<int:pk>',views.FBV_pk),
    
    
    #4.1 GET , POST from rest frame-work class based view CBV_list APIview
    path('rest/cbv_list/',views.CBV_list.as_view()),
    
    #4.2 GET PUT DELETE from rest frame-work class based view CBV_pk APIview
    path('rest/CBV_pk/<int:pk>',views.CBV_pk.as_view()),
    
    #5.1 mixins  GIT,POST
    path('rest/mixins_list/',views.Mixins_list.as_view()),
    
    #5.2 mixins GIT,PUT,DELETE
    path('rest/mixins_pk/<int:pk>',views.Mixins_pk.as_view()),
    
    
     #6.1  generics  GIT,POST
    path('rest/generics/',views.Generics_list.as_view()),
    
    #6.2 generics GIT,PUT,DELETE
    path('rest/generics/<int:pk>',views.Generics_pk.as_view()),
    
    
    #7 viewsets 
    path('rest/viewsets/',include(router.urls)),
    
   #8 find movie
   path('fbv/findmovie/',views.find_movie),
   
   #9 create reservation
   path('fbv/new_reservation',views.new_reservation),
   
   #rest auth url 
   path('api-auth',include('rest_framework.urls')),
   
   #rest auth token
   path('api-auth-token',obtain_auth_token),
]
