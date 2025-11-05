from django.contrib.auth.decorators import user_passes_test

#Sprawdzanie roli
def officer_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.groups.filter(name="Funkcjonariusz").exists())(view)
