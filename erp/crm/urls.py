from django.urls import path
from . import views
app_name = 'crm'
urlpatterns = [
    path("",views.index.as_view(),name="index"),
    # path("search/",views.search_view,name='search'),
    path("create_contact/",views.contact_create.as_view(),name="create_contact"),
    path("create_company/",views.company_create.as_view(),name="create_company"),
    path("delete_company/<int:pk>/",views.delete_company,name="delete_company"),
    path("contact_list/",views.contact_list.as_view(),name="contact_list"),
    path("company_list/",views.company_list.as_view(),name="company_list"),
    path("contact_detail/<int:pk>/",views.contact_detail_view.as_view(),name="contact_detail"),
    path("company_detail/<int:pk>/",views.company_detail_view.as_view(),name="company_detail"),
    path('notes/<int:pk>/update_note/', views.EditNoteView.as_view(), name='update_note'),
    path('update_contact/<int:pk>/', views.EditContactView.as_view(), name='update_contact'),
    path('update_company/<int:pk>/', views.EditCompanyView.as_view(), name='update_company'),
    path('notes/<int:pk>/delete_note/', views.DeleteNoteView.as_view(), name='delete_note'),
    # path('company_detail/<int:pk>/delete_company', views.DeleteNoteView.as_view(), name='delete_company'),
    path("delete_company_from_contact/<int:contact_pk>/",views.delete_company_from_contact.as_view(),name="delete_company_from_contact"),
    

]

htmx_urlpatterns = [
path('search_contact/',views.search_contact,name="search_contact"),
path('search_contacts_only/',views.search_contacts_only,name="search_contacts_only"),
path('add_contact_to_company/<int:company_pk>/<int:contact_pk>/',views.add_contact_to_company.as_view(),name="add_contact_to_company"),
]

urlpatterns += htmx_urlpatterns