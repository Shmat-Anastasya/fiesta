def cabinet(request):
    name = ""
    if request.user.is_authenticated:
        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            profile = getattr(request.user, "specialist_profile", None)
        if profile is not None:
            name = profile.first_name or profile.last_name
        if not name:
            name = request.user.email
    return {"cabinet_name": name}
