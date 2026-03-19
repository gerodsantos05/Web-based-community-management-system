from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignInForm, SignUpForm


def index(request):
    return render(request, "index.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
    })


def signin(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("home")

    form = SignInForm(request.POST)
    if form.is_valid():
        user = form.cleaned_data.get("user")
        login(request, user)
        return redirect("dashboard")

    return render(request, "index.html", {
        "signin_form": form,
        "signup_form": SignUpForm(),
        "open_modal": "signin",
    })


def about(request):
    return render(request, "about.html")


def products(request):
    return render(request, "product.html")


def contact(request):
    return render(request, "contact.html", {
        "signin_form": SignInForm(),
        "signup_form": SignUpForm(),
    })


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("home")

    form = SignUpForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect("signin")

    return render(request, "index.html", {
        "signup_form": form,
        "signin_form": SignInForm(),
        "open_modal": "signup",
    })


@login_required(login_url="signin")
def dashboard(request):
    if not request.user.is_superuser:
        return redirect("signin")

    return render(request, "dashboard.html", {
        "active_page": "dashboard",
    })


@login_required(login_url="signin")
def users(request):
    if not request.user.is_superuser:
        return redirect("signin")

    return render(request, "users.html", {
        "active_page": "users",
    })


@login_required(login_url="signin")
def donations(request):
    if not request.user.is_superuser:
        return redirect("signin")

    return render(request, "donation.html", {
        "active_page": "donations",
    })


@login_required(login_url="signin")
def payment(request):
    if not request.user.is_superuser:
        return redirect("signin")

    return render(request, "payment.html", {
        "active_page": "payment",
    })


@login_required(login_url="signin")
def inventory(request):
    if not request.user.is_superuser:
        return redirect("signin")

    return render(request, "inventory.html", {
        "active_page": "inventory",
    })


@login_required(login_url="signin")
def reports(request):
    if not request.user.is_superuser:
        return redirect("signin")

    return render(request, "reports.html", {
        "active_page": "reports",
    })


@login_required(login_url="signin")
def settings(request):
    if not request.user.is_superuser:
        return redirect("signin")

    return render(request, "settings.html", {
        "active_page": "settings",
    })


def logout_view(request):
    logout(request)
    return redirect("signin")
