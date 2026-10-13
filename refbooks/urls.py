from django.urls import path
from .views import CheckElementView, ElementListView, RefbookListView

urlpatterns = [
    path("", RefbookListView.as_view(), name="refbook-list"),
    path("<int:id>/elements", ElementListView.as_view(), name="element-list"),
    path("<int:id>/check_element", CheckElementView.as_view(), name="check-element"),
]
