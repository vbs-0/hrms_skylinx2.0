from django.shortcuts import render

from skylinx.decorators import login_required, permission_required


@login_required
@permission_required("geofencing.add_geofencing")
def geofaceconfig(request):
    return render(request, "attendance/geofaceconfig/geo_face_config.html")
