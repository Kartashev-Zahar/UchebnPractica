def roles(request):
    if request.user.is_authenticated:
        return {"roles": list(request.user.groups.values_list("name", flat=True))}
    return {"roles": []}
