from django.urls import path
from . import views
app_name = 'crm'
urlpatterns = [
    path("",views.index.as_view(),name="index"),
    # path("search/",views.search_view,name='search'),
    path("create_contact/",views.contact_create.as_view(),name="create_contact"),
    path("create_company/",views.company_create.as_view(),name="create_company"),
    path("delete_company/",views.DeleteCompanyView.as_view(),name="delete_company"),
    path("contact_list/",views.contact_list.as_view(),name="contact_list"),
    path("company_list/",views.company_list.as_view(),name="company_list"),
    path("contact_detail/<int:pk>/",views.contact_detail_view.as_view(),name="contact_detail"),
    path("company_detail/<int:pk>/",views.company_detail_view.as_view(),name="company_detail"),
    path('notes/<int:pk>/update_note', views.EditNoteView.as_view(), name='update_note'),
    path('contact_detail/<int:pk>/update_contact', views.EditContactView.as_view(), name='update_contact'),
    path('notes/<int:pk>/delete_note', views.DeleteNoteView.as_view(), name='delete_note'),
    

]

htmx_urlpatterns = [
path('search_contact/',views.search_contact,name="search_contact"),
]

urlpatterns += htmx_urlpatterns